from steps.artifacts_poetry_plugin_steps import TEST_RESOURCES_DIR
import os
import shutil


def after_scenario(context, scenario):
    shutil.rmtree(TEST_RESOURCES_DIR, ignore_errors=False, onerror=None)


def before_scenario(context, scenario):
    if os.path.isdir(TEST_RESOURCES_DIR):
        shutil.rmtree(TEST_RESOURCES_DIR, ignore_errors=False, onerror=None)
    os.mkdir(TEST_RESOURCES_DIR)
