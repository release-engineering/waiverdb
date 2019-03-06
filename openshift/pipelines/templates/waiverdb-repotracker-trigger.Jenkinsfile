// Use scripted syntax because CIBuildTrigger currently doesn't support the declarative syntax
properties([
  disableConcurrentBuilds(),
  pipelineTriggers([
    // example: https://github.com/jenkinsci/jms-messaging-plugin/blob/9b9387c3a52f037ba0d019c2ebcf2a2796fc6397/src/test/java/com/redhat/jenkins/plugins/ci/integration/AmqMessagingPluginIntegrationTest.java
    [$class: 'CIBuildTrigger',
      providerData: [$class: 'ActiveMQSubscriberProviderData',
        name: params.MESSAGING_PROVIDER,
        overrides: [topic: params.MESSAGING_TOPIC],
        selector: "repo = '${params.TRACKED_CONTAINER_REPO}' AND action IN ('added', 'updated') AND tag = '${params.TRACKED_TAG}'",
      ],
    ],
  ]),
])

if (!params.CI_MESSAGE) {
  echo 'This build is not started by a CI message. Only configurations were done.'
  return
}

def label = "jenkins-slave-${UUID.randomUUID().toString()}"
podTemplate(
  cloud: "${params.OPENSHIFT_CLOUD_NAME}",
  label: label,
  serviceAccount: "${env.JENKINS_AGENT_SERVICE_ACCOUNT}",
  defaultContainer: 'jnlp',
  yaml: """
    apiVersion: v1
    kind: Pod
    metadata:
      labels:
        app: "jenkins-${env.JOB_BASE_NAME}"
        factory2-pipeline-kind: "waiverdb-repotracker-trigger"
        factory2-pipeline-build-number: "${env.BUILD_NUMBER}"
    spec:
      containers:
      - name: jnlp
        image: ${params.JENKINS_AGENT_IMAGE}
        imagePullPolicy: Always
        tty: true
        resources:
          requests:
            memory: 256Mi
            cpu: 200m
          limits:
            memory: 512Mi
            cpu: 300m
    """
) {
  node(label) {
    stage('trigger test') {
      def message = readJSON text: params.CI_MESSAGE
      echo "Tag :${message.tag} is ${message.action} in ${message.repo}. New digest: ${message.digest}"
      def image = "${message.repo}@${message.digest}"
      echo "Triggering a job to test if $image meets all criteria of desired tag :${message.tag}"
      def buildInfo = null
      openshift.withCluster() {
        def testBcSelector = openshift.selector('bc', params.TEST_JOB_NAME)
        def buildSelector = testBcSelector.startBuild(
            '-e', "IMAGE=${image}",
          )
          buildSelector.watch {
            return !(it.object().status.phase in ["New", "Pending"])
          }
          buildInfo = buildSelector.object()
      }
      echo "Build ${buildInfo.metadata.annotations['openshift.io/jenkins-build-uri'] ?: buildInfo.metadata.name} started."
    }
  }
}
