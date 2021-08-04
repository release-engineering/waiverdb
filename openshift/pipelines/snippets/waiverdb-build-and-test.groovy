stage('Install pip dependencies') {
  steps {
    script {
      if (sh(returnStatus: true, script: 'pip3 install --user -r ./requirements.txt') != 0) {
        echo 'WARNING: Failed to install dependencies from requirements.txt.'
      }
    }
  }
}
stage('Run checks') {
  failFast false
  parallel {
    stage('Invoke Flake8') {
      steps {
        sh 'flake8'
      }
    }
  }
}
stage('Run unit tests') {
  steps {
    sh 'cp conf/settings.py.example conf/settings.py'
    // wait for the test datebase to come up
    sh 'wait-for-it -s -t 300 127.0.0.1:5432'
    // create a database role
    sh "psql -h 127.0.0.1 -U postgres -q -d waiverdb -c 'CREATE ROLE \"jenkins\" WITH LOGIN SUPERUSER;'"
    // run unit tests
    sh 'py.test-3 -v --junitxml=junit-tests.xml tests'
  }
  post {
    always {
      junit 'junit-tests.xml'
    }
  }
}
stage('Build Artifacts') {
  failFast false
  parallel {
    stage('Branch Docs') {
      stages {
        stage('Build Docs') {
          steps {
            sh 'make -C docs html'
          }
          post {
            always {
              archiveArtifacts artifacts: 'docs/_build/html/**'
            }
          }
        }
      }
    }
    stage('Build SRPM') {
      steps {
        sh './rpmbuild.sh -bs'
      }
      post {
        success {
          archiveArtifacts artifacts: 'rpmbuild-output/*.src.rpm'
        }
      }
    }
    stage('Branch RPM') {
      stages {
        stage('Build RPM') {
          steps {
            sh './rpmbuild.sh -bb'
          }
          post {
            success {
              archiveArtifacts artifacts: 'rpmbuild-output/*/*.rpm'
            }
          }
        }
        stage('Invoke Rpmlint') {
          steps {
            sh 'rpmlint -f rpmlint-config.py rpmbuild-output/*/*.rpm'
          }
        }
      }
    }
  }
}
stage('Build container') {
  environment {
    BUILDCONFIG_INSTANCE_ID = "waiverdb-temp-${currentBuild.id}-${UUID.randomUUID().toString().substring(0,7)}"
  }
  steps {
    script {
      // Generate a version-release number for the target Git commit
      def versions = sh(returnStdout: true, script: 'source ./version.sh && echo -en "$WAIVERDB_VERSION\n$WAIVERDB_CONTAINER_VERSION"').split('\n')
      def waiverdb_version = versions[0]
      env.TEMP_TAG = versions[1] + '-jenkins-' + currentBuild.id

      openshift.withCluster() {
        openshift.withProject(env.PIPELINE_ID) {
          // OpenShift BuildConfig doesn't support specifying a tag name at build time.
          // We have to create a new BuildConfig for each container build.
          // Create a BuildConfig from a seperated Template.
          echo 'Creating a BuildConfig for container build...'
          def template = readYaml file: 'openshift/waiverdb-container-template.yaml'
          def processed = openshift.process(template,
            "-p", "NAME=${env.BUILDCONFIG_INSTANCE_ID}",
            '-p', "WAIVERDB_GIT_REPO=${params.GIT_REPO}",
            // A pull-request branch, like pull/123/head, cannot be built with commit ID
            // because refspec cannot be customized in an OpenShift build .
            '-p', "WAIVERDB_GIT_REF=${env.PR_NO ? env.GIT_REPO_REF : env.GIT_COMMIT}",
            '-p', "WAIVERDB_IMAGE_TAG=${env.TEMP_TAG}",
            '-p', "WAIVERDB_VERSION=${waiverdb_version}",
            '-p', "WAIVERDB_IMAGESTREAM_NAME=waiverdb",
            '-p', "WAIVERDB_IMAGESTREAM_NAMESPACE=${env.PIPELINE_ID}",
          )
          def build = c3i.buildAndWait(script: this, objs: processed)
          echo 'Container build succeeds.'
          def ocpBuild = build.object()
          env.RESULTING_IMAGE_REF = ocpBuild.status.outputDockerImageReference
          env.RESULTING_IMAGE_DIGEST = ocpBuild.status.output.to.imageDigest
          def imagestream = openshift.selector('is', ['app': env.BUILDCONFIG_INSTANCE_ID]).object()
          env.RESULTING_IMAGE_REPOS = imagestream.status.dockerImageRepository
          env.RESULTING_TAG = env.TEMP_TAG
        }
      }
    }
  }
  post {
    failure {
      echo "Failed to build container image ${env.TEMP_TAG}."
    }
  }
}
stage("Functional tests phase") {
  stages {
    stage('Prepare') {
      steps {
        script {
          env.IMAGE = "${env.RESULTING_IMAGE_REPOS}:${env.RESULTING_TAG}"
        }
      }
    }
    stage('Run functional tests') {
      environment {
        // Jenkins BUILD_TAG could be too long (> 63 characters) for OpenShift to consume
        TEST_ID = "${params.TEST_ID ?: 'jenkins-' + currentBuild.id + '-' + UUID.randomUUID().toString().substring(0,7)}"
      }
      steps {
        echo "Container image ${env.IMAGE} will be tested."
        script {
          openshift.withCluster() {
            openshift.withProject(env.PIPELINE_ID) {
              // Don't set ENVIRONMENT_LABEL in the environment block! Otherwise you will get 2 different UUIDs.
              env.ENVIRONMENT_LABEL = "test-${env.TEST_ID}"
              def template = readYaml file: 'openshift/waiverdb-test-template.yaml'
              echo "Creating testing environment with TEST_ID=${env.TEST_ID}..."
              def models = openshift.process(template,
                '-p', "TEST_ID=${env.TEST_ID}",
                '-p', "WAIVERDB_APP_IMAGE=${env.IMAGE}",
              )
              c3i.deployAndWait(script: this, objs: models, timeout: 15)
              def appPod = openshift.selector('pods', ['environment': env.ENVIRONMENT_LABEL, 'service': 'web']).object()
              env.IMAGE_DIGEST = appPod.status.containerStatuses[0].imageID.split('@')[1]
              // Create route with short name
              openshift.create('route', 'edge', 'waiverdb', "--service=waiverdb-test-${env.TEST_ID}-web")
              // Give some time to active the route
              sh 'sleep 5'
              // Run functional tests
              def route_hostname = openshift.selector('routes', 'waiverdb').object().spec.host
              echo "Running tests against https://${route_hostname}/"
              withEnv(["WAIVERDB_TEST_URL=https://${route_hostname}/"]) {
                sh 'py.test-3 -v --junitxml=junit-functional-tests.xml functional-tests/'
              }
            }
          }
        }
      }
      post {
        always {
          script {
            junit 'junit-functional-tests.xml'
            archiveArtifacts artifacts: 'junit-functional-tests.xml'
            openshift.withCluster() {
              openshift.withProject(env.PIPELINE_ID) {
                /* Extract logs for debugging purposes */
                openshift.selector('deploy,pods', ['environment': env.ENVIRONMENT_LABEL]).logs()
              }
            }
          }
        }
      }
    }
  }
  post {
    always {
      script {
        if (!env.IMAGE_DIGEST) {
          // Don't send a message if the job fails before getting the image digest.
          return;
        }
        c3i.sendResultToMessageBus(
          imageRef: env.IMAGE,
          digest: env.IMAGE_DIGEST,
          environment: 'dev',
          scratch: params.GIT_REPO_REF != params.PAGURE_MAIN_BRANCH,
          docs: 'https://pagure.io/waiverdb/blob/master/f/openshift',
          xunit: "${env.BUILD_URL}/artifacts/junit-functional-tests.xml"
        )
      }
    }
  }
}
