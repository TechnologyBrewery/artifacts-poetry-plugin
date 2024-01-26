Feature: Artifacts-Poetry-Plugin
    Plugin used to deploy wheel files to an alternate repository

    Background:
        Given the following artifacts:
            |   key     | package       | version    | 
            |   A       | poetry        | 1.6.0      |
            |   B       | cleo          | 2.0.1      | 


    Scenario: Locate all dependent wheel files from a python project
        Given a Python project with dependencies on artifacts A,B
        When the Python dependency search is triggered
        Then artifacts A,B are located in the local cache 