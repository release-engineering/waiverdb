# Instructions to Fix a Broken Pipeline Build

1. `waiverdb-premerge` and `waiverdb-postmerge` builds could fail if new package dependencies are introduced. Because we don't root access to the Jenkins agent pod, dependency changes can't be applied automatically. To make changes to the dependencies, you have to rebuild the Jenkins agent image. Follow the `Build Jenkins slave container image` section in [OpenShift Manifests for CI/CD Pipelines and Deployment](pipeline-deployment.md) document.

2. If you see no updates on the pull-request after build, probably it is because the Pagure API key is expired.
Pagure API key is used by the pipeline jobs to interact with pagure.io, however it expires every 3 months.
To renew the Pagure API key, just generate a new key and reconfigure it. Refer to `Configure a Pagure API Key` section in OpenShift Manifests for CI/CD Pipelines and Deployment](pipeline-deployment.md) for more information.