# Deploy a WaiverDB Container Image to Dev Environment with WaiverDB C3I Pipeline

## Steps

1. [Run waiverdb-postmerge pipeline job](pipeline-build-and-test-branch.md) with `-e -e FORCE_PUBLISH_IMAGE=true` and `-e WAIVERDB_DEV_IMAGE_TAG=latest`.

2. Verify the image change by logging into your container registry (quay.io).