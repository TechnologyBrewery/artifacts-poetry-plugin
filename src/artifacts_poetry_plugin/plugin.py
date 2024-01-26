import os
from pathlib import Path
import poetry.plugins.application_plugin
import poetry.console.application
from poetry.factory import Factory
from cleo.commands.command import Command

ARTIFACTS_LIST = "artifacts-list"


def getPackages(poetry):
    locker = poetry.locker
    repository = locker.locked_repository()
    return repository.packages


class ArtifactsDeploy(Command):
    name = ARTIFACTS_LIST

    def handle(self) -> int:
        self.line("Artifacts List")
        packages = getPackages(Factory().create_poetry(Path(os.getcwd())))
        print(packages)
        return 0


def factory():
    return ArtifactsDeploy()


class ArtifactsPoetryPlugin(poetry.plugins.application_plugin.ApplicationPlugin):
    def activate(self, application: poetry.console.application.Application):
        application.command_loader.register_factory(ARTIFACTS_LIST, factory)
