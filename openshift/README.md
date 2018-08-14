# OpenShift Manifests for CI/CD Pipelines and Deployment

This directory includes OpenShift manifests and Dockerfiles that can be used
to deploy a CI/CD pipeline and a test environment for WaiverDB.

## WaiverDB Pipeline

WaiverDB Pipeline gives you control over building, testing, deploying, and promoting WaiverDB on OpenShift.

It uses [OpenShift Pipeline][], a technology powered by OpenShift, using a combination of the [Jenkins Pipeline Build Strategy][], [Jenkinsfiles][], and the OpenShift Domain Specific Language (DSL) powered by the [OpenShift Jenkins Pipeline (DSL) Plugin][] (previously called the OpenShift Jenkins Client Plugin).

When starting a new pipeline build, the Jenkins slave and the whole testing environment will be dynamically created as OpenShift pods. And after the build is complete, all of them will be destroyed. Concurrent builds are also allowed (but currently disabled) to increase the overall throughput.

Before using the Pipeline, please ensure your Jenkins master has the following plugins installed and configured:
- [Openshift Sync plugin][] [1]
- [Openshift Client plugin][OpenShift Jenkins Pipeline (DSL) Plugin] [1]
- [Kubernetes plugin][] [1]
- [SSH Agent plugin][]:

Notes:
[1]: Those plugins are preinstalled if you are using the Jenkins master shipped with OpenShift.

### Dev Pipeline
Dev Pipeline is a part of the WaiverDB Pipeline, covers the following steps:

- Run Flake8 and Pylint checks
- Run unit tests
- Build Docs
- Publish Docs
- Build SRPM
- Build RPM
- Invoke Rpmlint
- Build container
- Run functional tests
- Push container

Whenever a new Git commit comes in, the dev pipeline is run against the commit to ensure that this commit can be merged into mainline, and a container is built and pushed to the specified registry.

#### Installation
To install the pipeline to a project on OpenShift, just login to your
OpenShift cloud, switch to a project (I would suggest using a separated
project instead of sharing the real dev/stage/prod environment):

```bash
  oc login <your OpenShift cloud>
  oc project waiverdb-test # your project name
```

Then instantiate the template with default parameters
(this will set up a pipeline to build the upstream repo and publish the result to upstream registries):

```bash
  oc process --local -f ./waiverdb-dev-pipeline.yml | oc apply -f -
```

Or you want to set up a pipeline for your own fork:

```bash
  NAME=waiverdb-dev-pipeline
  oc process --local -f ./waiverdb-dev-pipeline-template.yml \
   -p NAME="$NAME" \
   -p WAIVERDB_GIT_REPO="https://pagure.io/forks/<username>/waiverdb.git" \
   -p WAIVERDB_GIT_REF="<your devel branch>" \
   -p WAIVERDB_DEV_IMAGE_DESTINATIONS="docker.io/<username>/waiverdb:latest" \
   -p PAGURE_DOC_REPO_NAME="forks/<username>/waiverdb" \
 | oc apply -f -
```

#### Configure Secrets for Push Containers
This section is optional if publishing containers is not needed.

To publish the container built by the pipeline, you need to set up a secret for your target container registries.

- Please go to your registry dashboard and create a robot account.
- Backup your docker-config-json file (`$HOME/.docker/config.json`) if present.
- Run `docker login` with the robot account you just created to produce a new docker-config-json file.
- Create a new [OpenShift secret for registries][] named `factory2-pipeline-registry-credentials` from your docker-config-json file:
```bash
  oc create secret generic factory2-pipeline-registry-credentials \
    --from-file=.dockerconfigjson="$HOME/.docker/config.json" \
    --type=kubernetes.io/dockerconfigjson
```

#### Configure Secrets for Publishing Pagure Docs
This section is optional if publishing Pagure Docs is not needed.

- Please go to your Pagure repository settings and activate the project documentation.
- Create an SSH key pair for publishing Pagure Docs and show the public key:
```bash
ssh-keygen -f "$HOME/.ssh/id_rsa_pagure"
cat "$HOME/.ssh/id_rsa_pagure.pub"
```
- Go to your Pagure repository settings, and add the public key as the deploy key.
- Add the private key to your OpenShift project by creating a new [OpenShift secret for SSH key authentication][]:
```bash
  oc create secret generic pagure-doc-secret \
    --from-file=ssh-privatekey="$HOME/.ssh/id_rsa_pagure" \
    --type=kubernetes.io/ssh-auth
  # This label is used by Jenkins OpenShift Sync Plugin for synchonizing OpenShift secrets with Jenkins Credentials.
  oc label secret pagure-doc-secret credential.sync.jenkins.openshift.io=true
```

