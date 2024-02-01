# Artifacts Poetry Plugin

## Description
The Artifacts Poetry Plugin is used to deploy all direct and transitive package dependencies of a python project to an alternate repository. The plugin requires the use of a pyproject.toml and generated poetry.lock file. All dependencies must be installed in poetry's local artifacts cache. 

## Requirments
Poetry >= 1.6.0
Python >= 3.8

## Installation
Below describes the steps in order to install the poetry plugin.

* Make sure you are in the project's root directory. 
* Execute the command `mvn clean install` to build the plugin.
* Execute the command `pip install dist/name-of-wheel-file`. (Note: A new terminal instance will need to be created in order to run the plugin)

## Uninstall
Below describes the steps needed to uninstall the plugin.

* Execute the command `pip uninstall artifacts-poetry-plugin` to uninstall the plugin. 

## Commands
Below describe the different commands the plugin offers

### Artifacts Deploy
* Used to deploy all the direct and transitive package dependencies of a python project. 
* You must register a repository using the following command `poetry add <repository-name> <url>` where `repository-name` is the name of the repository and `url` is the url to the repository
* If the repository requires credentials, use the following to register to the previously added repository `poetry config http-basic.<repository-name> <username> <password>`.
* To run, execute the command `poetry artifacts-deploy <repository-name>` in a python project. 