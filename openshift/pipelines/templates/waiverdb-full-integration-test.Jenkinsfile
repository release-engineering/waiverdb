pipeline {
  agent {
    kubernetes {
      cloud "${params.JENKINS_AGENT_CLOUD_NAME}"
      label "jenkins-slave-${UUID.randomUUID().toString()}"
      serviceAccount "${params.JENKINS_AGENT_SERVICE_ACCOUNT}"
      defaultContainer 'jnlp'
      yaml """
      apiVersion: v1
      kind: Pod
      metadata:
        labels:
          app: "${env.JOB_BASE_NAME}"
          factory2-pipeline-kind: "waiverdb-integration-test-pipeline"
          factory2-pipeline-build-number: "${env.BUILD_NUMBER}"
      spec:
        containers:
        - name: jnlp
          image: "${params.JENKINS_AGENT_IMAGE}"
          imagePullPolicy: Always
          resources:
            requests:
              memory: 512Mi
              cpu: 200m
            limits:
              memory: 768Mi
              cpu: 300m
      """
    }
  }
  options {
    timestamps()
    timeout(time: 30, unit: 'MINUTES')
  }
  stages {
    stage('Run integration test') {
      steps {
        script {
          env.IMAGE_DIGEST = getImageDigest(env.IMAGE)
          if (!env.IMAGE_DIGEST) {
            env.IMAGE_URI = env.IMAGE
             if (!env.IMAGE_URI.startsWith('atomic:') && !env.IMAGE_URI.startsWith('docker://')) {
                  env.IMAGE_URI = 'docker://' + env.IMAGE_URI
              }
            echo "Image URI ${env.IMAGE_URI} doesn't contain the image digest. Fetching from the registry..."
            def metadataText = sh(returnStdout: true, script: 'skopeo inspect ${IMAGE_URI}').trim()
            def metadata = readJSON text: metadataText
            env.IMAGE_DIGEST = metadata.Digest
          }
          if (!env.IMAGE_DIGEST) {
            error "Couldn't get digest of image '${env.IMAGE}'"
          }
          echo "Digest of image '${env.IMAGE}': ${env.IMAGE_DIGEST}"

          // TODO: in the short term, we don't run integration tests here
          // but trigger the integration test job in the c3i project.
          openshift.withCluster() {
            openshift.withProject(params.BACKEND_INTEGRATION_TEST_JOB_NAMESPACE) {
              def testBcSelector = openshift.selector('bc', params.BACKEND_INTEGRATION_TEST_JOB)
              def buildSelector = testBcSelector.startBuild(
                '-e', "WAIVERDB_IMAGE=${env.IMAGE}",
                '-e', "TARGET_IMAGE_REPO=factory2/waiverdb",
                '-e', "TARGET_IMAGE_DIGEST=${env.IMAGE_DIGEST}",
                '-e', "TARGET_IMAGE_IS_SCRATCH=${env.IMAGE_IS_SCRATCH}",
                '-e', "TARGET_IMAGE_VERREL=${env.BUILD_TAG}",
                '-e', "TESTCASE_CATEGORY=${env.ENVIRONMENT}",
                )
              waitForBuild(buildSelector)
              echo "Integration test passed."
            }
          }
        }
      }
    }
  }
}

// Extract digest from the image URI
// e.g. factory2/waiverdb@sha256:35201c572fc8a137862b7a256476add8d7465fa5043d53d117f4132402f8ef6b
//   -> sha256:35201c572fc8a137862b7a256476add8d7465fa5043d53d117f4132402f8ef6b
@NonCPS
def getImageDigest(String image) {
  def matcher = (env.IMAGE =~ /@(sha256:\w+)$/)
  return matcher ? matcher[0][1] : ''
}

// Wait for a build to complete.
// Taken from https://pagure.io/c3i-library/blob/master/f/src/com/redhat/c3i/util/Builder.groovy
// Note: We can't use `c3i.wait()` here because that function switches to the default project.
//  Filed a PR for this issue: https://pagure.io/c3i-library/pull-request/19
def waitForBuild(build) {
  echo "Waiting for ${build.name()} to start..."
  timeout(5) {
    build.watch {
      return !(it.object().status.phase in ["New", "Pending", "Unknown"])
    }
  }
  def buildobj = build.object()
  def buildurl = buildobj.metadata.annotations['openshift.io/jenkins-build-uri']
  if (buildurl) {
    echo "Details: ${buildurl}"
  }
  if (buildobj.spec.strategy.type == "JenkinsPipeline") {
    echo "Waiting for ${build.name()} to complete..."
    build.logs("--tail=1")
    timeout(60) {
      build.watch {
        it.object().status.phase != "Running"
      }
    }
  } else {
    echo "Following build logs..."
    while (build.object().status.phase == "Running") {
      build.logs("--tail=1", "--timestamps=true", "-f")
    }
  }
  buildobj = build.object()
  if (buildobj.status.phase != "Complete") {
    error "Build ${buildobj.metadata.name} ${buildobj.status.phase}"
  }
  return build.name()
}
