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

from virtual_machine import VirtualMachine
from file_parser import ParseXML
from envparse import env
from time import sleep
from config import setup_logging
from lisa_parser import main
from collections import defaultdict
import json
import multiprocessing
import Queue
import logging
import os
import ntpath
import sys

logger = logging.getLogger(__name__)

# TODO
# multiprocessing logging - config logging for each process
# argument parser - config file path, skip setup 
# edit individual test params
# add documentation

class RunLISA(object):
    xml_files = [
        'CoreTests.xml', 'KvpTests.xml', 'Kdump_Tests.xml',
        'LTP.xml', 'NET_Tests.xml', 'NET_Tests_IPv6.xml',
        'NMI_Tests.xml', 'Production_Checkpoint.xml', 'STOR_VHD.xml',
        'STOR_VHDX.xml', 'STOR_VHDXResize.xml', 'FCopy_Tests.xml',
        'STOR_VSS_Backup_Tests.xml', 'StressTests.xml', 'VMBus_Tests.xml', 'lsvmbus.xml'
    ]

    def __init__(self, lisa_path_queue, vm_queue, tests_config, lisa_path, lisa_params):
        self.lisa_queue = lisa_path_queue
        self.vm_queue = vm_queue
        self.config = tests_config
        self.main_lisa_path = lisa_path
        self.params = lisa_params

    def __call__(self, xml_dict):
        logger.info('Editing %s' % xml_dict['name'])
        vm_name = self.vm_queue.get()
        self.config['vmName'] = vm_name
        xml_obj = ParseXML(xml_dict['path'])
        xml_obj.edit_vm_conf(self.config)
        xml_obj.global_config.find('logfileRootDir').text = self.config['logPath']
        try:
            xml_obj.remove_tests(xml_dict['skip'])
        except KeyError:
            logger.debug('No tests will be removed')
        try:
            xml_obj.edit_test_params(xml_dict['params'])
        except KeyError:
            logger.debug('No parameters to edit')
        xml_obj.tree.write(xml_dict['path'])

        lisa_path = self.lisa_queue.get()
        os.chdir(lisa_path)
        lisa_bin = os.path.join(lisa_path, 'lisa.ps1')
        lisa_cmd_list = ['powershell', lisa_bin, 'run', xml_dict['path']]
        lisa_cmd_list.extend(self.params)
        logger.info('Running %s on %s with %s' % (xml_dict['path'], vm_name, lisa_path))
        try:
            VirtualMachine.execute_command(lisa_cmd_list)
            # Get ica log path
            logFolders = [ dir for dir in self.config['logPath'] if xml_obj.get_tests_suite() in dir ]
            result = (xml_dict['path'], max(logFolders, key=os.path.getmtime))
        except RuntimeError:
            logger.error('Test run exited with errors')
            result = False
        
        sleep(60)
        
        self.vm_queue.put(vm_name)
        self.lisa_queue.put(lisa_path)
        return result

    @staticmethod
    def create_test_list(xml_dict, lisa_abs_xml_path, tests_config=False):
        if 'run' in xml_dict.keys():
            xml_list = [
                { 'name': xml_file } for xml_file in xml_dict['run'] if xml_file in RunLISA.xml_files
                ]
        elif 'skip' in xml_dict.keys():
            xml_list = [
                { 'name': xml_file } for xml_file in RunLISA.xml_files if xml_file not in xml_dict['skip']
                ]
        else:
            xml_list = [
                { 'name': xml_file } for xml_file in RunLISA.xml_files
                ]

        if tests_config:
            for xml_dict in xml_list:
                xml_name = xml_dict['name']
                try:
                    xml_dict = tests_config[xml_name]
                    xml_dict['name'] = xml_name
                except KeyError:
                    logger.debug('No extra config found for %s' % xml_dict['name'])
                
                xml_dict['path'] = os.path.join(lisa_abs_xml_path, xml_dict['name'])
        else:
            for xml_dict in xml_list:
                xml_dict['path'] = os.path.join(lisa_abs_xml_path, xml_dict['name'])
 
        return xml_list

    @staticmethod
    def get_lisa_path():
        """Returns the full path of the main LISA folder"""
        for i in range(5):
            cwd_list = os.listdir(os.getcwd())
            if 'lisa.ps1' not in cwd_list:
                os.chdir('..')
                if i is 4:
                    return False
            else:
                break

        return os.getcwd()

    @staticmethod
    def create_vms(vhd_path_list, vm_base_name='lisa_parser_vm', hv_server='localhost', switch_name='external', mem_size='1GB', checkpoint='icabase'):
        vm_list = []
        index = 1
        for vhd_path in vhd_path_list:
            vm_name = ''.join([vm_base_name, str(index)])
            VirtualMachine.create_vm(vm_name, vhd_path, switch_name, hv_server, mem_size)
            VirtualMachine.create_checkpoint(vm_name, hv_server, checkpoint)
            vm_list.append(vm_name)
            index += 1

        return vm_list

    @staticmethod
    def copy_multiple_times(source_path, destination_folder, count=1):
        path_list = []
        base_name_list = ntpath.basename(source_path).split('.')
        for index in range(count):
            item_name = ''.join([base_name_list[0], str(index + 1)])
            if len(base_name_list) > 1:
                destination_path = os.path.join(destination_folder, '.'.join([item_name, base_name_list[1]]))
            else:
                destination_path = os.path.join(destination_folder, item_name)
            logger.debug('Copying %s to %s' % (source_path, destination_path))
            VirtualMachine.execute_command(['powershell', 'Copy-Item',  '-Recurse', source_path, destination_path])
            path_list.append(destination_path)

        return path_list

    @staticmethod
    def copy_lisa_folder(main_lisa_path, work_folder, count=1):
        work_lisa_path = os.path.join(work_folder, 'lisa')
        if not os.path.exists(work_lisa_path):
            os.mkdir(work_lisa_path)

        for item_path in os.listdir(main_lisa_path):
            full_path = os.path.join(main_lisa_path, item_path)
            if os.path.normpath(full_path) != os.path.normpath(work_folder):
                VirtualMachine.execute_command(['powershell', 'Copy-Item', full_path, work_lisa_path, '-recurse'])

        if count > 1:
            lisa_list = RunLISA.copy_multiple_times(work_lisa_path, work_folder, count=count-1)
            lisa_list.append(work_lisa_path)
            return lisa_list
        else:
            return [work_lisa_path]

    @staticmethod
    def setup_lisa_run(vm_config, pool_count=4, snapshot_name='icabase'):
        logger.debug('Running test run setup with - %s' % vm_config)
        main_lisa_path = RunLISA.get_lisa_path()
        logging.info('Using the following path for the main LISA folder - %s' % main_lisa_path)

        try:
            vhd_folder = vm_config['main']['vhdPath']
        except KeyError:
            vhd_folder = VirtualMachine.get_default_vhd_path()
            logger.info('No vhdFolder parameter provided. Defaulting to %s' % vhd_folder)

        vms['main'] = RunLISA.create_vms(
            RunLISA.copy_multiple_times(
                vm_config['main']['vhdPath'], vhd_folder, count=pool_count
                ), vm_base_name=vm_config['main']['name'])
        try:
            vms['dependency'] = RunLISA.create_vms(
                RunLISA.copy_multiple_times(
                    vm_config['dependency']['vhdPath'], vhd_folder
                    ), vm_base_name=vm_config['dependency']['name'])
        except KeyError:
            logger.debug('No dependency vm info found')
        logger.debug('Created vms - %s' % vms)

        work_folder = os.path.join(main_lisa_path, 'test_run')
        if os.path.exists(work_folder):
            VirtualMachine.execute_command(['powershell', 'Remove-Item','-Recurse', '-Force', work_folder])
        os.mkdir(work_folder)
        lisa_list = RunLISA.copy_lisa_folder(main_lisa_path, work_folder, count=pool_count)
        logger.debug('LISA folders list - %s' % lisa_list)

        return  main_lisa_path, vms, lisa_list


