# WaiverDB on OpenShift

This directory contains documents and OpenShift manifests for WaiverDB OpenShift deployments
and CI/CD automation on top of OpenShift.

## What do you want?

- Build and deploy a WaiverDB container manually
    - [Build a WaiverDB container locally](docs/build-waiverdb-container.md)
    - [Deploy a WaiverDB container to OpenShift manually](docs/deploy-waiverdb-container.md)
- Build, test, and deploy a WaiverDB container with WaiverDB C3I Pipeline (using CI/CD approach)
    - [Build and test a pull-request with WaiverDB C3I pipeline](docs/pipeline-build-and-test-pr.md)
    - [Build and test a Git branch with WaiverDB C3I pipeline](docs/pipeline-build-and-test-branch.md)
    - [Test a WaiverDB container with WaiverDB C3I pipeline](docs/pipeline-test-image.md)
    - [Deploy a WaiverDB container to dev environment](docs/pipeline-deploy-to-dev.md)
    - [Promote a WaiverDB container to stage or prod environment](docs/pipeline-promote-to-stage-or-prod.md)
    - [Fix broken WaiverDB C3I pipeline](docs/pipeline-fix-broken-build.md)
- Advanced topics about WaiverDB C3I pipeline
    - [WaiverDB C3I Pipeline Introduction](https://docs.google.com/a/redhat.com/document/d/e/2PACX-1vR11OgAmBRF1_Lprs8hpgchNodMb9sh1QKCO6t61JaGYs7UpBcsBJSQW_G7fqrwuRLBQPDrDbwKUtek/pub): See how WaiverDB C3I Pipeline works.
    - [Deploy WaiverDB C3I pipeline (not WaiverDB app) to OpenShift](docs/pipeline-deployment.md)
