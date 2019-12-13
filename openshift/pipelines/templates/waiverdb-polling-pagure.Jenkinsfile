{% include "snippets/c3i-library.groovy" %}
pipeline {
  agent {
    kubernetes {
      cloud "${OPENSHIFT_CLOUD_NAME}"
      label "jenkins-slave-${UUID.randomUUID().toString()}"
      serviceAccount "${NAME}-jenkins-slave"
      defaultContainer 'jnlp'
      yaml """
      apiVersion: v1
      kind: Pod
      metadata:
        labels:
          app: "jenkins-${env.JOB_BASE_NAME}"
          factory2-pipeline-kind: "waiverdb-polling-to-pagure-pipeline"
          factory2-pipeline-build-number: "${env.BUILD_NUMBER}"
      spec:
        containers:
        - name: jnlp
          image: "${JENKINS_AGENT_IMAGE}"
          imagePullPolicy: Always
          tty: true
          resources:
            requests:
              memory: 378Mi
              cpu: 200m
            limits:
              memory: 768Mi
              cpu: 500m
      """
    }
  }
  options {
    timestamps()
  }
  environment {
    PIPELINE_NAMESPACE = readFile('/run/secrets/kubernetes.io/serviceaccount/namespace').trim()
    PAGURE_URL = "${PAGURE_URL}"
    PAGURE_REPO_IS_FORK = "${PAGURE_REPO_IS_FORK}"
    PAGURE_POLLING_FOR_PR = "${PAGURE_POLLING_FOR_PR}"
    PAGURE_REPO_HOME = "${env.PAGURE_URL}${env.PAGURE_REPO_IS_FORK == 'true' ? '/fork' : ''}/${PAGURE_REPO_NAME}"
    GIT_URL = "${env.PAGURE_URL}/${env.PAGURE_REPO_IS_FORK == 'true' ? 'forks/' : ''}${PAGURE_REPO_NAME}.git"
    PREMERGE_JOB_NAME = "${PREMERGE_JOB_NAME}"
    POSTMERGE_JOB_NAME = "${POSTMERGE_JOB_NAME}"
  }
  triggers { pollSCM("${PAGURE_POLLING_SCHEDULE}") }
  stages {
    stage('Prepare') {
      agent { label 'master' }
      steps {
        script {
          // checking out the polled branch
          def polledBranch = env.PAGURE_POLLING_FOR_PR == 'true' ? 'origin/pull/*/head' : "origin/${PAGURE_POLLED_BRANCH}"
          def scmVars = checkout([$class: 'GitSCM',
            branches: [[name: polledBranch]],
            userRemoteConfigs: [
              [
                name: 'origin',
                url: env.GIT_URL,
                refspec: '+refs/heads/*:refs/remotes/origin/* +refs/pull/*/head:refs/remotes/origin/pull/*/head',
              ],
            ],
            extensions: [[$class: 'CleanBeforeCheckout']],
          ])
          env.WAIVERDB_GIT_COMMIT = scmVars.GIT_COMMIT
          // setting build display name
          def prefix = 'origin/'
          def branch = scmVars.GIT_BRANCH.startsWith(prefix) ? scmVars.GIT_BRANCH.substring(prefix.size())
            : scmVars.GIT_BRANCH // origin/pull/1234/head -> pull/1234/head, origin/master -> master
          env.WAIVERDB_GIT_BRANCH = branch
          echo "Build on branch=${env.WAIVERDB_GIT_BRANCH}, commit=${env.WAIVERDB_GIT_COMMIT}"
          if (env.PAGURE_POLLING_FOR_PR == 'false') {
            currentBuild.displayName = "${env.WAIVERDB_GIT_BRANCH}: ${env.WAIVERDB_GIT_COMMIT.substring(0, 7)}"
            currentBuild.description = """<a href="${env.PAGURE_REPO_HOME}/c/${env.WAIVERDB_GIT_COMMIT}">${currentBuild.displayName}</a>"""
          }
          else if (env.PAGURE_POLLING_FOR_PR == 'true' && branch ==~ /^pull\/[0-9]+\/head$/) {
            env.PR_NO = branch.split('/')[1]
            env.PR_URL = "${env.PAGURE_REPO_HOME}/pull-request/${env.PR_NO}"
            // To HTML syntax in build description, go to `Jenkins/Global Security/Markup Formatter` and select 'Safe HTML'.
            def pagureLink = """<a href="${env.PR_URL}">PR#${env.PR_NO}</a>"""
            echo "Building PR #${env.PR_NO}: ${env.PR_URL}"
            currentBuild.displayName = "PR#${env.PR_NO}"
            currentBuild.description = pagureLink
          } else { // This shouldn't happen.
            error("Build is aborted due to unexpected polling trigger actions.")
          }
        }
      }
    }
    stage('Update pipeline jobs') {
      when {
        expression {
          return "${PIPELINE_UPDATE_JOBS_DIR}" && env.PAGURE_POLLING_FOR_PR == 'false' && env.WAIVERDB_GIT_BRANCH == "${PAGURE_POLLED_BRANCH}"
        }
      }
      steps {
        checkout([$class: 'GitSCM',
          branches: [[name: env.WAIVERDB_GIT_COMMIT]],
          userRemoteConfigs: [
            [
              name: 'origin',
              url: env.GIT_URL,
              refspec: '+refs/heads/*:refs/remotes/origin/* +refs/pull/*/head:refs/remotes/origin/pull/*/head',
            ],
          ],
          extensions: [[$class: 'CleanBeforeCheckout']],
        ])
        script {
          dir('openshift/pipelines') {
            sh '''
            make install JOBS_DIR="${PIPELINE_UPDATE_JOBS_DIR}"
            '''
          }
        }
      }
    }
    stage('Build') {
      steps {
        script {
          openshift.withCluster() {
            def bc = env.PAGURE_POLLING_FOR_PR == 'true' ? env.PREMERGE_JOB_NAME : env.POSTMERGE_JOB_NAME
            def build = c3i.build(script: this, objs: "bc/${bc}",
              '-e', "WAIVERDB_GIT_REF=${env.WAIVERDB_GIT_BRANCH}",
            )
            c3i.waitForBuildStart(script: this, build: build)
            def devBuildInfo = build.object()
            def downstreamBuildName = devBuildInfo.metadata.name
            def downstreamBuildUrl = devBuildInfo.metadata.annotations['openshift.io/jenkins-build-uri']
            echo "Downstream build ${downstreamBuildName}(${downstreamBuildUrl}) started."
          }
        }
      }
    }
  }
}

