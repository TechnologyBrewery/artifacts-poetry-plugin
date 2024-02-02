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
from typing import List
import logging

ARTIFACTS_DEPLOY = "artifacts-deploy"
REPOSITORY_NAME = "repository_name"
logger = logging.getLogger(__name__)


def get_repository_data(config, repo_name, io):
    """Gets the URL, username, and password from the poetry configuration for the given repo name"""
    repo_data = {}
    repo_data["url"] = config.get(f"repositories.{repo_name}.url")
    if repo_data["url"] is None:
        raise RuntimeError(f"Repository {repo_name} is not defined")
    authenticator = Authenticator(config, io)
    auth = authenticator.get_http_auth(repo_name)
    if auth:
        repo_data["username"] = auth.username
        repo_data["password"] = auth.password
    else:
        raise RuntimeError(
            f"username and password are required. Please verify that your poetry config for this repository is correct for repository {repo_name}"
        )
    return repo_data


def get_packages(poetry) -> List[Package]:
    locker = poetry.locker
    repository = locker.locked_repository()
    return repository.packages


def get_cached_wheel_files(cache_dir):
    """Gets all wheel file locations for the given cache directory"""
    wheel_files = {}
    for root, dirs, files in os.walk(cache_dir):
        for file in files:
            if file.endswith(".whl"):
                wheel_files[file] = Path(os.path.join(root, file))
    return wheel_files


def add_package_paths(packages: List[Package], wheel_files):
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


def upload_packages(poetry, packages: List[Package], url, username, password, io):
    uploader = Uploader(poetry=poetry, io=io)
    uploader.auth(username=username, password=password)
    session = uploader.make_session()
    for package in packages:
        uploader._package = package
        for file in package.files:
            if "url" in file:
                uploader._upload_file(
                    session,
                    url,
                    file=file["url"],
                )


def add_project_package(poetry, packages: List[Package]):
    """Adds the generated package to the list of packages with its associated wheel file"""
    project_package = poetry.package
    for root, dirs, files in os.walk("dist/"):
        for file in files:
            if file.endswith(".whl"):
                file_data = {"file": file, "url": Path(os.path.join(root, file))}
                project_package.files.append(file_data)
    packages.append(project_package)


def get_all_poetry(path):
    poetry_files = []
    for root, dirs, files in os.walk(Path(path)):
        for file in files:
            if file == "pyproject.toml":
                poetry_files.append(Factory().create_poetry(Path(root)))
    return poetry_files


def get_deploy_packages(root_dir, cache_dir):
    """Gets all deployable packages from the given cache directory. A package is deployable if it has any wheel files associated with it"""
    total_deployable_packages = []
    total_non_deployable_packages = []
    poetry_files = get_all_poetry(root_dir)
    print(poetry_files)
    for poetry in poetry_files:
        packages = get_packages(poetry)
        wheel_files = get_cached_wheel_files(cache_dir)
        deployable_packages, non_deployable_packages = add_package_paths(
            packages=packages, wheel_files=wheel_files
        )
        total_deployable_packages.extend(deployable_packages)
        total_non_deployable_packages.extend(non_deployable_packages)
    add_project_package(poetry, total_deployable_packages)
    return total_deployable_packages, total_non_deployable_packages


class ArtifactsDeploy(Command):
    name = ARTIFACTS_DEPLOY

    arguments = [
        argument(REPOSITORY_NAME, "The name of the repository to deploy artifacts")
    ]

    help = "The Artifacts Deploy command is used to deploy all of a Python project's dependencies to a repository"

    def handle(self) -> int:
        self.line("Artifacts Deploy")
        repo_name = self.argument(REPOSITORY_NAME)
        poetry = Factory().create_poetry(Path(os.getcwd()))
        config = poetry.config
        repo_data = get_repository_data(config, repo_name, self.io)
        url = repo_data["url"]
        username = repo_data["username"]
        password = repo_data["password"]
        packages, non_deployable_packages = get_deploy_packages(
            os.getcwd(),
            poetry.config.artifacts_cache_directory.absolute().as_posix(),
        )
        upload_packages(
            poetry,
            packages=packages,
            url=url,
            username=username,
            password=password,
            io=self.io,
        )
        for package in non_deployable_packages:
            logger.warn(
                f"Could not find any wheel files for package {package.name}. Package may be statically linked or doesnt exist in artifacts cache"
            )
        return 0


def factory():
    return ArtifactsDeploy()


class ArtifactsPoetryPlugin(poetry.plugins.application_plugin.ApplicationPlugin):
    def activate(self, application: poetry.console.application.Application):
        application.command_loader.register_factory(ARTIFACTS_DEPLOY, factory)
