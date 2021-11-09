# Amazon Redshift Devops

## Overview
CI/CD in the context of application development is a well understood topic, and there are numerous patterns and tools that developers can use to build their pipelines to handle the build, test, deploy cycle once a new commit gets into version control. For data, schema or stored procedure changes directly related to the application, typically this is part of a code base and is included in the code repository of the application. These changes are then applied when the application gets deployed to the test/prod environment. 

This blog post will demonstrate how the same set of approaches can be applied to stored procedures, DML (data manipulation language) and schema changes to data warehouses like Amazon Redshift. In addition, database migrations and tests require connection information to the relevant Amazon Redshift cluster, we will be demonstrating how this can be integrated securely using AWS Secrets Manager.

Stored procedures are considered code and as such should undergo the same rigour as application code. This means that the pipeline should involve running test against changes to make sure that no regressions are introduced to the production environment. Lastly, since we’re automating the deployment of both stored procedures and schema changes, this significantly reduces inconsistencies in between environments.

## Proposed Architecture
Open-source deployment and deployment using CI/CD tool Jenkins and Docker. Docker container will be used to build redshift pipeline to deploy DDL/DML changes.  When a code change is pushed by developer into Git, webhooks trigger a build process in Jenkins. The build job is a pipeline (descriptive/scripted) , builds the docker image (based on docker config provided) and pushes the image into docker hub. Jenkins pipeline pulls the dockerhub image and deploys that as a container executing the pipeline to run DDL/DML statements.


![Architecture](doc-images/architecture.png)

## Running the Redshift pipeline
CI/CD tool executes a program in the GitHub repo for code deployment. Jenkins calls the python program python_client_redshift_ephemeral.py, it reads two config (.ini) files. First file,dw_config.ini contains cluster configuration. Second file, query_redshift_api.ini contains the SQL (DDL/DML/stored procedure) to be executed. 

You can see how all of these works together by doing the following steps:

### Clone the GitHub Repository
The AWS CloudFormation template and the source code for the example application can be found here: https://github.com/aws-samples/devops-redshift.git . Before you get started, you need to clone the repository using the following command:

`git clone https://github.com/aws-samples/devops-redshift.git`

This will create a new folder, redshift_devops, with the files inside. 

### Deploy CloudFormation Template
Go to the CloudFormation console and click "Create Stack" then choose "With new resources (standard)". 

Once you're in the "Create stack" page, choose "Upload a template file" and then "Choose file". The file should be in `<cloned_directory>/cloudformation_Redshift_devops.yml`. After you select the file, your screen should look like the following:

![Deploy Step 1](doc-images/stack_step1.png)

Click "Next" and complete the following parameters:
-	Stack name – we will use `RedshiftDevOps`
-	DataBucketName – S3 bucket name
-	Key – Your pem key to connect to ec2 instance.
-	Master user name
-	Master password for both test and prod Amazon Redshift clusters. The password has the following criteria:
    * Must be 8-64 characters.
    * Must contain at least one uppercase letter.
    * Must contain at least one lowercase letter.
    * Must contain at least one number.
    * Can only contain ASCII characters (ASCII codes 33-126), except ' (single quotation mark), " (double quotation mark), /, \, or @.
-	Redshift node count (default:dsc2 – 1 node) 
-	Your public IP

![Deploy Step 2](doc-images/stack_step2.png)

Click "Next"

![Deploy Step 3](doc-images/stack_step3.png)

We can leave everything as is in this page and click "Next".

![Deploy Step 4](doc-images/stack_step4.png)

Lastly, scroll to the bottom of the page and check the acknowledgement and click "Create stack". The stack will create the VPC, Amazon Redshift clusters, ec2 instance, deploy a container on ec2 running Jenkins.

Click the refresh button on the top right corner to track the progress of the stack creation.

![Deploy Step 5](doc-images/stack_step5.png)

1. Connect to ec2 instance and verify docker container is running. 

    Use SSH to log on to ec2 instance using the .pem file selected in cloud formation.

    Once logged on to ec2 instance run the command:
    
    `docker ps -a`

    ![Deploy Step 6](doc-images/stack_step6.png)

    myjenkins docker container is deployed mapping ec2 host folders with myjenkins container. This will preserve the state of Jenkins application (metadata, jobs etc.) even though container exits. If the container were to be re-started, configurations will not be lost.
      
    If the container exits for any reason, execute the following command on the terminal:

    `docker run -d -p 8080:8080 --name myjenkins -v /var/run/docker.sock:/var/run/docker.sock -v jenkins_home:/var/jenkins_home -v jenkins_downloads:/var/jenkins_home/downloads jenkins/jenkins:lts`

2. Once done, log on to Jenkins ec2url+jenkinsport
    
    Copy the URL and paste in a web browser (chrome, firefox recommended). Please note the URL will be unique to you and will be public ec2 instance name deployed by CFN. Port 8080 is used for web traffic.

    http://`ec2-34-239-162-89.compute-1.amazonaws.com`:8080/

    Log on to ec2 console and check the ec2 instance name entitled Jenkins Server

    ![Deploy Step 7](doc-images/stack_step7.png)

