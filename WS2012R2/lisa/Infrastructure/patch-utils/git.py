from utils import run_command
from shutil import rmtree
import os
import logging


logger=logging.getLogger(__name__)


class GitWrapper(object):
    base_cmd = ['git']

    def __init__(self, repo_path, remote_url=None):
        self.path = repo_path
        if remote_url:
            self.clone(remote_url, destination=repo_path)            


    def execute(self, arguments):
        return run_command(
            self.base_cmd.extend(arguments),
            work_dir=self.path
        )

    @staticmethod
    def clone(remote_url, destination=""):
        return run_command(
            GitWrapper.base_cmd.extend([
                'clone', remote_url, destination
            ])
        )
    
    def update_from_remote(self, local_branch, tag_name):
        self.execute(['checkout', 'master'])
        self.execute(['remote', 'update'])
        tag = self.execute(['tag', '-l', tag_name, '|', 'tail', '-n', '1'])
        self.execute(['checkout', '-b', local_branch, tag])

    def config(self, name, email):
        pass
    
    def add_files(self):
        pass
    
    def commit(self):
        pass

    def push(self, remote_addres, branch):
        pass

    def add_remote(self, remote_name, remote_url):
        return self.execute([
            'remote', 'add', remote_name, remote_url
            ])
    
    def fetch(self, remote_name, tags=False):
        cmd = ['fetch']
        if tags: cmd.append("--tags")
        return self.execute(cmd.append(remote_name))
    
    def manage_repo(self, remote_branch=None):
        #update linux repo - fetch from linux-next
        pass

    def log_path(self, path, author=None, date=None, format='%H'):
        git_cmd = ['log']
        if author: git_cmd.extend(['--author', author])
        if date: git_cmd.extend(['--since', date])

        git_cmd.append('--pretty=format:{}'.format(format))
        git_cmd.extend(['--', path])

        return self.execute(git_cmd).splitlines()
    
    def create_patch(self, commit_id, destination):
        return self.execute([
            'format-patch', '-1', commit_id,
            '-o', destination
            ]).strip()
        
    def create_patches(self, commit_list, patch_folder, reject_folder):
        if os.path.exists(patch_folder): rmtree(patch_folder)
        os.mkdir(patch_folder)
        patch_list = []
        for commit_id in commit_list:
            try:
                patch_list.append(self.create_patch(commit_id, patch_folder))
            except RuntimeError as exc:
                #TODO: Check error message format and fix it
                logger.error('Unable to create a patch file for {}'.format(commit_id))
                logger.error(exc)

        return patch_list

    def get_commit_list(self, files_map, date='a day ago', author=None):
        commit_list = []
        commit_subjects = []

        for linux_path, lis_next_path in files_map.items():
            commits = self.log_path(linux_path, date=date, author=author)
            commit_subjects.extend(self.log_path(linux_path, date=date, author=author, format='%h---%s'))
            commit_list.extend(commits)
    
        logger.info('Selected the following commits:')
        [logger.info(subject) for subject in commit_subjects]

        return set(commit_list)
