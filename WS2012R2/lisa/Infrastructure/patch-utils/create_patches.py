import os
import logging
from shutil import rmtree
from utils import change_dir, run_command
from constants import FILES_MAP
logger=logging.getLogger(__name__)

def get_commit_list(linux_repo_path, date='a day ago', author=None):
    commit_list = []
    commit_subjects = []
    for linux_path, lis_next_path in FILES_MAP.items():
        commits = get_commits(linux_path, date=date, author=author)
        commit_subjects.extend(get_commits(linux_path, date=date, author=author, format='%h---%s'))
        commit_list.extend(commits)
    
    logger.info('Selected the following commits:')
    [logger.info(subject) for subject in commit_subjects]

    return set(commit_list)

def create_patch_files(commit_list, patches_folder='./patches'):
    if os.path.exists(patches_folder): rmtree(patches_folder)
    os.mkdir(patches_folder)
    patch_list = []
    for commit_id in commit_list:
        patch_list.append(create_patch(commit_id, patches_folder))
    return patch_list

def get_commits(path, author=None, date=None, format='%H'):
    git_cmd = ['git', 'log']
    if author: git_cmd.extend(['--author', author])
    if date: git_cmd.extend(['--since', date])

    git_cmd.append('--pretty=format:{}'.format(format))
    git_cmd.extend(['--', path])

    return run_command(git_cmd).splitlines()

def create_patch(commit_id, destination):
    command = [
        'git', 'format-patch', '-1',
        commit_id, '-o', destination
        ]

    return run_command(command).strip()

