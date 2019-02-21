import java.text.*
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
          tty: true
          env:
          - name: REGISTRY_CREDENTIALS
            valueFrom:
              secretKeyRef:
                name: "${params.CONTAINER_REGISTRY_CREDENTIALS}"
                key: '.dockerconfigjson'
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
    stage('Prepare') {
      steps {
        checkout([$class: 'GitSCM',
          branches: [[name: params.WAIVERDB_GIT_REF]],
          userRemoteConfigs: [[url: params.WAIVERDB_GIT_REPO, refspec: '+refs/heads/*:refs/remotes/origin/* +refs/pull/*/head:refs/remotes/origin/pull/*/head']],
        ])
      }
    }
    stage('Cleanup') {
      // Cleanup all test environments that were created 1 hour ago in case of failures of previous cleanups.
      steps {
        script {
          openshift.withCluster() {
            def df = new SimpleDateFormat("yyyy-MM-dd'T'HH:mm:ss'Z'")
            df.setTimeZone(TimeZone.getTimeZone('UTC'))
            // Get all OpenShift objects of previous test environments
            def oldObjs = openshift.selector('dc,deploy,configmap,secret,svc,route',
              ['template': 'waiverdb-test', 'app':'waiverdb'])
            def now = new Date()
            // Delete all objects that are older than 1 hour
            for (objName in oldObjs.names()) {
              def obj = openshift.selector(objName)
              def objData = obj.object()
              if (!objData.metadata.creationTimestamp)
                continue
              def creationTime = df.parse(objData.metadata.creationTimestamp)
              // 1 hour = 1000 * 60 * 60 ms
              if (now.getTime() - creationTime.getTime() < 1000 * 60 * 60)
                continue
              echo "Deleting ${objName}..."
              obj.delete()
              echo "Deleted ${objName}"
            }
          }
        }
      }
    }
    stage('Run functional tests') {
      environment {
        // Jenkins BUILD_TAG could be too long (> 63 characters) for OpenShift to consume
        TEST_ID = "${params.TEST_ID ?: 'jenkins-' + currentBuild.id}"
        ENVIRONMENT_LABEL = "test-${env.TEST_ID}"
      }
      steps {
        echo "Container image ${params.IMAGE} will be tested."
        script {
          openshift.withCluster() {
            def imageTag = (params.IMAGE =~ /(?::(\w[\w.-]{0,127}))?$/)[0][1]
            def imageRepo = imageTag ? params.IMAGE.substring(0, params.IMAGE.length() - imageTag.length() - 1) : params.IMAGE
            env.IMAGE_TAG = imageTag ?: 'latest'
            def template = readYaml file: 'openshift/waiverdb-test-template.yaml'
            def webPodReplicas = 1 // The current quota in UpShift is agressively limited
            def models = openshift.process(template,
              '-p', "TEST_ID=${env.TEST_ID}",
              '-p', "WAIVERDB_APP_IMAGE_REPO=${imageRepo}",
              '-p', "WAIVERDB_APP_VERSION=${imageTag ?: 'latest'}",
              '-p', "WAIVERDB_REPLICAS=${webPodReplicas}",
            )
            def objects = openshift.apply(models)
            echo "Waiting for test pods with label environment=${env.ENVIRONMENT_LABEL} to become Ready"
            //def rm = dcSelector.rollout()
            def dcs = openshift.selector('dc', ['environment': env.ENVIRONMENT_LABEL])
            def rm = dcs.rollout()
            def pods = openshift.selector('pods', ['environment': env.ENVIRONMENT_LABEL])
            timeout(15) {
              pods.untilEach(webPodReplicas + 1) {
                def pod = it.object()
                if (pod.status.phase in ["New", "Pending", "Unknown"]) {
                  return false
                }
                if (pod.status.phase == "Running") {
                  for (cond in pod.status.conditions) {
                      if (cond.type == 'Ready' && cond.status == 'True') {
                          return true
                      }
                  }
                  return false
                }
                error("Test pod ${pod.metadata.name} is not running. Current phase is ${pod.status.phase}.")
              }
            }
            def appPod = openshift.selector('pods', ['environment': env.ENVIRONMENT_LABEL, 'service': 'web']).object()
            env.IMAGE_DIGEST = appPod.status.containerStatuses[0].imageID.split('@')[1]
            // Run functional tests
            def route_hostname = objects.narrow('route').object().spec.host
            echo "Running tests against https://${route_hostname}/"
            withEnv(["WAIVERDB_TEST_URL=https://${route_hostname}/"]) {
              sh 'py.test-3 -v --junitxml=junit-functional-tests.xml functional-tests/'
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
              /* Extract logs for debugging purposes */
              openshift.selector('deploy,pods', ['environment': env.ENVIRONMENT_LABEL]).logs()
            }
          }
        }
        cleanup {
          script {
            openshift.withCluster() {
              /* Tear down everything we just created */
              echo "Tearing down test resources..."
              openshift.selector('dc,deploy,configmap,secret,svc,route',
                      ['environment': env.ENVIRONMENT_LABEL]).delete()
            }
          }
        }
      }
    }
  }
  post {
    always {
      script {
        // currentBuild.result == null || currentBuild.result == 'SUCCESS' indicates a successful build,
        // because it's possible that the pipeline engine hasn't set the value nor seen an error when reaching to this line.
        // See example code in https://jenkins.io/doc/book/pipeline/jenkinsfile/#deploy
        def sendResult = sendCIMessage \
          providerName: 'Red Hat UMB', \
          overrides: [topic: 'VirtualTopic.eng.ci.container-image.test.complete'], \
          messageType: 'Custom', \
          messageProperties: '', \
          messageContent: """
          {
            "ci": {
              "name": "C3I Jenkins",
              "team": "DevOps",
              "url": "${env.JENKINS_URL}",
              "docs": "https://pagure.io/waiverdb/blob/master/f/openshift",
              "irc": "#pnt-devops-dev",
              "email": "pnt-factory2-devel@redhat.com",
              "environment": "stage"
            },
            "run": {
              "url": "${env.BUILD_URL}",
              "log": "${env.BUILD_URL}/console",
              "debug": "",
              "rebuild": "${env.BUILD_URL}/rebuild/parametrized"
            },
            "artifact": {
              "type": "container-image",
              "repository": "factory2/waiverdb",
              "digest": "${env.IMAGE_DIGEST}",
              "nvr": "waiverdb:${env.IMAGE_TAG}",
              "issuer": "c3i-jenkins",
              "scratch": true
            },
            "system":
               [{
                  "os": "${params.JENKINS_AGENT_IMAGE}",
                  "provider": "openshift",
                  "architecture": "x86_64"
               }],
            "type": "tier1",
            "category": "integration",
            "status": "${currentBuild.result == null || currentBuild.result == 'SUCCESS' ? 'passed':'failed'}",
            "xunit": "${env.BUILD_URL}/artifacts/junit-functional-tests.xml",
            "generated_at": "${new Date().format("yyyy-MM-dd'T'HH:mm:ss'Z'", TimeZone.getTimeZone('UTC'))}",
            "namespace": "waiverdb-test",
            "version": "0.1.0"
          }
          """
        // echo sent message id and content
        echo sendResult.getMessageId()
        echo sendResult.getMessageContent()
      }
    }
  }
}
