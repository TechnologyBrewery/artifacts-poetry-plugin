from typing import List
from behave import given
from behave import when
from behave import then
from artifacts_poetry_plugin.plugin import ArtifactsDeploy
from poetry.core.packages.package import Package
from poetry.core.constraints.version import Version
import os

TEST_RESOURCES_DIR = os.path.join(os.getcwd(), "tests", "resources")
ARTIFACT_CACHE = os.path.join(TEST_RESOURCES_DIR, "artifacts")


@given("the following artifacts")
def the_following_artifacts(context):
    context.packages = {}
    create_dir(ARTIFACT_CACHE)
    for row in context.table:
        name = row["package"]
        version = row["version"]
        filename = f"{name}-{version}.whl"
        file = open(os.path.join(ARTIFACT_CACHE, filename), "w")
        file.close()
        files = [filename]
        version_obj = Version()
        package = Package(name=name, version=version_obj, pretty_version=version)
        package.files = files
        context.packages[row["key"]] = package


@given("a python project {project_name} with dependencies on package {keys}")
def step_impl(context, project_name, keys):
    create_project(context, TEST_RESOURCES_DIR, keys, project_name)


@given("no wheel file associated with package {keys}")
def step_impl(context, keys):
    for key in keys.split(","):
        package = context.packages[key]
        for file in package.files:
            filepath = os.path.join(ARTIFACT_CACHE, file)
            if os.path.isfile(filepath):
                os.remove(filepath)


@when("the dependency deployment is triggered on {project_name}.")
def step_impl(context, project_name):
    project_path = os.path.join(TEST_RESOURCES_DIR, project_name)
    artifacts_deploy = ArtifactsDeploy()
    poetry_files = artifacts_deploy.create_poetry_packages(project_path, ARTIFACT_CACHE)
    deploy_packages = []
    non_deploy_packages = []
    for poetry in poetry_files:
        deploy_packages.extend(poetry.deployable_packages)
        non_deploy_packages.extend(poetry.non_deployable_packages)
    context.deploy_packages = deploy_packages
    context.non_deploy_packages = non_deploy_packages


@given("a python subproject {project_name} with dependencies on package {keys}")
def step_impl(context, project_name, keys):
    create_project(context, context.current_dir, keys, project_name)


@then("package {keys} are able to be deployed to an alternate repository.")
def step_impl(context, keys):
    deploy_package_set = get_package_set(context.deploy_packages)
    compare_package_set = get_package_set_from_keys(keys, context.packages)
    assert compare_package_set.issubset(deploy_package_set)


@then("package {keys} are not able to be deployed to an alternate repository.")
def step_impl(context, keys):
    non_deploy_package_set = get_package_set(context.non_deploy_packages)
    compare_non_deploy_package_set = get_package_set_from_keys(keys, context.packages)
    assert compare_non_deploy_package_set.issubset(non_deploy_package_set)


def get_package_set(packages: List[Package]):
    """Converts a list of packages to a set"""
    package_set = set()
    for package in packages:
        package_set.add((package.name, package.pretty_version))
    return package_set


def get_package_set_from_keys(keys, packages):
    """Gets the packages identified by the keys and put them into a set"""
    package_set = set()
    for key in keys.split(","):
        if key in packages:
            package = packages[key]
            package_set.add((package.name, package.pretty_version))
    return package_set


def create_dir(path):
    if os.path.isdir(path) is False:
        os.mkdir(path)


def create_project(context, path, keys, project_name):
    """Creates a poetry project at the given path with the packages identified by the keys"""
    project_path = os.path.join(path, project_name)
    create_dir(project_path)
    dist_path = os.path.join(project_path, "dist")
    create_dir(dist_path)
    wheel_path = os.path.join(dist_path, "project.whl")
    wheel_file = open(wheel_path, "w")
    wheel_file.close()
    write_pyproject_file(project_path, project_name)
    write_lock_file(context, project_path, keys)
    context.current_dir = project_path


def write_pyproject_file(path, project_name):
    """Writes a pyproject file"""
    with open(os.path.join(path, "pyproject.toml"), "w") as pyproject:
        pyproject.write("\n[tool.poetry]\n")
        pyproject.write(f'name = "{project_name}"\n')
        pyproject.write('version = "1.0.0"\n')
        pyproject.write('description = ""\n')
        pyproject.write("authors = []")


def write_lock_file(context, path, keys):
    """Writes a poetry lock file with packages identified by the keys"""
    with open(os.path.join(path, "poetry.lock"), "w") as poetry_lock:
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
