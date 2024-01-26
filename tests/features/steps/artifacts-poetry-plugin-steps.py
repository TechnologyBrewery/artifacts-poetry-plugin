from behave import given
from behave import when
from behave import then
from artifacts_poetry_plugin.plugin import getPackages
from poetry.factory import Factory
import os
import shutil
from pathlib import Path
import subprocess

TEST_RESOURCES_DIR = os.path.join(os.getcwd(), "tests", "resources")
TEMPLATE_PY_PROJECT = os.path.join(TEST_RESOURCES_DIR, "template.toml")
PY_PROJECT = os.path.join(TEST_RESOURCES_DIR, "pyproject.toml")
POETRY_LOCK = os.path.join(TEST_RESOURCES_DIR, "poetry.lock")


class Package:
    def __init__(self, name, pretty_version) -> None:
        self.name = name
        self.pretty_version = pretty_version

    def name(self):
        return self.name

    def pretty_version(self):
        return self.pretty_version


@given("the following artifacts")
def the_following_artifacts(context):
    context.packages = {}
    for row in context.table:
        context.packages[row["key"]] = Package(
            name=row["package"], pretty_version=row["version"]
        )


@given("a Python project with dependencies on artifacts {keys}")
def step_impl(context, keys):
    shutil.copy(TEMPLATE_PY_PROJECT, PY_PROJECT)
    with open(PY_PROJECT, "a") as py_project:
        py_project.write("\n[tool.poetry.dependencies]\n")
        for key in keys.split(","):
            package = context.packages[key]
            py_project.write(f'{package.name} = "{package.pretty_version}"\n')
        py_project.write(f'python = "^3.8"')
    subprocess.run(["poetry", "install", "--no-root"], cwd=TEST_RESOURCES_DIR)


@when("the Python dependency search is triggered")
def step_impl(context):
    poetry = Factory().create_poetry(Path(POETRY_LOCK))
    context.response_packages = getPackages(poetry)


@then("artifacts {keys} are located in the local cache")
def step_impl(context, keys):
    response_package_set = set()
    for package in context.response_packages:
        response_package_set.add((package.name, package.pretty_version))
    compare_package_set = set()
    for key in keys.split(","):
        if key in context.packages:
            package = context.packages[key]
            compare_package_set.add((package.name, package.pretty_version))
    assert compare_package_set.issubset(response_package_set)
