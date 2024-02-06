import os
from pathlib import Path
import poetry.plugins.application_plugin
import poetry.console.application
from poetry.factory import Factory
from cleo.commands.command import Command
import poetry.config.config
from poetry.publishing.uploader import Uploader
from poetry.utils.authenticator import Authenticator
from poetry.core.packages.package import Package
from cleo.helpers import argument
from poetry.config.config import Config
from typing import List
import logging

ARTIFACTS_DEPLOY = "artifacts-deploy"
REPOSITORY_NAME = "repository_name"
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


class ArtifactsDeploy(Command):
    name = ARTIFACTS_DEPLOY

    arguments = [
        argument(
            REPOSITORY_NAME,
            "The name of the repository to which artifacts should be deployed",
        )
    ]

    help = "The Artifacts Deploy command is used to deploy all of a Python project's dependencies to a repository"

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

    def get_cached_wheel_files(self, cache_dir):
        """Gets all wheel file locations for the given cache directory"""
        wheel_files = {}
        for root, dirs, files in os.walk(cache_dir):
            for file in files:
                if file.endswith(".whl") or file.endswith(".tar.gz"):
                    wheel_files[file] = Path(os.path.join(root, file))
        return wheel_files

    def get_deploy_non_deploy_packages(self, packages: List[Package], wheel_files):
        """Adds the wheel file locations for each package's files"""
        non_deployable_packages = []
        deployable_packages = []
        for package in packages:
            file_found = False
            for file in package.files:
                if file["file"] in wheel_files:
                    file_found = True
                    file["url"] = wheel_files[file["file"]]
            if file_found:
                deployable_packages.append(package)
            else:
                non_deployable_packages.append(package)
        return deployable_packages, non_deployable_packages

    def upload_packages(self, poetry_files, url, username, password, io):
        deploy_set = set()
        for poetry in poetry_files:
            uploader = Uploader(poetry, io)
            uploader.auth(username=username, password=password)
            session = uploader.make_session()
            for package in poetry.deployable_packages:
                uploader._package = package
                for file in package.files:
                    if "url" in file and file["url"] not in deploy_set:
                        deploy_set.add(file["url"])
                        uploader._upload_file(
                            session, url, file=file["url"], skip_existing=True
                        )

    def get_project_package(self, poetry):
        """Adds the generated package to the list of packages with its associated wheel file"""
        project_package_path = os.path.join(poetry.root_dir, "dist")
        project_package = poetry.package
        for root, dirs, files in os.walk(project_package_path):
            for file in files:
                if file.endswith(".whl") or file.endswith(".tar.gz"):
                    file_data = {"file": file, "url": Path(os.path.join(root, file))}
                    project_package.files.append(file_data)
        return project_package

    def get_all_poetry(self, path):
        poetry_files = []
        for root, dirs, files in os.walk(Path(path)):
            if "pyproject.toml" in files and "poetry.lock" in files:
                poetry_root = Path(root)
                poetry = Factory().create_poetry(poetry_root)
                poetry.root_dir = poetry_root
                poetry_files.append(poetry)
                logger.info(f"Found python project at {root}")
        return poetry_files

    def log_non_deployable_packages(self, poetry_files):
        package_set = set()
        for poetry in poetry_files:
            for package in poetry.non_deployable_packages:
                if package.name not in package_set:
                    package_set.add(package.name)
                    logger.warn(
                        f"Could not find any wheel or tar.gz files for package {package.name}:{package.pretty_version}. Package may be statically linked or doesnt exist in artifacts cache"
                    )

    def create_poetry_packages(self, root_dir, cache_dir):
        """Gets all poetry packages required by each downstream project from the given cache directory."""
        poetry_files = self.get_all_poetry(root_dir)
        for poetry in poetry_files:
            packages = self.get_poetry_packages(poetry)
            wheel_files = self.get_cached_wheel_files(cache_dir)
            (
                deployable_packages,
                non_deployable_packages,
            ) = self.get_deploy_non_deploy_packages(
                packages=packages, wheel_files=wheel_files
            )
            project_package = self.get_project_package(poetry)
            if len(project_package.files) > 0:
                deployable_packages.append(project_package)
            else:
                non_deployable_packages.append(project_package)
            poetry.deployable_packages = deployable_packages
            poetry.non_deployable_packages = non_deployable_packages
        return poetry_files

    def handle(self) -> int:
        self.line("Artifacts Deploy")
        repo_name = self.argument(REPOSITORY_NAME)
        config = Config.create()
        poetry_files = self.create_poetry_packages(
            os.getcwd(),
            config.artifacts_cache_directory.absolute().as_posix(),
        )
        repo_data = self.get_repository_data(config, repo_name, self.io)
        self.upload_packages(
            poetry_files=poetry_files,
            url=repo_data.url,
            username=repo_data.username,
            password=repo_data.password,
            io=self.io,
        )
        self.log_non_deployable_packages(poetry_files)
        return 0


def factory():
    return ArtifactsDeploy()


class ArtifactsPoetryPlugin(poetry.plugins.application_plugin.ApplicationPlugin):
    def activate(self, application: poetry.console.application.Application):
        application.command_loader.register_factory(ARTIFACTS_DEPLOY, factory)
