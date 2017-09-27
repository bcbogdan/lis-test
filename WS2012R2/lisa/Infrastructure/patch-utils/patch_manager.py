import logging
import os
from shutil import rmtree, copy
from utils import run_command, clone_repo, change_dir
from constants import LIS_NEXT_REPO_URL
import fileinput

logger=logging.getLogger(__name__)

def normalize_path(patch_path):
    replace_list = [
        ('--- a/drivers/hv', '--- a'), ('+++ a/drivers/hv', '+++ a'),
        ('--- a/drivers/net/hyperv', '--- a'), ('+++ b/drivers/net/hyperv', '+++ b'),
        ('--- a/drivers/scsi', '--- a'), ('+++ b/drivers/scsi', '+++ b'),
        ('--- a/tools/hv', '--- a/tools'), ('+++ b/tools/hv', '+++ b/tools'),
        ('--- a/arch/x86/include/asm/', '--- a/arch/x86/include/lis/asm/'),
        ('+++ b/arch/x86/include/asm/', '+++ b/arch/x86/include/lis/asm/'),
        ('+++ b/arch/x86/include/uapi/asm/', '+++ b/arch/x86/include/uapi/lis/asm/'),
        ('--- b/arch/x86/include/uapi/asm/', '--- a/arch/x86/include/uapi/lis/asm/'),
        ('--- b/drivers/pci/host/','--- a/'), ('+++ b/drivers/pci/host/','+++ b/')
    ]

    for to_search, to_replace in replace_list:
        for line in fileinput.input(patch_path, inplace=True):
            print line.replace(to_search, to_replace),

def apply_patch(build_folder, patch_file, dry_run=False):
    cmd = ['cd', build_folder, '&&', 'patch', '<', patch_file]
    return run_command(cmd)

def build(build_folder, clean=False):
    base_build_cmd = ['cd', build_folder, '&&', 'make', '-C']
    drivers = '/lib/modules/$(uname -r)/build M=`pwd`'
    daemons = './tools'
    # First run the clean commands
    run_command(base_build_cmd + [drivers, 'clean'])
    run_command(base_build_cmd + [daemons, 'clean'])
    
    if not clean:
        run_command(base_build_cmd + [drivers])
        run_command(base_build_cmd + [daemons])


def copy_reject_file(patch_path):
    patch_folder_path, patch_file = os.path.split(os.path.abspath(patch_path))
    folder_name = 'failed'
    folder_path = os.path.join(patch_folder_path, folder_name)
    if not os.path.exists(folder_path): os.mkdir(folder_path)
    copy('{}.rej'.format(patch_file), folder_path)


def apply_patches(patches_folder, builds_folder):
    if os.path.exists(builds_folder): rmtree(builds_folder) 
    os.mkdir(builds_folder)

    for patch_file in os.listdir(patches_folder):
        patch_path = os.path.join(patches_folder, patch_file)
        repo_path = os.path.join(builds_folder, patch_file)
        logger.info('Cloning into %s' % repo_path)
        clone_repo(LIS_NEXT_REPO_URL, repo_path)
        try:
            apply_patch(repo_path, patch_path)
            logger.info('Successfully aplied patch on %s' % repo_path)
        except RuntimeError as exc:
            logger.error('Unable to apply patch %s' % patch_file)
            logger.error(exc)

def compile_patches(builds_folder):
    for build_folder in os.listdir(builds_folder):
        build_path = os.path.join(builds_folder, build_folder)
        try:
            build(build_path)
            logger.info('Successfully compiled %s' % build_path)
        except RuntimeError as exc:
            logger.error('Unable to build %s' % build_path)
            logger.error(exc)
        
        try:
            build(build_path, clean=True)
        except RuntimeError as exc:
            logger.error('Error while running cleanup for %s' % build_path)
            logger.error(exc)
