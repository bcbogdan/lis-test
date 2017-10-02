import subprocess
import logging
import argparse
import os
from constants import LINUX_REPO_URL, LINUX_NEXT_REMOTE, LIS_NEXT_REPO_URL, BUILDS_PATH
logger=logging.getLogger(__name__)

def change_dir(func):
    def wrapper(*args, **kwargs):
        cur_dir = os.getcwd()
        result = func(*args, **kwargs)
        os.chdir(cur_dir)
        return result
    return wrapper

def get_arg_parser():
    parser = argparse.ArgumentParser()
    sub_parsers = parser.add_subparsers(help='CLI Commands')
    
    create_patch = sub_parsers.add_parser('create', help='Create patches in folder')
    create_patch.add_argument(
        '-d', '--date',
        help='Date since last commit. Default - a day ago',
        default="1 day ago")
    create_patch.add_argument(
        '-a', '--author',
        help='Specific commit author',
        default=None
    )
    create_patch.add_argument(
        '-l', '--linux-repo',
        help='Linux repo path',
        default='None'
    )
    create_patch.add_argument(
        '-p', '--patches-folder',
        help='Folder where the patch files will be created',
        default='./patches'
    )
    create_patch.add_argument(
        '-v', '--verbose',
        help='Verbose logging',
        action='store_true',
        default=False
    )
    create_patch.add_argument(
        '-f', '--find',
        help='Perform find step',
        action='store_true',
        default=False
    )
    
    apply_patches = sub_parsers.add_parser('apply', help='Apply patches from a specified folder')
    apply_patches.add_argument(
        'patches_folder',
        help='Location of the patch files that will be applied',
        default='.\patches'
    )
    apply_patches.add_argument(
        '-p', '--project',
        help='Remote repository on which patches will be applied',
        default=LIS_NEXT_REPO_URL
    )
    apply_patches.add_argument(
        '-o', '--output-location',
        help='Location where the new builds will be saved',
        default=BUILDS_PATH
    )

    compile_patches = sub_parsers.add_parser('compile', help='Compile projects')
    compile_patches.add_argument(
        'builds_path',
        help='Location of the builds that will be compiled',
        default='/root/builds'
    )

    parse_patches = sub_parsers.add_parser('parse', help='Build projects')
    parse_patches.add_argument(
        'log_folder',
        help='Location of the log files that will be parsed'
    )

    commit_patches = sub_parsers.add_parser('commit', help='Commit patches')
    commit_patches.add_argument(
        'builds_folder'
    )
    commit_patches.add_argument(
        '-e', '--email'
    )
    commit_patches.add_argument(
        '-n', '--name'
    )
    commit_patches.add_argument(
        '-p', '--password'
    )
    commit_patches.add_argument(
        '-u', '--username'
    )

    server = sub_parsers.add_parser('serve', help='Start patch server')
    server.add_argument(
        'expected_requests', 
        type=int,
        help='Number of POST requests expected'
    )
    server.add_argument(
        '-a', '--address',
        default='0.0.0.0'
    )
    server.add_argument(
        '-p', '--port',
        default=80,
        type=int
    )
    return parser

def clone_repo(repo_url, repo_path):
    return run_command([
        'git', 'clone', repo_url,
        repo_path
    ])

def add_remote(remote_name, remote_url):
    return run_command([
        'git', 'remote', 'add',
        remote_name, remote_url
    ])

@change_dir
def manage_linux_repo(repo_path, create=False):
    if create:
        clone_repo(LINUX_REPO_URL, repo_path)
        os.chdir(repo_path)
        add_remote('linux-next', LINUX_NEXT_REMOTE)
        run_command(['git', 'fetch', 'linux-next']) 
        run_command(['git', 'fetch', '--tags', 'linux-next'])
    else:
        os.chdir(repo_path)
        run_command(['git', 'checkout', 'master'])
        run_command(['git', 'remote', 'update'])

def run_command(command_arguments):
    ps_command = subprocess.Popen(
    command_arguments,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE
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
