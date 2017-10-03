import logging
import os
from shutil import rmtree, move
from json import load
from utils import apply_patch, normalize_path
from server import start_server, PatchServerHandler, PatchServer
from git import GitWrapper

logger = logging.getLogger(__name__)

class PatchManager(object):
    def __init__(self, command, args):
        self.__dict__ = args.__dict__.copy()
        self.command = command
    
    def __call__(self):
        try:
            method = getattr(self, self.command)
            method()
        except AttributeError:
            logger.error('Invalid command - {}'.format(self.command))

    def create(self):
        repo = GitWrapper(self.linux_repo)
        repo.update_from_remote(self.branch, self.remote_tag)

        with open(self.files_map) as data:
            files_map = load(data)
        commit_list = repo.get_commit_list(files_map, self.date, self.author)
        
        patch_list = repo.create_patch_files(commit_list, self.patches_folder)
        if len(patch_list) > 0:
            logger.info('Created the following patch files:')
            [logger.info(patch_path) for patch_path in patch_list]
        else:
            logger.info('No patches created.')

    def apply(self):
        if os.path.exists(self.builds_folder): rmtree(self.builds_folder) 
        os.mkdir(self.builds_folder)

        for patch_file in os.listdir(self.patches_folder):
            patch_path = os.path.join(self.patches_folder, patch_file)
            normalize_path(patch_path)

            repo_path = os.path.join(self.builds_folder, patch_file)
            logger.info('Cloning into %s' % repo_path)
            repo = GitWrapper(repo_path, self.remote_repo)
            try:
                apply_patch(repo_path, patch_path)
                logger.info('Successfully aplied patch on %s' % repo_path)
            except RuntimeError as exc:
                logger.error('Unable to apply patch %s' % patch_file)
                logger.error(exc)
                move(patch_path, self.failures_path)

    def compile(self):
        for build_folder in os.listdir(self.builds_folder):
            build_path = os.path.join(self.builds_folder, build_folder)
            try:
                build(build_path)
                logger.info('Successfully compiled %s' % build_path)
            except RuntimeError as exc:
                logger.error('Unable to build %s' % build_path)
                logger.error(exc)
                move(build_path, self.failures_path)
            
            try:
                build(build_path, clean=True)
            except RuntimeError as exc:
                logger.error('Error while running cleanup for %s' % build_path)
                move(build_path, self.failures_path)
                logger.error(exc)

    def commit(self):
        commit_message =  "RH${RHELVERSION}:$commit_desc <upstream:$commit_id>"
        for project in  os.listdir(self.projects_path):
            project_path = os.path.join(self.projects_path, project)
            repo = GitWrapper(project_path)
            repo.config(name=self.name, email=self.email)
            repo.add_files(['.','./\*.h','./\*.c'])
            repo.commit_changes()
            repo.push(self.remote_url, self.branch)

    def serve(self):
        PatchServerHandler.expected_requests = self.expected_requests
        start_server(PatchServer, PatchServerHandler.check, host=self.address, port=self.port)
