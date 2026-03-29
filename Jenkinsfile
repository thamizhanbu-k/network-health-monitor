pipeline {
    agent any

    environment {
        IMAGE_NAME    = 'network-health-monitor'
        DOCKER_USER   = credentials('dockerhub-username')
        IMAGE_TAG     = "v${BUILD_NUMBER}" // e.g., v15
    }

    triggers {
        githubPush()
    }

    stages {
        stage('Checkout') {
            steps {
                // Automatically checks out the repo this Jenkinsfile lives in!
                checkout scm
            }
        }

        stage('Install and Test') {
            steps {
                // Uses a virtual environment to safely install Python packages and run pytest
                sh '''
                    python3 -m venv venv
                    . venv/bin/activate
                    pip install -r requirements.txt
                    pytest tests/ -v
                '''
            }
        }

        stage('Docker Build') {
            steps {
                // Builds the new image using the Jenkins build number as the version tag
                sh "docker build -t ${DOCKER_USER}/${IMAGE_NAME}:${IMAGE_TAG} ."
            }
        }

        stage('Docker Push') {
            steps {
                // Safely injects DockerHub credentials to push the image to the cloud
                withCredentials([usernamePassword(
                    credentialsId: 'dockerhub-creds',
                    usernameVariable: 'DOCKER_USERNAME',
                    passwordVariable: 'DOCKER_PASSWORD'
                )]) {
                    sh 'docker login -u $DOCKER_USERNAME -p $DOCKER_PASSWORD'
                    sh "docker push ${DOCKER_USERNAME}/${IMAGE_NAME}:${IMAGE_TAG}"
                }
            }
        }

        stage('Deploy to Kubernetes') {
            steps {
                // Updates the K8s deployment to use the brand new image tag we just pushed!
                sh "kubectl set image deployment/health-monitor app=${DOCKER_USER}/${IMAGE_NAME}:${IMAGE_TAG}"
                sh 'kubectl rollout status deployment/health-monitor'
            }
        }
    }

    post {
        success {
            echo "✅ Successfully deployed ${IMAGE_NAME}:${IMAGE_TAG}"
        }
        failure {
            echo '❌ Pipeline failed — check the console logs'
        }
    }
}