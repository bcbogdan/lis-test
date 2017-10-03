import argparse

LIS_NEXT_REPO_URL = 'https://github.com/LIS/lis-next.git'
LINUX_REPO_URL = 'https://github.com/torvalds/linux.git'
LINUX_NEXT_REMOTE = 'https://git.kernel.org/pub/scm/linux/kernel/git/next/linux-next.git'
BUILDS_PATH = '/root/builds'
FAILURES_PATH = '/root/failed'

FILES_MAP = {
    "drivers/hv": "hv/",
    "tools/hv": "hv/tools/",
    "drivers/net/hyperv": "hv/"
}

def get_arg_parser():
    parser = argparse.ArgumentParser()
    sub_parsers = parser.add_subparsers(help='CLI Commands')
    
    create_patch = sub_parsers.add_parser(
        'create', 
        help='Create patch files from previous commits'
    )
    create_patch.add_argument(
        '-d', '--date',
        help='Date used to check commit history',
        default="1 day ago")
    create_patch.add_argument(
        '-a', '--author',
        help='Specific commit author',
        default=None
    )
    create_patch.add_argument(
        '-l', '--linux-repo',
        help='Directory containing a local linux repository',
        default='None'
    )
    create_patch.add_argument(
        '-p', '--patches-folder',
        help='Location of the patch files',
        default='./patches'
    )
    create_patch.add_argument(
        '-t', '--remote_tag',
        help='Tag name',
        default='next-*'
    )
    create_patch.add_argument(
        '-b', '--branch',
        help='Local branch name',
        default='patch-automation'
    )
    create_patch.add_argument(
        '-m', '--files_map',
        help='JSON file containing a mapping between linux tree and project tree',
        default='./map.json'
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