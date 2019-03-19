# Build and test a pull-request using WaiverDB C3I pipeline

If you are looking to rebuild a pull-request, the simplest way is to update your pull-request. WaiverDB C3I pipeline should be aware of your pull-request change and start a new pipeline build automatically.
This document is for advanced users to manually trigger a `premerge` pipeline build.

- Note: 
    1. You should have the `admin` or `edit` permission to `waiverdb-test` project on Red Hat internal OpenShift cloud (PSI UpShift).
    2. DO NOT push test images to `latest`, `stage`, or `prod` tag, otherwise the change will go to the real `dev`, `stage`, or `prod` environments!

1. Log into UpShift, switch to `waiverdb-test` project:

    ```
    oc project waiverdb-test
    ```

2. Start a new build of `waiverdb-premerge` pipeline job with WaiverDB Git repository and pull-request branch (in the form of `pull/<number>/head`) that you want to build from and the tag to be applied:

    ```
    oc start-build waiverdb-premerge [ -e WAIVERDB_GIT_REPO=<git-repository-url> ] -e WAIVERDB_GIT_REF=<git-branch-name> [ [ -e FORCE_PUBLISH_IMAGE=true -e WAIVERDB_DEV_IMAGE_TAG=<tag-name> ]
    ```

    For example, to build and test pull-request #123, run

    ```
    oc start-build waiverdb-premerge -e WAIVERDB_GIT_REF=pull/123/head
    ```

    If you don't specify `FORCE_PUBLISH_IMAGE`, the newly built image will be thrown away after build.
    `WAIVERDB_DEV_IMAGE_TAG` defaults to `latest`. Change the tag name to avoid accidentally overwriting the `latest` image.

    For more information about job parameters, see  [waiverdb-build-template.yaml](../pipelines/templates/waiverdb-build-template.yaml).

3. Visualize the build process at https://paas.upshift.redhat.com/console/project/waiverdb-test/browse/pipelines/waiverdb-premerge.

4. Your newly built image will be available at `quay.io/factory2/waiverdb:<tag-name>` if `FORCE_PUBLISH_IMAGE` and `WAIVERDB_DEV_IMAGE_TAG` is specified.
