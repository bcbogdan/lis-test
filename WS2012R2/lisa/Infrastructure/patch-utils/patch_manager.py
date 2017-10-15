import logging
import os
from shutil import rmtree, move
from json import load
from utils import apply_patch, normalize_path, build, get_commit_info, parse_results
from server import start_server, PatchServerHandler, PatchServer
from urlparse import urlparse, urlunparse
from git import GitWrapper

logger = logging.getLogger(__name__)

class PatchManager(object):
    def __init__(self, command, args):
        self.__dict__ = args.__dict__.copy()
        self.command = command
    
    def __call__(self):
        try:
            logger.info('Running %s command with the following arguments:' % self.command)
            logger.info(self.__dict__)
            method = getattr(self, self.command)
            method()
        except AttributeError:
            logger.error('Invalid command - {}'.format(self.command))

    def create(self):
        # check if valid path
        repo = GitWrapper(self.linux_repo)
        repo.update_from_remote(self.branch, self.remote_tag)

        with open(self.files_map) as data:
            files_map = load(data)
        commit_list = repo.get_commit_list(files_map, self.date, self.author)
        
        patch_list = repo.create_patches(commit_list, self.patches_folder)
        if len(patch_list) > 0:
            logger.info('Created the following patch files:')
            [logger.info(patch_path) for patch_path in patch_list]
        else:
            logger.info('No patches created.')

    def apply(self):
        patch_list = os.listdir(self.patches_folder)
        
        for patch_file in os.listdir(self.patches_folder):
            patch_path = os.path.join(self.patches_folder, patch_file)
            normalize_path(patch_path)

            repo_path = os.path.join(self.builds_path, patch_file)
            logger.info('Cloning into %s' % repo_path)
            repo = GitWrapper(repo_path, self.project)
            try:
                #TODO: Add internal path as parameter
                work_path = os.path.join(repo_path,'hv-rhel7.x/hv')
                logger.info('Appling patch on %s' % work_path)
                apply_patch(work_path, patch_path)
            except RuntimeError as exc:
                logger.error('Unable to apply patch %s on %s' % (patch_file, repo_path))
                with open('%s/%s.log' % (self.failures_path, patch_file), 'w') as log_file:
                    log_file.write(exc[1])
                    log_file.write(exc[2])
                move(repo_path, '%s/%s' % (self.failures_path, '%s-build' % patch_file))
                logger.error('Logs cand be found at %s' % (self.failures_path+patch_file+'.log'))            
    
    def compile(self):
        for build_folder in os.listdir(self.builds_path):
            build_path = os.path.join(self.builds_path, build_folder)
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
        commit_message = "RH7: {} <upstream:{}>"
        for project in os.listdir(self.builds_folder):
            project_path = os.path.join(self.builds_folder, project)
            patch_path = os.path.join(self.patch_files, project)
            commit_id, commit_desc = get_commit_info(patch_path)
            repo = GitWrapper(project_path)
            repo.config(name=self.name, email=self.email)
            repo.add_files(['*.h','*.c'])
            repo.commit(commit_message.format(commit_desc, commit_id))
            parsed_url = urlparse(self.remote_url)
            new_url = parsed_url._replace(netloc="{}:{}@{}".format(self.username, self.password, parsed_url.netloc))
            repo.push(urlunparse(new_url), self.branch)

    def parse(self):
        tested_patches = os.listdir(self.builds_path)
        result_dict = {}
        for log_file in os.listdir(self.results_path):
            log_path = os.path.join(self.results_path, log_file)
            with open(log_path, 'r') as log_content:
                results = parse_results(log_content, tested_patches)
                for patch_name, result in results.items():
                    if result != 'Passed':
                        logger.warning('%s failed on %s' % (patch_name, log_file))
                        build_path = os.path.join(self.builds_path, patch_name)
                        move(build_path, self.failures_path)

    def serve(self):
        PatchServerHandler.expected_requests = self.expected_requests
        PatchServerHandler.builds_path = self.builds_path
        for build in os.listdir(self.builds_path):
            PatchServerHandler.expected_results.append(build)
            PatchServerHandler.expected_results.append("install_%s" % build)
        PatchServerHandler.failures_path = self.failures_path
        PatchServerHandler.expected_results = os.listdir(self.builds_path)
        start_server(PatchServer, PatchServerHandler.check, host=self.address, port=self.port)
