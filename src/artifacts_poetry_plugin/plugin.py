import poetry.plugins.application_plugin
import poetry.console.application
from cleo.commands.command import Command
from cleo.helpers import argument
from artifacts_poetry_plugin.ArtifactsDeployHelper import ArtifactsDeployHelper

ARTIFACTS_DEPLOY = "artifacts-deploy"
ARTIFACTS_DEPLOY_ALL = "artifacts-deploy-all"
REPOSITORY_NAME = "repository_name"


class ArtifactsDeployCommand(Command):
    name = ARTIFACTS_DEPLOY

    arguments = [
        argument(
            REPOSITORY_NAME,
            "The name of the repository to which artifacts should be deployed",
        )
    ]

    help = "The Artifacts Deploy command is used to deploy a Python project's dependencies to a repository"

    def handle(self) -> int:
        self.line("Artifacts Deploy")
        repo_name = self.argument(REPOSITORY_NAME)
        artifacts_deploy_helper = ArtifactsDeployHelper()
        artifacts_deploy_helper.deploy_poetry(repo_name, False, self.io)
        return 0


class ArtifactsDeployAllCommand(Command):
    name = ARTIFACTS_DEPLOY_ALL

    arguments = [
        argument(
            REPOSITORY_NAME,
            "The name of the repository to which artifacts should be deployed",
        )
    ]

    help = "The Artifacts Deploy command is used to deploy all downstream Python project's dependencies to a repository"

    def handle(self) -> int:
        self.line("Artifacts Deploy All")
        repo_name = self.argument(REPOSITORY_NAME)
        artifacts_deploy_helper = ArtifactsDeployHelper()
        artifacts_deploy_helper.deploy_poetry(repo_name, True, self.io)
        return 0


def artifacts_deploy_all_factory():
    return ArtifactsDeployAllCommand()


def artifacts_deploy_factory():
    return ArtifactsDeployCommand()


class ArtifactsPoetryPlugin(poetry.plugins.application_plugin.ApplicationPlugin):
    def activate(self, application: poetry.console.application.Application):
        application.command_loader.register_factory(
            ARTIFACTS_DEPLOY_ALL, artifacts_deploy_all_factory
        )
        application.command_loader.register_factory(
            ARTIFACTS_DEPLOY, artifacts_deploy_factory
        )
