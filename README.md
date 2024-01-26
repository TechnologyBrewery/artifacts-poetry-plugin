# Artifacts Poetry Plugin

## Description
The Artifacts Poetry Plugin is used to print out all direct and transitive package dependencies of a python project.

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

## Test
To run the plugins tests, go to to the tests directory and execute the command `behave`. All tests should pass successfully. 

## Commands
Below describe the different commands the plugin offers

### Artifacts List
* Used to list all the direct and transitive package dependencies of a python project. 
* To run, execute the command `poetry artifacts-list` in a python project. 