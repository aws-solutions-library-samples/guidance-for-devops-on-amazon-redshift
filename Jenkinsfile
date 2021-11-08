/* Declarative Jenkins Pipeline
1. Builds docker dockerImage
2. Pushes image to dockerhub
3. Deploys the container image as a stand alone container
4. Executes Redshift pipeline code for execution
5. Adding changes for dry run
*/

pipeline {
    environment {
    registry = "jeetesh9108/rs-pipeline"
    registryCredential = 'dockerhub_id'
    dockerImage = ''
    AWS_ACCESS_KEY_ID='AKIAWPVSKFO3WFO5FLUL'
    AWS_SECRET_ACCESS_KEY= credentials('SECRET_ACCESS_KEY')
    AWS_DEFAULT_REGION='us-east-1'
    configFile ='query_redshift_api.ini'
    output = 'c'
    name = 'rs_containerv1'
    /*Parameters to be modified */
    clusterconfigfile='dw_config.ini'
    clusterconfigparm='DEV'
    /*Name of the section and query id to be executed default:ALL */
    sectionName ='ALL'
    query_id ='ALL'


    }
	agent any
	stages {
			stage('Build Docker Image')	{
			steps{
			script{
			sh 'docker build -t jeetesh9108/rs-pipeline:2.0.0 .'
			dockerImage = docker.build registry + ":$BUILD_NUMBER"
				  }
			   }
			}
			    stage('Push Docker Image') {
			    steps
			    {
			    script {
                docker.withRegistry( '', registryCredential )
                {
                        dockerImage.push()
                }
	        			}
	        	}
	        }
	        stage ('Run container on Server') {
	        steps
	        { script {
		        execute_command = "python3 python_client_redshift_ephemeral.py rollforward $configFile $sectionName $query_id $output $clusterconfigfile $clusterconfigparm"
		        dockerRun = "docker run -d -it  -v /home/ec2-user/container_data:/src/output_data --name rs_containerv1 -e AWS_ACCESS_KEY_ID=$AWS_ACCESS_KEY_ID -e AWS_SECRET_ACCESS_KEY=$AWS_SECRET_ACCESS_KEY -e AWS_DEFAULT_REGION=$AWS_DEFAULT_REGION jeetesh9108/rs-pipeline:2.0.0 $execute_command"
		        sh '''OLD="$(docker ps --all --quiet --filter name=rs_containerv1)"
                                if [ -n "$OLD" ]; then
                                   docker stop $OLD &&  echo "container stopped";
                                   docker rm $OLD && echo "container removed";
                                else
                                    echo "No container running";
                                fi'''
                sh "echo 'Starting container'"
                sh "$dockerRun"
			}
		}

    }
  }
}