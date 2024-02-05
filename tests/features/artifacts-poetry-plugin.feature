Feature: Artifacts-Poetry-Plugin
    Plugin used to deploy wheel files to an alternate repository

    Background:
        Given the following artifacts:
            |   key     | package       | version    | 
            |   A       | poetry        | 1.6.0      |
            |   B       | cleo          | 2.0.1      | 
            |   C       | crytography   | 1.0.0      | 


    Scenario: Get all deployable Python dependencies from a project
        Given a python project test-1 with dependencies on package A,B
        When the dependency deployment is triggered. 
        Then package A,B are able to be deployed to an alternate repository.  
        
    
    Scenario: Get a non deployable Python dependency from a project
        Given a python project test-2 with dependencies on package A
        But no wheel file associated with package A
        When the dependency deployment is triggered. 
        Then package A are not able to be deployed to an alternate repository.

    