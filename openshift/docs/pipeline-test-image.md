# Test a WaiverDB Container Image with WaiverDB C3I Pipeline

## Prerequisites
1. The WaiverDB image to be tested must be available from a container registry (like `quay.io`). If you want to build an image from a Git branch or a Pagure pull-request, see [Build and test a pull-request with WaiverDB C3I pipeline](./pipeline-build-and-test-pr.md) or [Build and test a Git branch with WaiverDB C3I pipeline](./pipeline-build-and-test-branch.md).

## Steps

1. Log into UpShift, switch to `waiverdb-test` project:

    ```
    oc project waiverdb-test
    ```

2. Choose the pipeline job according to type of integration you want to run:
    - waiverdb-dev-integration-test: test the image in a dev preview environment
    - waiverdb-stage-integration-test: test the image in a stage preview environment
    - waiverdb-prod-integration-test: test the image in a prod preview environment

3. Test the image by triggering a new pipeline build from your chosen pipeline job:

    ```
    oc start-build <job-name> -e IMAGE=<image-to-test> [ -e CONTAINER_REGISTRY_CREDENTIALS=<registry-credentials>]
    ```

    For example, to test `quay.io/factory2/waiverdb:foo` in a stage preview environment. run:

    ```
    oc start-build waiverdb-stage-integration-test -e IMAGE=quay.io/factory2/waiverdb:foo
    ```

    If your container registry requires authentication, use the `CONTAINER_REGISTRY_CREDENTIALS` parameter.
    For more information about parameters of integration test pipeline jobs, see  [waiverdb-integration-test-template.yaml](../pipelines/templates/waiverdb-integration-test-template.yaml).

4. Visualize the build process at https://paas.upshift.redhat.com/console/project/waiverdb-test/browse/pipelines/$job-name.

5. After the test finishes, a UMB message will be sent to `VirtualTopic.eng.ci.container-image.test.complete` topic. The test result will also be available at ResultsDB with the artifact type `container-image`. 