def validate_config(config_dict):
    missing_filed = ''
    if 'tests' not in config_dict.keys():
        missing_filed = 'tests'
    elif 'vms' not in config_dict.keys():
        missing_filed = 'vms'
    elif 'generalConfig' not in config_dict.keys():
        missing_filed = 'generalConfig'
    
    if missing_filed:
        logger.error('Field %s not found' % missing_filed)
        logger.error('Look over the demo config file for more details')
        return False
    else:
        return True


if __name__ == '__main__':
    setup_logging(default_level=3)
    
    config_file_path = r'.\\lisa_parser\\test_run_conf.json'
    if len(sys.argv) == 2:
        config_file_path  = sys.argv[1]
            
    if not os.path.exists(config_file_path):
        logger.error('Specified config file not found - %s' %  config_file_path)
        sys.exit(1)

    with open(config_file_path) as config_data:
        config_dict = json.load(config_data)
        if not validate_config(config_dict):
            sys.exit(1)
    
    pool_count = 4
    try:
        pool_count = int(config_dict['processes'])
    except KeyError:
        logger.info('Processes field not provided. Defaulting to %d' % pool_count)
        
    main_lisa_path, vms, lisa_folders = RunLISA.setup_lisa_run(config_dict['vms'], pool_count=pool_count, snapshot_name=config_dict['generalConfig']['testParams']['snapshotName'])

    proc_manager = multiprocessing.Manager()
    vms_queue = proc_manager.Queue()
    lisa_queue = proc_manager.Queue()
    

    for i in range(pool_count):
        vms_queue.put(vms[i])
        lisa_queue.put(lisa_folders[i])
    
    logger.info('Creating the tests list')
    xml_list = RunLISA.create_test_list(config_dict['tests'], os.path.join(main_lisa_path, 'xml'))

    # Check for logPath
    try:
        logPath = config_dict['generalConfig']['logPath']
        logger.debug('Using %s for tests log output' % logPath)
    except KeyError:
        logPath = os.path.join(main_lisa_path, 'TestResults')
        logger.debug('Log path was not specified for %s. Using default path' % xml_path)
    
    try:
        lisa_params = config_dict['lisaParams']
    except KeyError:
        lisa_params = []
        logger.info('No extra params for LISA run have been specified')

    logger.info('Starting %d parallel LISA runs' % pool_count)
    proc = multiprocessing.Pool(pool_count)
    result = proc.map(RunLISA(lisa_queue, vms_queue, config_dict['generalConfig'], main_lisa_path, lisa_params), xml_list)

    logger.info('Test run completed')
    # Parse results if specified
    if 'parseResults' in config_dict:
        logger.info('Parsing results')
        logger.debug('Using the following paths - %s' % result)
        parser_args = ["xml_file", "ica_log_file"]
        for key, value in config_dict['parseResults'].iteritems():
            parser_args.append(key)
            parser_args.append(value)
        for paths_tuple in result:
            if path_tuple:
                parser_args[0] = path_tuple[0]
                parser_args[1] = os.path.join(path_tuple[1], 'ica.log')
                main(parser_args)
