{% include "snippets/c3i-library.groovy" %}
def pipeline_data
pipeline {
  {% include "snippets/default-agent.groovy" %}
  options {
    timestamps()
    timeout(time: 30, unit: 'MINUTES')
  }
  environment {
    TRIGGER_NAMESPACE = readFile("/run/secrets/kubernetes.io/serviceaccount/namespace").trim()
  }
  stages {
    stage('Request Pipeline') {
      openshift.withCluster() {
        openshift.withProject(env.TRIGGER_NAMESPACE) {
          def testroute = openshift.create('route', 'edge', "test-${env.BUILD_NUMBER}",  '--service=test', '--port=8080')
          def testhost = testroute.object().spec.host
          env.PAAS_DOMAIN = testhost.minus("test-${env.BUILD_NUMBER}-${env.TRIGGER_NAMESPACE}.")
          testroute.delete()
        }
      }
      echo "Routes end with ${env.PAAS_DOMAIN}"
      steps {
        script {
          env.PIPELINE_ID = 'c3i-pipeline-' + UUID.randomUUID().toString().substring(0,4)
          openshift.withCluster() {
            openshift.withProject(params.PIPELINEAAS_PROJECT) {
              c3i.buildAndWait(script: this, objs: "bc/pipeline-as-a-service",
                '-e', "DEFAULT_IMAGE_TAG=${env.ENVIRONMENT}",
                '-e', "WAIVERDB_IMAGE=${env.IMAGE}",
                '-e', "PIPELINE_ID=${env.PIPELINE_ID}",
                '-e', "PAAS_DOMAIN=${env.PAAS_DOMAIN}"
                '-e', "KOJI_HUB_IMAGE=",
                '-e', "MBS_BACKEND_IMAGE=",
                '-e', "MBS_FRONTEND_IMAGE=",
                '-e', "KOJI_HUB_IMAGE="
              )
            }
          }
        }
      }
    }
    stage('Run integration test') {
      steps {
        script {
          c3i.clone(repo: params.BACKEND_INTEGRATION_TEST_REPO,
            branch: params.BACKEND_INTEGRATION_TEST_REPO_BRANCH)
          pipeline_data = readJSON(text: controller.getVars())
          sh "${env.WORKSPACE}/${BACKEND_INTEGRATION_TEST_FILE} https://${env.PIPELINE_ID}.${env.PAAS_DOMAIN}"
        }
      }
    }
  }
  post {
    changed {
      script {
        if (params.MAIL_ADDRESS) {
          emailext to: "${env.MAIL_ADDRESS}",
          subject: "${env.JOB_NAME} ${env.BUILD_NUMBER} changed: ${currentBuild.result}",
          body: "${env.JOB_NAME} ${env.BUILD_NUMBER} changed. Current status: ${currentBuild.result}. You can check it out: ${env.BUILD_URL}"
        }
      }
    }
    always {
      script {
        if (!env.MESSAGING_PROVIDER) {
          // Don't send a message if messaging provider is not configured
          return
        }
        c3i.sendResultToMessageBus(
          pipeline_data.WAIVERDB_IMAGE,
          pipeline_data.WAIVERDB_IMAGE_DIGEST,
          env.BUILD_TAG,
          env.TARGET_IMAGE_IS_SCRATCH == "true",
          env.MESSAGING_PROVIDER
        )
      }
    }
    failure {
      script {
        openshift.withCluster() {
          openshift.withProject(env.PIPELINE_ID) {
            echo 'Getting logs from all pods...'
            openshift.selector('pods').logs('--tail=100')
          }
        }
      }
    }
    cleanup {
      script {
        if (env.NO_CLEANUP_AFTER_TEST == 'true') {
          return
        }
        openshift.withCluster() {
          openshift.withProject(env.PIPELINE_ID) {
            /* Tear down everything we just created */
            echo 'Tearing down test resources...'
            openshift.selector('all,pvc,configmap,secret',
                               ['c3i.redhat.com/pipeline': env.PIPELINE_ID]).delete('--ignore-not-found=true')
          }
        }
      }
    }
  }
}
