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

def apply_patch(patch_file, dry_run=False):
    if dry_run:
        dry_run = '--dry-run'
    else:
        dry_run = ''

    cmd = ['patch', dry_run, '--ignore-whitespace',
            '-p1', '-F1', '-f', '<', patch_file
    ]
    return run_command(cmd)

def build(clean=False):
    base_build_cmd = ['make', '-C']
    drivers = '/lib/modules/$(uname -r)/build M=`pwd`'
    daemons = './tools'
    # First run the clean commands
    run_command(base_build_cmd, [drivers, 'clean'])
    run_command(base_build_cmd, [daemons, 'clean'])
    
    if not clean:
        run_command(base_build_cmd + [drivers])
        run_command(base_build_cmd + [daemons])


def copy_reject_file(patch_path):
    patch_folder_path, patch_file = os.path.split(os.path.abspath(patch_path))
    folder_name = 'failed'
    folder_path = os.path.join(patch_folder_path, folder_name)
    if not os.path.exists(folder_path): os.mkdir(folder_path)
    copy('{}.rej'.format(patch_file), folder_path)


@change_dir
def test_patch(patch_path, repo_path):
    os.chdir(repo_path)
    logger.info('Normalizing the paths in the patch')
    normalize_path(patch_path)
    
    try:
        logger.info("Applying patch")    
        apply_patch(patch_path)
    except RuntimeError as exc:
        logger.error("Failed to apply patch")
        copy_reject_file(patch_path)
        raise exc
    
    try:
        logger.info("Building LIS drivers and daemons")
        build()
    except RuntimeError as exc:
        logger.error("Unable to build project")
        raise exc 

    try:
        logger.info("Running repo cleanup")
        build(clean=True)
    except RuntimeError:
        logger.warning("Failed to run project cleanup")

def test_patches(patches_folder):
    backup_folder = os.path.join(patches_folder, 'original')
    if not os.path.exists(backup_folder): os.mkdir(backup_folder)
    for patch_file in os.listdir(patches_folder):
        patch_path = os.path.join(patches_folder, patch_file)
        copy(patch_path, backup_folder)
        with open(patch_path, 'r') as f:
            commit_id = f.readline().strip().split()[1]
        repo_path = './lis-next-{}'.format(commit_id)
        if os.path.exists(repo_path): rmtree(repo_path)
        clone_repo(LIS_NEXT_REPO_URL, repo_path)
        try:
            test_patch(patch_path, os.path.join(repo_path, 'hv-rhel7.x/hv'))
        except RuntimeError:
            logger.error("Patch test failed.")
