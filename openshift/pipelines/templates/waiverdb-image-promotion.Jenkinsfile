pipeline {
  {% include "snippets/default-agent.groovy" %}
  options {
    timestamps()
    timeout(time: 30, unit: 'MINUTES')
  }
  environment {
    PIPELINE_NAMESPACE = readFile(file: '/run/secrets/kubernetes.io/serviceaccount/namespace').trim()
    SERVICE_ACCOUNT_TOKEN = readFile(file: '/var/run/secrets/kubernetes.io/serviceaccount/token').trim()
  }
  stages {
    stage ('Prepare') {
      steps {
        script {
          // Setting up registry credentials
          dir ("${env.HOME}/.docker") {
            // for the OpenShift internal registry
            def dockerConfig = readJSON text: '{ "auths": {} }'
            dockerConfig.auths['docker-registry.default.svc:5000'] = [
              'email': '',
              'auth': sh(returnStdout: true, script: 'set +x; echo -n "serviceaccount:$SERVICE_ACCOUNT_TOKEN" | base64 -').trim()
              ]
            // merging user specified credentials
            if (params.CONTAINER_REGISTRY_CREDENTIALS) {
              openshift.withCluster() {
                def dockerconf = openshift.selector('secret', params.CONTAINER_REGISTRY_CREDENTIALS).object().data['.dockerconfigjson']
                def dockerString = new String(dockerconf.decodeBase64())
                toBeMerged = readJSON text: dockerString
                dockerConfig.auths.putAll(toBeMerged.auths)
              }
            }
            // writing to ~/.docker/config.json
            writeJSON file: 'config.json', json: dockerConfig
          }
        }
      }
    }
    stage('Pull Container') {
      steps {
        echo "Pulling container image ${params.IMAGE}..."
        sh '''set -e +x # hide the token from Jenkins console
        rm -rf _build/container
        mkdir -p _build
        skopeo copy \
          --src-cert-dir=/var/run/secrets/kubernetes.io/serviceaccount \
          docker://"$IMAGE" dir:_build/container
        '''
      }
    }
    stage('Promote') {
      steps {
        script {
          def destinations = params.PROMOTING_DESTINATIONS ?
            params.PROMOTING_DESTINATIONS.split(',') : []
          openshift.withCluster() {
            def pushTasks = destinations.collectEntries {
              ["Pushing ${it}" : {
                def dest = it
                // Only docker and atomic registries are allowed
                if (!it.startsWith('atomic:') && !it.startsWith('docker://')) {
                  dest = 'docker://' + it
                }
                dest += ':' + params.DEST_TAG
                echo "Pushing container to ${dest}..."
                withEnv(["DEST_IMAGE_REF=${dest}"]) {
                  /* Pushes to the internal registry can sometimes randomly fail
                  * with "unknown blob" due to a known issue with the registry
                  * storage configuration. So we retry up to 5 times. */
                  retry(5) {
                    sh 'skopeo copy dir:_build/container "$DEST_IMAGE_REF"'
                  }
                }
              }]
            }
            parallel pushTasks
          }
        }
      }
    }
    stage('Tag Image Stream') {
      when {
        expression {
          return params.DEST_IMAGESTREAM_NAME && params.TAG_INTO_IMAGESTREAM == "true"
        }
      }
      steps {
        script {
          def destRef = "${params.DEST_IMAGESTREAM_NAMESPACE ?: env.PIPELINE_NAMESPACE }/${params.DEST_IMAGESTREAM_NAME}:${params.DEST_TAG}"
          openshift.withCluster() {
            echo "Tagging ${params.IMAGE} into ${destRef}..."
            openshift.tag('--source=docker', params.IMAGE, destRef)
          }
        }
      }
    }
  }
}