3. A screen asking for administrator password will be displayed.

    ![Deploy Step 8](doc-images/stack_step8.png)

    Log on to the Jenkins container using the command 

    `docker exec -it myjenkins /bin/bash`

    Once inside the container shell, execute the command:

    `cat /var/lib/jenkins/secrets/initialAdminPassword`

4. The simplest and most common way of installing plugins is through the **Manage Jenkins > Manage Plugins**. Click **Available** to view all the Jenkins plugin that can be installed. Using the search box, search for **Docker Plugin**. Select **Docker,Docker API Plugin,Docker Pipeline,docker-build-step**

    ![Deploy Step 9](doc-images/stack_step9.png)

5. Adding security credentials within Jenkins.
    
    Next, we will add credentials for accessing docker, github and AWS account. Click 
    Dashboard> Manage Jenkins> Manage Credentials > Jenkins (stores scoped t Jenkins)

    ![Deploy Step 10](doc-images/stack_step10.png)

    Click Add credential, create an id (you can create a custom id or you could use the default guid provided by Jenkins).

    ![Deploy Step 11](doc-images/stack_step11.png)

    On the “Kind” drop down box, select GithubApp define username and password click ok. Repeat the same process, for Docker. Select kind as secret text and then add, AWS secret.

6. Jenkins 2.0 allows creation of pipeline as code, as essential part of continuous delivery (CD). Declarative pipeline is groovy based, having a programming language to build pipelines avoids runtime issues with the build script. 

    On the left pane select New Item>Pipeline> "Redshift_declarative_pipeline" as the name of declarative pipeline.

    ![Deploy Step 12](doc-images/stack_step12.png)

    Provide a description for the pipeline. Select a build trigger, we will like to create a based on changes made to the git repo. Click the check box "GitHub hook trigger for GITScm polling".

    ![Deploy Step 13](doc-images/stack_step13.png)

    In the Advanced Project Options. For pipeline definition drop down select "Pipeline script from SCM". Select Git as SCM and provide the repository URL for github repo. For credentials select Github credentials added. Script path will look for the file to be used for declarative pipeline, type in name as Jenkinsfile. Click Save.

    ![Deploy Step 14](doc-images/stack_step14.png)

7. We will implement another version of pipeline by using Jenkins scripted pipeline option. You can decide to run either Declarative or scripted pipeline. Declarative pipelines are preferred as they allow pipeline to be managed as code.

    To begin, navigate to Jenkins homepage and on the left pane, select New Item>Pipeline> "redshift_devops_scripted_pipeline" as the name of scripted pipeline.

    In the advance project option, select “pipeline script” as definition. Copy contents from Jenkins_scripted_pipeline.txt into the script section. In the script, replace variable name – DOCKERRPONAME with the docker repo created and YOURDOCKERLOGON with your docker in login name. 

    Also, note that AWS_DEFAULT_REGION is set as 'us-west-2'. You can modify the region based on your preference.

    After changes have been made, click save and apply.

    ![Deploy Step 15](doc-images/stack_step15.png)

8. Navigate to your git account containing cloned devops-redshift repository and click settings. Click webhooks on the left had side pane, it should open the manage webhook window. In the payload URL, put in the Jenkins URL with /github-wehook/ URI path. 

    http://`ec2-34-239-162-89.compute-1.amazonaws.com`:8080/github-webhook/

    ![Deploy Step 16](doc-images/stack_step16.png)

    This webhook notifies Jenkins to trigger a build when there are any changes to the GitHub repository.

9. Copy and paste the below lines in the query_redshift_api.ini file 

    [DDL_v08]

    query6 = create table test_table_service (col1 varchar(10), col2 varchar(20));

    And commit the changes. 
10. Git will send an event to the Jenkins server to start the build. If all works, you should see the Jenkins job automatically triggered at this point. 

11. Once the Jenkins job has been completed you should have the container running. To check the container, navigate to terminal and run docker ps -a you should see a container rs_containerv1 running.

    ![Deploy Step 17](doc-images/stack_step17.png)

12. To verify the steps executed by the docker container , check the logs. Run

    `docker logs rs_containerv1 -f`

    to see the log lines getting generated.

13.	The process will execute test cases and print results of assertions for values specified in the results section. 

14.	Finally, log on to console -> Redshift -> clusters and you will a new cluster based on the cluster name provided in the clusterconfig.ini file. 

15.	Once all the execution steps are completed, container will show a status of EXITED(0).

    ![Deploy Step 18](doc-images/stack_step18.png)

## Security

See [CONTRIBUTING](CONTRIBUTING.md#security-issue-notifications) for more information.

## License

This library is licensed under the MIT-0 License. See the [LICENSE](LICENSE) file.