#### Build Jenkins slave container image
Before running the pipeline, you need to build a container image for Jenkins slave pods.
This step should be repeated every time you change
the Dockerfile for the Jenkins slave pods.
```bash
 oc start-build waiverdb-dev-pipeline-jenkins-slave
```

#### Trigger A Pipeline Build
To trigger a pipeline build, start the `waiverdb-dev-pipeline` BuildConfig with the Git commit ID or branch that you want to
test against:
```bash
  oc start-build waiverdb-dev-pipeline -e WAIVERDB_GIT_REF=<branch_name_or_commit_id>
```
You can go to the OpenShift Web console to check the details of the pipeline build.

### Integration Test Pipeline
Typically, integration tests should be rerun
- when a new container image of WaiverDB is built
- when any service that WaiverDB depends on is updated to a new version
- to ensure an image is mature enough for promotion

Hence, splitting the functional test stage makes it possible to run integration
tests individually. It can also be a step of a larger pipeline.

#### Installation
To install this OpenShift pipeline:
```bash
oc process --local -f pipelines/templates/waiverdb-integration-test-template.yaml \
   -p NAME=waiverdb-integration-test \
  | oc apply -f -
```

Additional installations with default parameters for dev, stage, and prod environments:
```bash
# for dev
oc process --local -f pipelines/templates/waiverdb-integration-test-template.yaml \
   -p NAME=waiverdb-dev-integration-test \
   -p IMAGE="quay.io/factory2/waiverdb:latest" \
  | oc apply -f -
# for stage
oc process --local -f pipelines/templates/waiverdb-integration-test-template.yaml \
   -p NAME=waiverdb-stage-integration-test \
   -p IMAGE="quay.io/factory2/waiverdb:stage" \
  | oc apply -f -
# for prod
oc process --local -f pipelines/templates/waiverdb-integration-test-template.yaml \
   -p NAME=waiverdb-prod-integration-test \
   -p IMAGE="quay.io/factory2/waiverdb:prod" \
  | oc apply -f -
```

#### Usage
To trigger a pipeline build for each environment, run:
```bash
# for dev
oc start-build waiverdb-dev-integration-test
# for stage
oc start-build waiverdb-stage-integration-test
# for prod
oc start-build waiverdb-prod-integration-test
```

To trigger a custom integration test, start a new pipeline build with the image reference you want to test against and the Git repository and commit ID/branch name
where the functional test suite is used:
```bash
oc start-build waiverdb-integration-test \
  -e IMAGE="quay.io/factory2/waiverdb:test" \
  -e WAIVERDB_GIT_REPO=https://pagure.io/forks/<username>/waiverdb.git \
  -e WAIVERDB_GIT_REF=my-branch # master branch is default
```

#### NOTE
The stage of reporting test results to ResultsDB has not been implemented.

[OpenShift Pipeline]: https://docs.okd.io/3.9/dev_guide/openshift_pipeline.html
[Jenkins Pipeline Build Strategy]: https://docs.openshift.com/container-platform/3.9/dev_guide/dev_tutorials/openshift_pipeline.html
[Jenkinsfiles]: https://jenkins.io/doc/book/pipeline/jenkinsfile/
[OpenShift Jenkins Pipeline (DSL) Plugin]: https://github.com/openshift/jenkins-client-plugin
[Openshift Sync plugin]: https://github.com/openshift/jenkins-sync-plugin
[Kubernetes plugin]: https://github.com/jenkinsci/kubernetes-plugin
[SSH Agent plugin]: https://github.com/jenkinsci/ssh-agent-plugin
[OpenShift secret for registries]:https://docs.openshift.com/container-platform/3.9/dev_guide/builds/build_inputs.html#using-docker-credentials-for-private-registries
[OpenShift secret for SSH key authentication]: https://docs.openshift.com/container-platform/3.9/dev_guide/builds/build_inputs.html#source-secrets-ssh-key-authentication
