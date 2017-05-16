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
def init_copy_vhds(source_path, destination_path=False, count=1, base_vhd_name=""):
    """ Create a list of tuples that can be processed as by the pool method for the copy vhd process
    """
    if not destination_path:
        destination_path = VirtualMachine.get_default_vhd_path().strip()

    base_name = basename(source_path).strip()
    vhd_name = "-".join([base_vhd_name, base_name.split('.')[0]])
    if count > 1:
        return [ (source_path, path.join(destination_path, vhd_name + str(index) + '.vhdx')) for index in range(count) ]
    else:
        return [(source_path, path.join(destination_path, base_name))]

def copy_item(path_tuple):
    """ Copies a file and returns the destination path 
    """
    #print('asdasd')
    if path.exists(path_tuple[1]): remove(path_tuple[1])
    copy(path_tuple[0], path_tuple[1])
    return path_tuple[1]

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

def create_vms(vhd_path_list, vm_base_name='lisa_parser_vm', hv_server='localhost', switch_name='external', mem_size='1GB', checkpoint='icabase'):
    """ Creates multiple VMs, from a provided vhd list, in order to run multiple LISA tests
    """
    vm_list = []
    index = 1
    for vhd_path in vhd_path_list:
        vm_name = ''.join([vm_base_name, str(index)])
        # Create VM fails for folders that contain spaces
        vhd_path = ''.join(["\"", vhd_path, "\""])
        # Check if VM already exists
        try:
            VirtualMachine.execute_command(['powershell', 'Get-VM', '-Name', vm_name, '-ComputerName', hv_server], log_output=False)
            logger.debug('Virtual Machine {} already exists'.format(vm_name))
            logger.debug('Removing existing VM')
            VirtualMachine.execute_command(['powershell', 'Remove-VM', '-Name', vm_name, '-ComputerName', hv_server, '-Force'])
        except RuntimeError as vm_err:
            logger.warning('Error while querying for VM')
            logger.warning(vm_err)

        VirtualMachine.create_vm(vm_name, vhd_path, switch_name, hv_server, mem_size)
        if checkpoint: VirtualMachine.create_checkpoint(vm_name, hv_server, checkpoint)
        vm_list.append(vm_name)
        index += 1

    return vm_list

def get_progress_string(iteration, total, prefix = '', suffix='', decimals = 1, length = 50, fill = '#'):
    percent = ("{0:." + str(decimals) + "f}").format(100 * (iteration / float(total)))
    filledLength = int(length * iteration // total)
    bar = fill * filledLength + '-' * (length - filledLength)
    return "\r {} |{}| {} {}".format(prefix, bar, percent, suffix)

def write_on_line(output, line_number=1, new_line=False, direction='up'):
    if direction == 'up':
        direction = 'A'
    elif direction == 'down':
        direction = 'B'
    if line_number > 0:
        sys.stdout.write("\033[{}{}".format(line_number, direction))
    #sys.stdout.write("\033[F")
    sys.stdout.write(output)
    sys.stdout.flush()
    sys.stdout.write('\r')
    sys.stdout.flush()
    if new_line or iteration == total:
        sys.stdout.write('\n')

def print_progress_bar(iteration, total, prefix='', suffix='', decimals=1, length=50, fill='#'):
    percent = ("{0:." + str(decimals) + "f}").format(100 * (iteration / float(total)))
    filledLength = int(length * iteration // total)
    bar = fill * filledLength + '-' * (length - filledLength)
    print('\r%s |%s| %s%% %s' % (prefix, bar, percent, suffix), end='\r')
    # Print New Line on Complete
    if iteration == total: 
        print()
