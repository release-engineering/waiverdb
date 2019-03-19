# Promoting a WaiverDB image to Stage or Prod with WaiverDB C3I Pipeline

## Prerequisites
1. The WaiverDB image to be promoted must be available from a container registry (like `quay.io`). If you want to build an image from a Git branch or a Pagure pull-request, see [Build and test a pull-request with WaiverDB C3I pipeline](./pipeline-build-and-test-pr.md) or [Build and test a Git branch with WaiverDB C3I pipeline](./pipeline-build-and-test-branch.md).

## Steps

1. Log into UpShift, switch to `waiverdb-test` project:

    ```
    oc project waiverdb-test
    ```

2. To promote an image to stage, use pipeline job `waiverdb-promoting-to-stage`. To promote an image to prod, use pipeline job `waiverdb-promoting-to-prod`.


3. Trigger your chosen pipeline job:

    ```
    oc start-build <job-name> -e IMAGE=<image-to-promote> [ -e CONTAINER_REGISTRY_CREDENTIALS=<registry-credentials>]
    ```

    For example, to promote `quay.io/factory2/waiverdb:foo` to stage, run:

    ```
    oc start-build waiverdb-promoting-to-stage -e IMAGE=quay.io/factory2/waiverdb:foo
    ```

    If your container registry requires authentication, use the `CONTAINER_REGISTRY_CREDENTIALS` parameter.
    For more information about parameters of integration test pipeline jobs, see  [waiverdb-image-promotion-template.yaml](../pipelines/templates/waiverdb-image-promotion-template.yaml).

4. Visualize the promotion process at https://paas.upshift.redhat.com/console/project/waiverdb-test/browse/pipelines/$job-name.

5. Verify the image change by logging into your container registry (quay.io).