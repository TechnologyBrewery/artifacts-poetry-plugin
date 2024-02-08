from poetry.publishing.uploader import Uploader
from poetry.utils.authenticator import Authenticator
from poetry.core.packages.package import Package
from poetry.factory import Factory
from poetry.config.config import Config
import os
from pathlib import Path
from typing import List
import logging

logger = logging.getLogger(__name__)


class RepoData:
    def __init__(self, url, username, password):
        self.url = url
        self.username = username
        self.password = password

    def url(self):
        return self.url

    def username(self):
        return self.username

    def password(self):
        return self.password


class ArtifactsDeployHelper:
    def get_repository_data(self, config, repo_name, io):
        """Gets the URL, username, and password from the poetry configuration for the given repo name"""
        err_msg = f"username and password are required. Please verify that your poetry config for this repository is correct for repository {repo_name}"
        url = config.get(f"repositories.{repo_name}.url")
        if url is None:
            raise RuntimeError(f"Repository {repo_name} is not defined")
        authenticator = Authenticator(config, io)
        auth = authenticator.get_http_auth(repo_name)
        username = None
        password = None
        if auth:
            username = auth.username
            password = auth.password
        else:
            raise RuntimeError(err_msg)
        if username is None or password is None:
            raise RuntimeError(err_msg)
        return RepoData(url, username, password)

    def get_poetry_packages(self, poetry) -> List[Package]:
        """Gets packages from the given poetry.lock file"""
        locker = poetry.locker
        repository = locker.locked_repository()
        return repository.packages

    def get_cached_dependency_files(self, cache_dir):
        """Gets all wheel file locations for the given cache directory"""
        dependency_files = {}
        for root, dirs, files in os.walk(cache_dir):
            for file in files:
                if file.endswith(".whl") or file.endswith(".tar.gz"):
                    dependency_files[file] = Path(os.path.join(root, file))
        return dependency_files

    def get_deploy_non_deploy_packages(self, packages: List[Package], dependency_files):
        """Adds the wheel file locations for each package's files"""
        non_deployable_packages = []
        deployable_packages = []
        for package in packages:
            file_found = False
            for file_info in package.files:
                if file_info["file"] in dependency_files:
                    file_found = True
                    file_info["url"] = dependency_files[file_info["file"]]
            if file_found:
                deployable_packages.append(package)
            else:
                non_deployable_packages.append(package)
        return deployable_packages, non_deployable_packages

    def upload_poetry_packages(self, poetry_list, url, username, password, io):
        """Deploys packages from all poetry objects in the given list"""
        deploy_set = set()
        for poetry in poetry_list:
            uploader = Uploader(poetry, io)
            uploader.auth(username=username, password=password)
            session = uploader.make_session()
            self.upload_packages(
                poetry.deployable_packages, deploy_set, uploader, session, url
            )

    def upload_packages(self, packages, deploy_set, uploader, session, url):
        """Deploys all packages if they do not exist in the deploy set to the given repository url"""
        for package in packages:
            uploader._package = package
            for file_info in package.files:
                if "url" in file_info and file_info["url"] not in deploy_set:
                    deploy_set.add(file_info["url"])
                    uploader._upload_file(
                        session, url, file=file_info["url"], skip_existing=True
                    )

    def get_project_dist_package(self, poetry):
        """Adds the generated package to the list of packages with its associated wheel file"""
        project_dist_path = os.path.join(poetry.root_dir, "dist")
        project_package = poetry.package
        for root, dirs, files in os.walk(project_dist_path):
            for file in files:
                if file.endswith(".whl") or file.endswith(".tar.gz"):
                    file_data = {"file": file, "url": Path(os.path.join(root, file))}
                    project_package.files.append(file_data)
        return project_package

    def get_all_poetry(self, path, downstream):
        """If downstream is true, gets all poetry objects starting from the given path.
        If false, will only get the poetry objects at the given path
        """
        poetry_list = []
        if downstream is False:
            poetry = self.get_poetry(path, os.listdir(path))
            if poetry is not None:
                poetry_list.append(poetry)
                return poetry_list
        for root, dirs, files in os.walk(Path(path)):
            poetry = self.get_poetry(root, files)
            if poetry is not None:
                poetry_list.append(poetry)
        return poetry_list

    def get_poetry(self, root, files):
        poetry = None
        if "pyproject.toml" in files and "poetry.lock" in files:
            poetry_root = Path(root)
            poetry = Factory().create_poetry(poetry_root)
            poetry.root_dir = poetry_root
            logger.info(f"Found python project at {root}")
        return poetry

    def log_non_deployable_packages(self, poetry_list):
        package_set = set()
        for poetry in poetry_list:
            for package in poetry.non_deployable_packages:
                if package.name not in package_set:
                    package_set.add(package.name)
                    logger.warn(
                        f"Could not find any wheel or tar.gz files for package {package.name}:{package.pretty_version}. Package may be statically linked or doesnt exist in artifacts cache"
                    )

    def create_poetry_packages(self, root_dir, cache_dir, deploy_downstream):
        """Gets all poetry packages required by each downstream project from the given cache directory."""
        poetry_list = self.get_all_poetry(root_dir, deploy_downstream)
        for poetry in poetry_list:
            packages = self.get_poetry_packages(poetry)
            dependency_files = self.get_cached_dependency_files(cache_dir)
            (
                deployable_packages,
                non_deployable_packages,
            ) = self.get_deploy_non_deploy_packages(
                packages=packages, dependency_files=dependency_files
            )
            project_package = self.get_project_dist_package(poetry)
            if len(project_package.files) > 0:
                deployable_packages.append(project_package)
            else:
                non_deployable_packages.append(project_package)
            poetry.deployable_packages = deployable_packages
            poetry.non_deployable_packages = non_deployable_packages
        return poetry_list

    def deploy_poetry(self, repo_name, downstream, io):
        config = Config.create()
        poetry_list = self.create_poetry_packages(
            os.getcwd(),
            config.artifacts_cache_directory.absolute().as_posix(),
            downstream,
        )
        repo_data = self.get_repository_data(config, repo_name, io)
        self.upload_poetry_packages(
            poetry_list=poetry_list,
            url=repo_data.url,
            username=repo_data.username,
            password=repo_data.password,
            io=io,
        )
        self.log_non_deployable_packages(poetry_list)
