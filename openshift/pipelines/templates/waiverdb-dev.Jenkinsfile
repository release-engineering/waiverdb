pipeline {
  agent {
    kubernetes {
      cloud params.JENKINS_AGENT_CLOUD_NAME
      label "jenkins-slave-${UUID.randomUUID().toString()}"
      serviceAccount params.JENKINS_AGENT_SERVICE_ACCOUNT
      defaultContainer 'jnlp'
      yaml """
      apiVersion: v1
      kind: Pod
      metadata:
        labels:
          app: "jenkins-${env.JOB_BASE_NAME}"
          factory2-pipeline-kind: "waiverdb-dev-pipeline"
          factory2-pipeline-build-number: "${env.BUILD_NUMBER}"
      spec:
        containers:
        - name: jnlp
          image: "${params.JENKINS_AGENT_IMAGE}"
          imagePullPolicy: Always
          tty: true
          env:
          - name: REGISTRY_CREDENTIALS
            valueFrom:
              secretKeyRef:
                name: "${params.CONTAINER_REGISTRY_CREDENTIALS}"
                key: '.dockerconfigjson'
          # Required by unit tests: Set up NSS Wrapper to generate a fake user name for the random UID assigned by OpenShift
          - name: LD_PRELOAD
            value: '/usr/lib64/libnss_wrapper.so'
          - name: NSS_WRAPPER_PASSWD
            value: '/tmp/passwd'
          - name: NSS_WRAPPER_GROUP
            value: '/etc/group'
          volumeMounts:
          - name: postgresql-socket
            mountPath: /var/run/postgresql
          resources:
            requests:
              memory: 768Mi
              cpu: 300m
            limits:
              memory: 1Gi
              cpu: 500m
        - name: db
          image: registry.access.redhat.com/rhscl/postgresql-95-rhel7:latest
          imagePullPolicy: Always
          env:
          - name: POSTGRESQL_USER
            value: waiverdb
          - name: POSTGRESQL_PASSWORD
            value: waiverdb
          - name: POSTGRESQL_DATABASE
            value: waiverdb
          volumeMounts:
          - name: postgresql-socket
            mountPath: /var/run/postgresql
          resources:
            requests:
              memory: 256Mi
              cpu: 100m
            limits:
              memory: 384Mi
              cpu: 200m
        volumes:
        - name: postgresql-socket
          emptyDir: {}
      """
    }
  }
  options {
    timestamps()
    timeout(time: 30, unit: 'MINUTES')
  }
  environment {
    PIPELINE_NAMESPACE = readFile('/run/secrets/kubernetes.io/serviceaccount/namespace').trim()
    PIPELINE_USERNAME = sh(returnStdout: true, script: 'id -un').trim()
  }
  stages {
    stage('Prepare') {
      steps {
        script {
          if (params.BUILD_DISPLAY_RENAME_TO) {
            currentBuild.displayName = params.BUILD_DISPLAY_RENAME_TO
          }
          def scmVars = checkout([$class: 'GitSCM',
            branches: [[name: params.WAIVERDB_GIT_REF]],
            userRemoteConfigs: [[url: params.WAIVERDB_GIT_REPO, refspec: '+refs/heads/*:refs/remotes/origin/* +refs/pull/*/head:refs/remotes/origin/pull/*/head']],
          ])
          // Generate a version-release number for the target Git commit
          def versions = sh(returnStdout: true, script: 'source ./version.sh && echo -en "$WAIVERDB_VERSION\n$WAIVERDB_CONTAINER_VERSION"').split('\n')
          env.WAIVERDB_VERSION = versions[0]
          env.WAIVERDB_CONTAINER_VERSION = versions[1]
          env.TEMP_TAG = env.WAIVERDB_CONTAINER_VERSION + '-jenkins-' + currentBuild.id
        }
        sh 'cp conf/settings.py.example conf/settings.py'
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
        stage('Invoke Pylint') {
          steps {
            sh 'pylint-3 --reports=n waiverdb'
          }
        }
      }
    }
    stage('Run unit tests') {
      steps {
        // wait for the test datebase to come up
        sh 'wait-for-it -s -t 300 127.0.0.1:5432'
        // create a database role
        sh 'psql -h 127.0.0.1 -U "postgres" -q -d "waiverdb" -c "CREATE ROLE \"$PIPELINE_USERNAME\" WITH LOGIN SUPERUSER;"'
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
            stage('Publish Docs') {
              when {
                expression {
                  return "${params.PAGURE_DOC_REPO_NAME}" && (params.WAIVERDB_GIT_REF == "${params.WAIVERDB_MAIN_BRANCH}" || env.FORCE_PUBLISH_DOCS == "true")
                }
              }
              steps {
                sshagent (credentials: ["${env.PIPELINE_NAMESPACE}-${params.PAGURE_DOC_SECRET}"]) {
                  sh '''
                  mkdir -p ~/.ssh/
                  touch ~/.ssh/known_hosts
                  ssh-keygen -R pagure.io
                  echo 'pagure.io ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQC198DWs0SQ3DX0ptu+8Wq6wnZMrXUCufN+wdSCtlyhHUeQ3q5B4Hgto1n2FMj752vToCfNTn9mWO7l2rNTrKeBsELpubl2jECHu4LqxkRVihu5UEzejfjiWNDN2jdXbYFY27GW9zymD7Gq3u+T/Mkp4lIcQKRoJaLobBmcVxrLPEEJMKI4AJY31jgxMTnxi7KcR+U5udQrZ3dzCn2BqUdiN5dMgckr4yNPjhl3emJeVJ/uhAJrEsgjzqxAb60smMO5/1By+yF85Wih4TnFtF4LwYYuxgqiNv72Xy4D/MGxCqkO/nH5eRNfcJ+AJFE7727F7Tnbo4xmAjilvRria/+l' >>~/.ssh/known_hosts
                  rm -rf docs-on-pagure
                  git clone ssh://git@pagure.io/docs/${PAGURE_DOC_REPO_NAME}.git docs-on-pagure
                  rm -rf docs-on-pagure/*
                  cp -r docs/_build/html/* docs-on-pagure/
                  cd docs-on-pagure
                  git config user.name 'Pipeline Bot'
                  git config user.email "pipeline-bot@localhost.localdomain"
                  git add -A .
                  if [[ "$(git diff --cached --numstat | wc -l)" -eq 0 ]] ; then
                      exit 0 # No changes, nothing to commit
                  fi
                  git commit -m "Automatic commit of docs built by Jenkins job ${JOB_NAME} #${BUILD_NUMBER}"
                  git push origin master
                  '''
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
        BUILDCONFIG_INSTANCE_ID = "waiverdb-container-build-${currentBuild.id}"
      }
      steps {
        script {
          openshift.withCluster() {
            // OpenShift BuildConfig doesn't support specifying a tag name at build time.
            // We have to create a new BuildConfig for each container build.
            // Create a BuildConfig from a seperated Template.
            echo 'Creating a BuildConfig for container build...'
            def template = readYaml file: 'openshift/waiverdb-container-template.yaml'
            def processed = openshift.process(template,
              "-p", "NAME=${env.BUILDCONFIG_INSTANCE_ID}",
              '-p', "WAIVERDB_GIT_REPO=${params.WAIVERDB_GIT_REPO}",
              '-p', "WAIVERDB_GIT_REF=${params.WAIVERDB_GIT_REF}",
              '-p', "WAIVERDB_IMAGE_TAG=${env.TEMP_TAG}",
              '-p', "WAIVERDB_VERSION=${env.WAIVERDB_VERSION}",
              '-p', "WAIVERDB_IMAGESTREAM_NAME=${params.WAIVERDB_IMAGESTREAM_NAME}",
              '-p', "WAIVERDB_IMAGESTREAM_NAMESPACE=${params.WAIVERDB_IMAGESTREAM_NAMESPACE}",
            )
            def created = openshift.apply(processed)
            def bc = created.narrow('bc')
            echo 'Starting a container build from the created BuildConfig...'
            buildSelector = bc.startBuild()
            // `buildSelector.logs()` can be dumb when the OpenShift Build is not started.
            // Let's wait for it to be started or completed (failed).
            echo 'Waiting for the container build to be started...'
            timeout(5) { // 5 min
              buildSelector.watch {
                return !(it.object().status.phase in ["New", "Pending", "Unknown"])
              }
            }
            echo 'Following container build logs...'
            // This function sometimes hangs infinitely.
            // Not sure it is a problem of OpenShift Jenkins Client plugin
            // or OpenShift.
            // FIXME: logs() step may fail with unknown reasons.
            timeout(time: 15, activity: false) {
              buildSelector.logs('-f')
            }
            // Ensure the build is stopped
            echo 'Waiting for the container build to be fully stopped...'
            timeout(5) { // 5 min
              buildSelector.watch {
                return it.object().status.phase != "Running"
              }
            }
            // Assert build result
            def ocpBuild = buildSelector.object()
            if (ocpBuild.status.phase != "Complete") {
              error("Failed to build container image for ${env.TEMP_TAG}, .status.phase=${ocpBuild.status.phase}.")
            }
            echo 'Container build is complete.'
            env.RESULTING_IMAGE_REF = ocpBuild.status.outputDockerImageReference
            env.RESULTING_IMAGE_DIGEST = ocpBuild.status.output.to.imageDigest
            def imagestream= created.narrow('is').object()
            env.RESULTING_IMAGE_REPO = imagestream.status.dockerImageRepository
            env.RESULTING_TAG = env.TEMP_TAG
          }
        }
      }
      post {
        cleanup {
          script {
            openshift.withCluster() {
              echo 'Tearing down...'
              openshift.selector('bc', [
                'app': env.BUILDCONFIG_INSTANCE_ID,
                'template': 'waiverdb-container-template',
                ]).delete()
            }
          }
        }
      }
    }
    stage('Run functional tests') {
      steps {
        script {
          openshift.withCluster() {
            openshift.withProject(params.WAIVERDB_INTEGRATION_TEST_BUILD_CONFIG_NAMESPACE) {
              def testBcSelector = openshift.selector('bc', params.WAIVERDB_INTEGRATION_TEST_BUILD_CONFIG_NAME)
              echo 'Starting a functional test for the built container image...'
              def buildSelector = testBcSelector.startBuild(
                  '-e', "IMAGE=${env.RESULTING_IMAGE_REPO}:${env.RESULTING_TAG}",
                  '-e', "WAIVERDB_GIT_REPO=${params.WAIVERDB_GIT_REPO}",
                  '-e', "WAIVERDB_GIT_REF=${params.WAIVERDB_GIT_REF}",
                )
              timeout(5) { // 5 min
                buildSelector.watch {
                  return !(it.object().status.phase in ["New", "Pending", "Unknown"])
                }
              }
              echo 'Following functional test logs...'
              // This function sometimes hangs infinitely. Not sure it is a problem of OpenShift Jenkins Client plugin or OpenShift.
              timeout(time: 15) {
                buildSelector.logs('-f')
              }
              echo 'Waiting for the integration test to be fully stopped...'
              timeout(5) { // 5 min
                buildSelector.watch {
                  return it.object().status.phase != "Running"
                }
              }
              // Assert build result
              def ocpBuild = buildSelector.object()
              if (ocpBuild.status.phase != "Complete") {
                error("Functional test failed for image ${env.TEMP_TAG}, .status.phase=${ocpBuild.status.phase}.")
              }
              echo 'Functional test is PASSED.'
            }
          }
        }
      }
    }
    stage('Push container') {
      when {
        expression {
          return params.FORCE_PUBLISH_IMAGE == 'true' ||
            params.WAIVERDB_GIT_REF == params.WAIVERDB_MAIN_BRANCH
        }
      }
      steps {
        script {
          def destinations = env.WAIVERDB_DEV_IMAGE_DESTINATIONS ?
            env.WAIVERDB_DEV_IMAGE_DESTINATIONS.split(',') : []
          openshift.withCluster() {
            def sourceImage = env.RESULTING_IMAGE_REPO + ":" + env.RESULTING_TAG
            if (env.REGISTRY_CREDENTIALS) {
               dir ("${env.HOME}/.docker") {
                    writeFile file:'config.json', text: env.REGISTRY_CREDENTIALS
               }
            }
            // pull the built image from imagestream
            echo "Pulling container from ${sourceImage}..."
            def registryToken = readFile(file: '/var/run/secrets/kubernetes.io/serviceaccount/token')
            withEnv(["SOURCE_IMAGE_REF=${sourceImage}", "TOKEN=${registryToken}"]) {
              sh '''set -e +x # hide the token from Jenkins console
              mkdir -p _build
              skopeo copy \
                --src-cert-dir=/var/run/secrets/kubernetes.io/serviceaccount/ \
                --src-creds=serviceaccount:"$TOKEN" \
                docker://"$SOURCE_IMAGE_REF" dir:_build/waiverdb_container
              '''
            }
            // push to registries
            def pushTasks = destinations.collectEntries {
              ["Pushing ${it}" : {
                def dest = it
                // Only docker and atomic registries are allowed
                if (!it.startsWith('atomic:') && !it.startsWith('docker://')) {
                  dest = 'docker://' + it
                }
                echo "Pushing container to ${dest}..."
                withEnv(["DEST_IMAGE_REF=${dest}"]) {
                  /* Pushes to the internal registry can sometimes randomly fail
                  * with "unknown blob" due to a known issue with the registry
                  * storage configuration. So we retry up to 5 times. */
                  retry(5) {
                    sh 'skopeo copy dir:_build/waiverdb_container "$DEST_IMAGE_REF"'
                  }
                }
              }]
            }
            parallel pushTasks
          }
        }
      }
    }
    stage('Tag into image stream') {
      when {
        expression {
          return "${params.WAIVERDB_DEV_IMAGE_TAG}" && params.TAG_INTO_IMAGESTREAM == "true" &&
            (params.FORCE_PUBLISH_IMAGE == 'true' || params.WAIVERDB_GIT_REF == params.WAIVERDB_MAIN_BRANCH)
        }
      }
      steps {
        script {
          openshift.withCluster() {
            openshift.withProject("${params.WAIVERDB_IMAGESTREAM_NAMESPACE}") {
              def sourceRef = "${params.WAIVERDB_IMAGESTREAM_NAME}:${env.RESULTING_TAG}"
              def destRef = "${params.WAIVERDB_IMAGESTREAM_NAME}:${params.WAIVERDB_DEV_IMAGE_TAG}"
              echo "Tagging ${sourceRef} as ${destRef}..."
              openshift.tag("${sourceRef}", "${destRef}")
            }
          }
        }
      }
    }
  }
  post {
    cleanup {
      script {
        if (env.RESULTING_TAG) {
          echo "Removing tag ${env.RESULTING_TAG} from the ImageStream..."
          openshift.withCluster() {
            openshift.withProject("${params.WAIVERDB_IMAGESTREAM_NAMESPACE}") {
              openshift.tag("${params.WAIVERDB_IMAGESTREAM_NAME}:${env.RESULTING_TAG}",
                "-d")
            }
          }
        }
      }
    }
  }
}
