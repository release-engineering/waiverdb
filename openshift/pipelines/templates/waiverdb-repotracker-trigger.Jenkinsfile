{% include "snippets/c3i-library.groovy" %}
pipeline {
  {% include "snippets/default-agent.groovy" %}
  options {
    timestamps()
    timeout(time: 120, unit: 'MINUTES')
    buildDiscarder(logRotator(numToKeepStr: '10'))
  }
  triggers {
    ciBuildTrigger(
      noSquash: false,
      providerList: [
        activeMQSubscriber(
          name: params.MESSAGING_PROVIDER,
          overrides: [topic: params.MESSAGING_TOPIC],
          selector: "repo = '${params.TRACKED_CONTAINER_REPO}' AND action IN ('added', 'updated') AND tag = '${params.TRACKED_TAG}'",
        )
      ]
    )
  }
  stages {
    stage("Message Check and setup") {
      steps {
        script {
          if (!params.CI_MESSAGE) {
            error("This build is not started by a CI message. Only configurations were done.")
          }
          def message = readJSON text: params.CI_MESSAGE
          echo "Tag :${message.tag} is ${message.action} in ${message.repo}. New digest: ${message.digest}"
          def env.IMAGE = "${message.repo}@${message.digest}"
          echo "Triggering a job to test if ${env.IMAGE} meets all criteria of desired tag :${message.tag}"
          env.IMAGE_IS_SCRATCH = false
          env.PIPELINE_ID = "c3i-waiverdb-tag-${message.tag}-${message.digest[-9..-1]}"
        }
      }
    }
    {% include "snippets/waiverdb-full-integration-test.groovy" %}
  }
}
