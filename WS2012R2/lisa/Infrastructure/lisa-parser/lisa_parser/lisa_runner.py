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
from shutil import rmtree
from config import setup_logging
from lisa_parser import main
from collections import defaultdict
from time import time
import lisa_utils
import json
import multiprocessing
import Queue
import logging
import os
import ntpath
import sys

logger = logging.getLogger(__name__)
proc_logger = multiprocessing.log_to_stderr()
proc_logger.setLevel(logging.INFO)
# TODO
# multiprocessing logging - config logging for each process
# argument parser - config file path, skip setup
# add documentation

class RunLISA(object):
    xml_files = [
        'CoreTests.xml', 'KvpTests.xml', 'Kdump_Tests.xml',
        'LTP.xml', 'NET_Tests.xml', 'NET_Tests_IPv6.xml',
        'NMI_Tests.xml', 'Production_Checkpoint.xml', 'STOR_VHD.xml',
        'STOR_VHDX.xml', 'STOR_VHDXResize.xml', 'FCopy_Tests.xml',
        'STOR_VSS_Backup_Tests.xml', 'StressTests.xml', 'VMBus_Tests.xml', 'lsvmbus.xml'
    ]

    def __init__(self, lisa_path_queue, vm_queue, general_config, lisa_path, lisa_params):
        self.lisa_queue = lisa_path_queue
        self.vm_queue = vm_queue
        self.config = general_config
        self.main_lisa_path = lisa_path
        self.params = lisa_params

    def __call__(self, xml_dict):
        proc_logger.info('Editing %s' % xml_dict['name'])
        vm_name = self.vm_queue.get()
        self.config['vmName'] = vm_name
        xml_obj = ParseXML(xml_dict['path'])
        xml_obj.edit_vm_conf(self.config)
        xml_obj.global_config.find('logfileRootDir').text = self.config['logPath']

        if 'skip' in xml_dict:
            proc_logger.info('Removing %s from %s' % (xml_dict['skip'], xml_dict['name']))
            xml_obj.remove_tests(xml_dict['skip'])
        
        if 'params' in xml_dict:
            proc_logger('Editing parameters %s for %s' % (xml_dict['params'], xml_dict['name']))
            # Check for parameters that require vmName
            for test_name, params in xml_dict['params'].iteritems():
                if 'vmName' in params.keys():
                    params['vmName'] = vm_name
            xml_obj.edit_test_params(xml_dict['params'])
            
        if 'extraTests' in xml_dict:
            for index, value in xml_dict['extraTests']:
                xml_obj.insert_test(value, index)

        xml_obj.tree.write(xml_dict['path'])

        lisa_path = self.lisa_queue.get()
        os.chdir(lisa_path)
        lisa_bin = os.path.join(lisa_path, 'lisa.ps1')
        lisa_cmd_list = ['powershell', lisa_bin, 'run', xml_dict['path']]
        lisa_cmd_list.extend(self.params)
        proc_logger.info('Running the following LISA command - %s' % ' '.join(lisa_cmd_list))
        ica_log = os.path.join(self.config['logPath'], xml_dict['name'] +'.log')
        try:
            lisa_output = VirtualMachine.execute_command(lisa_cmd_list)
            ica_log = os.path.join(self.config['logPath'], xml_dict['name'] +'.log')
        except RuntimeError as lisa_error:
            proc_logger.error('Test run exited with error code')
            proc_logger.error(lisa_error)
        
        sleep(10)
        
        #Get the full path of the log files
        test_suite = xml_dict['name'].split('.')[0]
        log_folders = [os.path.join(self.config['logPath'] , dir) for dir in os.listdir(self.config['logPath']) if test_suite in dir ]
        self.vm_queue.put(vm_name)
        self.lisa_queue.put(lisa_path)
        log_folder = max(log_folders, key=os.path.getmtime)
        proc_logger.info('Test log folder - %s' % log_folder)
        
        return xml_dict['path'], log_folder

    @staticmethod
    def create_test_list(xml_dict, lisa_abs_xml_path, tests_config=False, extra_tests=False):
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
                try:
                    xml_dict.update(tests_config[xml_dict['name']])
                except KeyError:
                    logger.debug('No extra config found for %s' % xml_dict['name'])
                xml_dict['path'] = os.path.join(lisa_abs_xml_path, xml_dict['name'])
                logger.debug('Processed xml - %s', xml_dict)
        else:
            for xml_dict in xml_list:
                xml_dict['path'] = os.path.join(lisa_abs_xml_path, xml_dict['name'])
                logger.debug('Processed xml - %s', xml_dict)

        if extra_tests:
            for xml_dict in xml_list:
                xml_dict['extraTests'] = extra_tests
 
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
    # TODO: Add option to specify work folder path
    work_folder_name = 'test_run'
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

    lisa_setup_start = time()
    logger.debug('Running test run setup with - %s' % config_dict)

    pool_count = int(config_dict['processes'])
    logger.info('LISA will run on {} different processes'.format(pool_count))

    logger.info('Copying VHDs')
    vhd_folder = False
    vhd_copy_process_start = time()
    if 'vhdFolder' in config_dict['vms']['main'].keys(): vhd_folder = config_dict['vms']['main']['vhdFolder']
    pool_list = lisa_utils.init_copy_vhds(config_dict['vms']['main']['vhdPath'], count=pool_count)
    logger.info(pool_list)
    vhd_list = multiprocessing.Pool(pool_count).map(lisa_utils.copy_item, pool_list)
    vhd_copy_process_time = time() - vhd_copy_process_start
    logger.info('VHD list {}'.format(vhd_list))
    logger.info('Elapsed time for VHD copy process - {}'.format(vhd_copy_process_time))

    
    main_lisa_path = RunLISA.get_lisa_path()
    logging.info('Using the following path for the main LISA folder - %s' % main_lisa_path)
    vms = lisa_utils.create_vms(vhd_list, vm_base_name=config_dict['vms']['main']['name'])
    # TODO: Create dependency VM
    logger.debug('Created vms - %s' % vms)

    work_folder = os.path.join(main_lisa_path, work_folder_name)
    if os.path.exists(work_folder): VirtualMachine.execute_command(['powershell', 'Remove-Item','-Recurse', '-Force', work_folder])
    os.mkdir(work_folder)
    lisa_folders = lisa_utils.copy_lisa_folder(main_lisa_path, work_folder, count=pool_count)
    logger.debug('LISA folders list - %s' % lisa_folders)
    logger.info('Elapsed time for LISA setup - {}'.format(time() - lisa_setup_start))

    proc_manager = multiprocessing.Manager()
    vms_queue = proc_manager.Queue()
    lisa_queue = proc_manager.Queue()

    for i in range(pool_count):
        vms_queue.put(vms['main'][i])
        lisa_queue.put(lisa_folders[i])

    
    extra_tests = False
    if 'extraTests' in config_dict:
        extra_tests = config_dict['extraTests']

    logger.info('Creating the tests list')
    xml_list = RunLISA.create_test_list(config_dict['tests'], os.path.join(main_lisa_path, 'xml'), config_dict['testsConfig'], extra_tests)

    # Check for logPath
    try:
        logPath = config_dict['generalConfig']['logPath']
        logger.debug('Using %s for tests log output' % logPath)
    except KeyError:
        config_dict['generalConfig']['logPath'] = os.path.join(main_lisa_path, 'TestResults')
        logger.debug('Log path was not specified for %s. Using default path' % config_dict['generalConfig']['logPath'])
    
    try:
        lisa_params = []
        for key, value in config_dict['lisaParams'].iteritems():
            lisa_params.append(key)
            lisa_params.append(value)
    except KeyError:
        lisa_params = []
        logger.info('No extra params for LISA run have been specified')

    #multiprocessing.log_to_stderr()
    logger.info('Starting %d parallel LISA runs' % pool_count)
    proc = multiprocessing.Pool(pool_count)
    result = proc.map(RunLISA(lisa_queue, vms_queue, config_dict['generalConfig'], main_lisa_path, lisa_params), xml_list)

    logger.info('Test run completed')
    logger.debug(result)
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
