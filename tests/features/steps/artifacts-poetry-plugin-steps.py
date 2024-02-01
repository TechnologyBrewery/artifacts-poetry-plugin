from behave import given
from behave import when
from behave import then
from artifacts_poetry_plugin.plugin import get_deploy_packages
from poetry.factory import Factory
import os
from pathlib import Path

TEST_RESOURCES_DIR = os.path.join(os.getcwd(), "tests", "resources")
TEMPLATE_PY_PROJECT = os.path.join(TEST_RESOURCES_DIR, "template.toml")
PY_PROJECT = os.path.join(TEST_RESOURCES_DIR, "pyproject.toml")
POETRY_LOCK = os.path.join(TEST_RESOURCES_DIR, "poetry.lock")


class Package:
    def __init__(self, name, pretty_version, files) -> None:
        self.name = name
        self.pretty_version = pretty_version
        self.files = files

    def name(self):
        return self.name

    def pretty_version(self):
        return self.pretty_version

    def files(self):
        return self.files


@given("the following artifacts")
def the_following_artifacts(context):
    context.packages = {}
    for row in context.table:
        name = row["package"]
        version = row["version"]
        filename = f"{name}-{version}.whl"
        file = open(os.path.join(TEST_RESOURCES_DIR, filename), "w")
        file.close()
        files = []
        files.append(filename)
        context.packages[row["key"]] = Package(
            name=name, pretty_version=version, files=files
        )


@given("a Python project with dependencies on package {keys}")
def step_impl(context, keys):
    with open(POETRY_LOCK, "w") as poetry_lock:
        poetry_lock.write("\n[metadata]\n")
        poetry_lock.write('lock-version = "2.0"\n')
        poetry_lock.write('python-versions = "^3.8"\n\n')
        for key in keys.split(","):
            package = context.packages[key]
            files = package.files
            poetry_lock.write("[[package]]\n")
            poetry_lock.write(f'name = "{package.name}"\n')
            poetry_lock.write(f'version = "{package.pretty_version}"\n')
            poetry_lock.write(f'description = "Test"\n')
            poetry_lock.write(f"optional = false\n")
            poetry_lock.write(f'python-versions = ">=2.6, !=3.0.*, !=3.1.*, !=3.2.*"\n')
            poetry_lock.write(f"files = [\n")
            for file in files:
                poetry_lock.write(
                    "{"
                    + f'file = "{file}", hash = "sha256:ebda1a6c9e5bfe95c5f9f0a2794e01c7098b3dde86c10a95d8621c5907ff6f1c"'
                    + "},\n"
                )
            poetry_lock.write("]\n\n")


@when("the Python deployable dependency is triggered.")
def step_impl(context):
    poetry = Factory().create_poetry(Path(POETRY_LOCK))
    deploy_packages, non_deploy_packages = get_deploy_packages(
        poetry, TEST_RESOURCES_DIR
    )
    context.deploy_packages = deploy_packages
    context.non_deploy_packages = non_deploy_packages


def get_package_set(packages):
    package_set = set()
    for package in packages:
        package_set.add((package.name, package.pretty_version))
    return package_set


def get_package_set_from_keys(keys, packages):
    package_set = set()
    for key in keys.split(","):
        if key in packages:
            package = packages[key]
            package_set.add((package.name, package.pretty_version))
    return package_set


@then("package {keys} are able to be deployed to an alternate repository.")
def step_impl(context, keys):
    deploy_package_set = get_package_set(context.deploy_packages)
    compare_package_set = get_package_set_from_keys(keys, context.packages)
    assert compare_package_set.issubset(deploy_package_set)


@given("no wheel file associated with package {keys}")
def step_impl(context, keys):
    for key in keys.split(","):
        package = context.packages[key]
        for file in package.files:
            filepath = os.path.join(TEST_RESOURCES_DIR, file)
            if os.path.isfile(filepath):
                os.remove(filepath)


@then("package {keys} are not able to be deployed to an alternate repository.")
def step_impl(context, keys):
    non_deploy_package_set = get_package_set(context.non_deploy_packages)
    compare_non_deploy_package_set = get_package_set_from_keys(keys, context.packages)
    assert compare_non_deploy_package_set.issubset(non_deploy_package_set)
