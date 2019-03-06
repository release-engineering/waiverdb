library identifier: 'c3i@master', changelog: false,
  retriever: modernSCM([$class: 'GitSCMSource', remote: 'https://pagure.io/c3i-library.git'])
import static org.apache.commons.lang.StringEscapeUtils.escapeHtml;
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
          factory2-pipeline-kind: "waiverdb-build-pipeline"
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
    PAGURE_API = "${params.PAGURE_URL}/api/0"
    PAGURE_REPO_IS_FORK = "${params.PAGURE_REPO_IS_FORK}"
    PAGURE_REPO_HOME = "${env.PAGURE_URL}${env.PAGURE_REPO_IS_FORK == 'true' ? '/fork' : ''}/${params.PAGURE_REPO_NAME}"
  }
  stages {
    stage('Prepare') {
      steps {
        script {
          // check out specified branch/commit
          /*def scmVars =*/ checkout([$class: 'GitSCM',
            branches: [[name: params.WAIVERDB_GIT_REF]],
            userRemoteConfigs: [[url: params.WAIVERDB_GIT_REPO, refspec: '+refs/heads/*:refs/remotes/origin/* +refs/pull/*/head:refs/remotes/origin/pull/*/head']],
          ])

          // get current commit ID
          // FIXME: Due to a bug discribed in https://issues.jenkins-ci.org/browse/JENKINS-45489,
          // the return value of checkout() is unreliable.
          // Not working: env.WAIVERDB_GIT_COMMIT = scmVars.GIT_COMMIT
          env.WAIVERDB_GIT_COMMIT = sh(returnStdout: true, script: 'git rev-parse HEAD').trim()
          echo "Build ${params.WAIVERDB_GIT_REF}, commit=${env.WAIVERDB_GIT_COMMIT}"

          // Is the current branch a pull-request? If no, env.PR_NO will be empty.
          env.PR_NO = getPrNo(params.WAIVERDB_GIT_REF)

          // Generate a version-release number for the target Git commit
          def versions = sh(returnStdout: true, script: 'source ./version.sh && echo -en "$WAIVERDB_VERSION\n$WAIVERDB_CONTAINER_VERSION"').split('\n')
          env.WAIVERDB_VERSION = versions[0]
          env.WAIVERDB_CONTAINER_VERSION = versions[1]
          env.TEMP_TAG = env.WAIVERDB_CONTAINER_VERSION + '-jenkins-' + currentBuild.id
        }
      }
    }
    stage('Update Build Info') {
      when {
        expression {
          return params.PAGURE_URL && params.PAGURE_REPO_NAME
        }
      }
      steps {
        script {
          // Set friendly display name and description
          if (env.PR_NO) { // is pull-request
            env.PR_URL = "${env.PAGURE_REPO_HOME}/pull-request/${env.PR_NO}"
            echo "Building PR #${env.PR_NO}: ${env.PR_URL}"
            // NOTE: Old versions of OpenShift Client Jenkins plugin are buggy to handle arguments
            // with special bash characters (like whitespaces, #, etc).
            // https://bugzilla.redhat.com/show_bug.cgi?id=1625518
            currentBuild.displayName = "PR#${env.PR_NO}"
            // To enable HTML syntax in build description, go to `Jenkins/Global Security/Markup Formatter` and select 'Safe HTML'.
            def pagureLink = """<a href="${env.PR_URL}">${currentBuild.displayName}</a>"""
            try {
              def prInfo = withPagure {
                it.getPR(env.PR_NO)
              }
              pagureLink = """<a href="${env.PR_URL}">PR#${env.PR_NO}: ${escapeHtml(prInfo.title)}</a>"""
              // set PR status to Pending
              setBuildStatusOnPagurePR(null, 'Pending')
            } catch (Exception e) {
              echo "Error using pagure API: ${e}"
            }
            currentBuild.description = pagureLink
          } else {
            currentBuild.displayName = "${env.WAIVERDB_GIT_REF}: ${env.WAIVERDB_GIT_COMMIT.substring(0, 7)}"
            currentBuild.description = """<a href="${env.PAGURE_REPO_HOME}/c/${env.WAIVERDB_GIT_COMMIT}">${currentBuild.displayName}</a>"""
          }
        }
        sh 'cp conf/settings.py.example conf/settings.py'
        sh 'pip3 install --user -r ./requirements.txt'
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
                  return "${params.PAGURE_DOC_REPO_NAME}" && (params.WAIVERDB_GIT_REF == params.WAIVERDB_MAIN_BRANCH || env.FORCE_PUBLISH_DOCS == "true")
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
        BUILDCONFIG_INSTANCE_ID = "waiverdb-temp-${currentBuild.id}-${UUID.randomUUID().toString().substring(0,7)}"
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
              // A pull-request branch, like pull/123/head, cannot be built with commit ID
              // because refspec cannot be customized in an OpenShift build .
              '-p', "WAIVERDB_GIT_REF=${env.PR_NO ? params.WAIVERDB_GIT_REF : env.WAIVERDB_GIT_COMMIT}",
              '-p', "WAIVERDB_IMAGE_TAG=${env.TEMP_TAG}",
              '-p', "WAIVERDB_VERSION=${env.WAIVERDB_VERSION}",
              '-p', "WAIVERDB_IMAGESTREAM_NAME=${params.WAIVERDB_IMAGESTREAM_NAME}",
              '-p', "WAIVERDB_IMAGESTREAM_NAMESPACE=${params.WAIVERDB_IMAGESTREAM_NAMESPACE}",
            )
            def created = openshift.apply(processed)
            def bc = created.narrow('bc')
            echo 'Starting a container build from the created BuildConfig...'
            buildSelector = bc.startBuild()
            c3i.wait(buildSelector.name())
            echo 'Container build succeeds.'
            def ocpBuild = buildSelector.object()
            env.RESULTING_IMAGE_REF = ocpBuild.status.outputDockerImageReference
            env.RESULTING_IMAGE_DIGEST = ocpBuild.status.output.to.imageDigest
            def imagestream= created.narrow('is').object()
            env.RESULTING_IMAGE_REPO = imagestream.status.dockerImageRepository
            env.RESULTING_TAG = env.TEMP_TAG
          }
        }
      }
      post {
        failure {
          echo "Failed to build container image ${env.TEMP_TAG}."
        }
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
                  '-e', "WAIVERDB_GIT_REPO=${params.WAIVERDB_GIT_REPO}",
                  '-e', "IMAGE=${env.RESULTING_IMAGE_REPO}:${env.RESULTING_TAG}",
                  '-e', "WAIVERDB_GIT_REF=${env.PR_NO ? env.WAIVERDB_GIT_REF : env.WAIVERDB_GIT_COMMIT}",
                  '-e', "IMAGE_IS_SCRATCH=${params.WAIVERDB_GIT_REF != params.WAIVERDB_MAIN_BRANCH}",
                )
              c3i.wait(buildSelector.name())
              echo "Functional test passed."
            }
          }
        }
      }
      post {
        failure {
          echo "Functional test failed."
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
                def dest = "${it}:${params.WAIVERDB_DEV_IMAGE_TAG ?: 'latest'}"
                // Only docker and atomic registries are allowed
                if (!dest.startsWith('atomic:') && !dest.startsWith('docker://')) {
                  dest = 'docker://' + dest
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
    success {
      script {
        // updating Pagure PR flag and make a comment
        if (env.PR_NO && params.PAGURE_API_KEY_SECRET_NAME) {
          try {
            setBuildStatusOnPagurePR(100, 'Build passed.')
            echo "Updated PR #${env.PR_NO} status to PASS."
          } catch (e) {
            echo "Error updating PR #${env.PR_NO} status to PASS: ${e}"
          }
        }
      }
    }
    failure {
      script {
        // updating Pagure PR flag
        if (env.PR_NO && params.PAGURE_API_KEY_SECRET_NAME) {
          try {
            setBuildStatusOnPagurePR(0, 'Build failed.')
            echo "Updated PR #${env.PR_NO} status to FAILURE."
          } catch (e) {
            echo "Error updating PR #${env.PR_NO} status to FAILURE: ${e}"
          }
          try {
            commentOnPR("""
            Build ${env.WAIVERDB_GIT_COMMIT} [FAILED](${env.BUILD_URL})!
            Rebase or make new commits to rebuild.
            """.stripIndent())
            echo "Comment made."
          } catch (e) {
            echo "Error making a comment on PR #${env.PR_NO}: ${e}"
          }
        }
        // sending email
        if (params.MAIL_ADDRESS){
          try {
            sendBuildStatusEmail('failed')
          } catch (e) {
            echo "Error sending email: ${e}"
          }
        }
      }
    }
  }
}
@NonCPS
def getPrNo(branch) {
  def prMatch = branch =~ /^(?:.+\/)?pull\/(\d+)\/head$/
  return prMatch ? prMatch[0][1] : ''
}
def withPagure(args=[:], cl) {
  args.apiUrl = env.PAGURE_API
  args.repo = env.PAGURE_REPO_NAME
  args.isFork = env.PAGURE_REPO_IS_FORK == 'true'
  def pagureClient = pagure.client(args)
  return cl(pagureClient)
}
def withPagureCreds(args=[:], cl) {
  def pagureClient = null
  withCredentials([string(credentialsId: "${env.PIPELINE_NAMESPACE}-${env.PAGURE_API_KEY_SECRET_NAME}", variable: 'TOKEN')]) {
    args.token = env.TOKEN
    pagureClient = withPagure(args, cl)
  }
  return pagureClient
}
def setBuildStatusOnPagurePR(percent, String comment) {
  withPagureCreds {
    it.updatePRStatus(username: 'c3i-jenkins', uid: 'ci-pre-merge',
      url: env.BUILD_URL, percent: percent, comment: comment, pr: env.PR_NO)
  }
}
def commentOnPR(String comment) {
  withPagureCreds {
    it.commentOnPR(comment: comment, pr: env.PR_NO)
  }
}
def sendBuildStatusEmail(String status) {
  def recipient = params.MAIL_ADDRESS
  def subject = "Jenkins job ${env.JOB_NAME} #${env.BUILD_NUMBER} ${status}."
  def body = "Build URL: ${env.DEV_BUILD_URL}"
  if (env.PR_NO) {
    subject = "Jenkins job ${env.JOB_NAME}, PR #${env.PR_NO} ${status}."
    body += "\nPull Request: ${env.PR_URL}"
  }
  emailext to: recipient, subject: subject, body: body
}
