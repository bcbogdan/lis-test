import subprocess
import logging
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

def run_command(command_arguments, work_dir='./'):
    ps_command = subprocess.Popen(
    command_arguments,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    cwd=work_dir
    )
    logger.debug('Running command {}'.format(command_arguments))
    stdout_data, stderr_data = ps_command.communicate()

    logger.debug('Command output %s', stdout_data)
    if ps_command.returncode != 0:
        raise RuntimeError(
            "Command failed, status code %s stdout %r stderr %r" % (
                ps_command.returncode, stdout_data, stderr_data
            )
        )
    else:
        return stdout_data
