agent {
  kubernetes {
    cloud "${params.OPENSHIFT_CLOUD_NAME}"
    label "jenkins-slave-${UUID.randomUUID().toString()}"
    serviceAccount "${params.JENKINS_AGENT_SERVICE_ACCOUNT}"
    defaultContainer 'jnlp'
    yaml """
    apiVersion: v1
    kind: Pod
    metadata:
      labels:
        app: "${env.JOB_BASE_NAME}"
        factory2-pipeline-build-number: "${env.BUILD_NUMBER}"
    spec:
      containers:
      - name: jnlp
        image: "${params.JENKINS_AGENT_IMAGE}"
        imagePullPolicy: Always
        tty: true
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
