"""
Linux on Hyper-V and Azure Test Code, ver. 1.0.0
Copyright (c) Microsoft Corporation

All rights reserved
Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.

See the Apache Version 2.0 License for specific language governing
permissions and limitations under the License.
"""
from __future__ import print_function
from ntpath import basename
from virtual_machine import VirtualMachine
from shutil import copy, copytree, rmtree
from os import path, remove, listdir, mkdir
import logging
import sys

logger = logging.getLogger(__name__)

def generate_vhd_names(source_vhd_path, destination_vhd_folder, count=1, base_vhd_name=""):
    """ Generate incremental vhd paths based on the source vhd name
    """
    base_name = basename(source_vhd_path).strip()
    vhd_name = "".join([base_vhd_name, base_name.split('.')[0]])
    for index in range(count):
        yield path.join(destination_vhd_folder, vhd_name + str(index) + '.' + base_name.split('.')[1]) 

def init_create_vms(vm_settings, count=1):
    if 'vhdFolder' not in vm_settings.keys():
        vhd_folder = VirtualMachine.get_default_vhd_path().strip()
    else:
        vhd_folder = vm_settings['vhdFolder']

    vm_list = []
    vhd_paths = generate_vhd_names(vm_settings['vhdPath'], vhd_folder, count=count, base_vhd_name=vm_settings['name'])
    index = 0
    for path in vhd_paths:
        index += 1
        vm_dict = {
            'vmName': vm_settings['name'] + str(index),
            'sourceVhd': vm_settings['vhdPath'],
            'vhdPath': path,
            'server': vm_settings['server'],
            'switchName': vm_settings['switchName'],
            'memory': vm_settings['memory'],
            'snapshotName': vm_settings['snapshotName'],
            'generation': vm_settings['generation']
        }
        vm_list.append(vm_dict)

    return vm_list

def copy_lisa_folder(lisa_path, destination_folder, count=1):
    """ Copies the LISA folder, multiple time, so multiple LISA runs can be executed afterwards
    """
    lisa_paths = []
    for index in range(count):
        destination_path = path.join(destination_folder, 'lisa' + str(index))
        lisa_paths.append(destination_path)
        if path.exists(destination_path): VirtualMachine.execute_command(['powershell', 'Remove-Item','-Recurse', '-Force', work_folder])
        mkdir(destination_path)
        for item_path in listdir(lisa_path):
            full_path = path.join(lisa_path, item_path)
            if path.normpath(full_path) != path.normpath(destination_folder):
                if path.isdir(full_path):
                    copytree(full_path, path.join(destination_path, item_path))
                else:
                	copy(full_path, path.join(destination_path, item_path))
    return lisa_paths

def create_vm(vm_settings_dict):
    # Copy VM VHD
    source_vhd_path = vm_settings_dict['sourceVhd']
    vm_vhd_path = vm_settings_dict['vhdPath']
    if path.exists(vm_vhd_path): remove(vm_vhd_path)
    copy(source_vhd_path, vm_vhd_path)

    # Create VM
    vm_name = vm_settings_dict['vmName']
    hv_server = vm_settings_dict['server']
    # New-VM fails for folders that contain spaces
    vm_vhd_path = ''.join(["\"", vm_vhd_path, "\""])

    if VirtualMachine.check_vm(vm_name, hv_server): VirtualMachine.remove_vm(vm_name, hv_server)
    VirtualMachine.create_vm(
        vm_name, vm_vhd_path, vm_settings_dict['switchName'], hv_server, vm_settings_dict['memory']
    )
    VirtualMachine.create_checkpoint(vm_name, hv_server, vm_settings_dict['snapshotName'])

    return vm_name

def print_progress_bar(iteration, total, prefix='', suffix='', decimals=1, length=50, fill='#'):
    percent = ("{0:." + str(decimals) + "f}").format(100 * (iteration / float(total)))
    filledLength = int(length * iteration // total)
    bar = fill * filledLength + '-' * (length - filledLength)
    print('\r%s |%s| %s%% %s' % (prefix, bar, percent, suffix), end='\r')
    # Print New Line on Complete
    if iteration == total: 
        print()
