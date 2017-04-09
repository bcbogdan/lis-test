import json
from virtual_machine import VirtualMachine
from file_parser import ParseXML
from envparse import env
import shutil
from config import setup_logging
import multiprocessing
import Queue
import logging
import os
import ntpath
import sys
import pdb

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

    def __init__(self, lisa_path_queue, vm_queue, tests_config, lisa_path):
        self.lisa_queue = lisa_path_queue
        self.vm_queue = vm_queue
        self.config = tests_config
        self.main_lisa_path = lisa_path

    def __call__(self, xml_path):
        logger.info('Editing %s' % xml_path)
        vm_name = self.vm_queue.get()
        self.config['vmName'] = vm_name
        xml_obj = ParseXML(xml_path)
        xml_obj.edit_vm_conf(self.config)

        try:
            xml_obj.global_config.find('logfileRootDir').text = self.config['logPath']
        except KeyError:
            xml_obj.global_config.find('logfileRootDir').text = os.path.join(self.main_lisa_path, 'TestResults')
            logger.debug('Log path was not specified for %s. Using default path' % xml_path)
        
        xml_obj.tree.write(xml_path)
        lisa_path = self.lisa_queue.get()
        os.chdir(lisa_path)
        print(os.getcwd())
        print(xml_path)
        lisa_bin = os.path.join(lisa_path, 'lisa.ps1')
        logger.info('Running %s on %s with %s' % (xml_path, vm_name, lisa_path))
        try:
            VirtualMachine.execute_command(['powershell', lisa_bin, 'run', xml_path, '-dbgLevel', '5'])
        except RuntimeError:
            logger.error('Test run exited with errors')
        self.vm_queue.put(vm_name)
        self.lisa_queue.put(lisa_path)

    @staticmethod
    def create_test_list(test_config_dict, lisa_abs_xml_path):

        if 'run' in test_config_dict.keys():
            xml_list = [
                os.path.join(lisa_abs_xml_path, xml_file) for xml_file in test_config_dict['run'] if xml_file in RunLISA.xml_files
                ]
        elif 'skip' in test_config_dict.keys():
            xml_list = [
                os.path.join(lisa_abs_xml_path, xml_file) for xml_file in RunLISA.xml_files if xml_file not in test_config_dict['skip']
                ]
        else:
            xml_list = [
                os.path.join(lisa_abs_xml_path, xml_file) for xml_file in RunLISA.xml_files
                ]

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

        work_folder = os.path.join(main_lisa_path, 'test_run')
        if os.path.exists(work_folder):
            VirtualMachine.execute_command(['powershell', 'Remove-Item','-Recurse', '-Force', work_folder])
        os.mkdir(work_folder)

        vhd_destination_folder = os.path.join(work_folder, 'vhds')
        if not os.path.exists(vhd_destination_folder):
            os.makedirs(vhd_destination_folder)

        vms = {}
        vms['main'] = RunLISA.create_vms(
            RunLISA.copy_multiple_times(
                vm_config['main']['vhdPath'], vhd_destination_folder, count=pool_count
                ), vm_base_name=vm_config['main']['name'])
        try:
            vms['dependency'] = RunLISA.create_vms(
                RunLISA.copy_multiple_times(
                    vm_config['dependency']['vhdPath'], vhd_destination_folder
                    ), vm_base_name=vm_config['dependency']['name'])
        except KeyError:
            logger.debug('No dependency vm info found')

        lisa_list = RunLISA.copy_lisa_folder(main_lisa_path, work_folder, count=pool_count)

        return  main_lisa_path, vms, lisa_list


if __name__ == '__main__':
    setup_logging(default_level=3)

    logging.info(os.getcwd())
    with open(r'.\\lisa_parser\\test_run_conf.json') as config_data:
        config_dict = json.load(config_data)
    
    pool_count = 4

    try:
        pool_count = int(config_dict['processes'])
    except KeyError:
        logger.info('Processes field not provided. Defaulting to %d' % pool_count)
        
    main_lisa_path, vms, lisa_folders = RunLISA.setup_lisa_run(config_dict['vms'], pool_count=pool_count, snapshot_name=config_dict['testsConfig']['testParams']['snapshotName'])
    
    
    proc_manager = multiprocessing.Manager()
    vms_queue = proc_manager.Queue()
    lisa_queue = proc_manager.Queue()
    
    for i in range(pool_count):
        vms_queue.put(vms[i])
        lisa_queue.put(lisa_folders[i])
    
    xml_list = RunLISA.create_test_list(config_dict['tests'], os.path.join(main_lisa_path, 'xml'))

    proc = multiprocessing.Pool(pool_count)
    result = proc.map(RunLISA(lisa_queue, vms_queue, config_dict['testsConfig'], main_lisa_path), xml_list)
