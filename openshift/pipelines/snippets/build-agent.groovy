agent {
  kubernetes {
    cloud params.OPENSHIFT_CLOUD_NAME
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
        - name: USER_NAME
          value: jenkins
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
