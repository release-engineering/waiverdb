stage('Run integration tests') {
  stages {
    stage('Request Pipeline') {
      steps {
        script {
          openshift.withCluster() {
            openshift.withProject(params.PIPELINE_AS_A_SERVICE_BUILD_NAMESPACE) {
              c3i.buildAndWait(script: this, objs: "bc/pipeline-as-a-service",
                '-e', "DEFAULT_IMAGE_TAG=${env.ENVIRONMENT}",
                '-e', "WAIVERDB_IMAGE=${env.TRACKED_CONTAINER_REPO}:${env.TRACKED_TAG}",
                '-e', "PIPELINE_ID=${env.PIPELINE_ID}",
                '-e', "PAAS_DOMAIN=${env.PAAS_DOMAIN}",
                '-e', "SERVICES_TO_DEPLOY='resultsdb-updater greenwave resultsdb umb waiverdb krb5 ldap'",
                '-e', "PIPELINE_PARAMS='{\"greenwave_wrapper_koji\": \"\", \"greenwave_side_tags_url_template\": \"\", \"greenwave_dist_git_url_template\": \"\" }'",
                '-e', "TRIGGERED_BY=${env.BUILD_URL}"
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
        pipeline_data = controller.getVars()
        c3i.sendResultToMessageBus(
          imageRef: pipeline_data.WAIVERDB_IMAGE,
          digest: pipeline_data.WAIVERDB_IMAGE_DIGEST,
          environment: env.ENVIRONMENT,
          scratch: false,
          docs: 'https://gitlab.cee.redhat.com/devops/factory2-segment-tests/tree/master/integration-test'
        )
      }
    }
    failure {
      script {
        c3i.archiveContainersLogs(env.PIPELINE_ID)
      }
    }
  }
}
