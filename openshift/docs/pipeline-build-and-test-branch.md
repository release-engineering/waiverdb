# Build and test a Git branch using WaiverDB C3I pipeline
- Note: 
    1. You should have the `admin` or `edit` permission to `waiverdb-test` project on Red Hat internal OpenShift cloud (PSI UpShift).
    2. DO NOT push test images to `latest`, `stage`, or `prod` tag, otherwise they would be deployed to real `dev`, `stage`, or `prod` environments!

1. Log into UpShift, switch to `waiverdb-test` project:

    ```
    oc project waiverdb-test
    ```

2. Start a new build of `waiverdb-postmerge` pipeline job, specifying the WaiverDB Git repository and branch that you want to build from and the tag to be applied:

    ```
    oc start-build waiverdb-postmerge [ -e WAIVERDB_GIT_REPO=<git-repository-url> ] [ -e WAIVERDB_GIT_REF=<git-branch-name> ] [ -e FORCE_PUBLISH_IMAGE=true ] [ -e WAIVERDB_DEV_IMAGE_TAG=<tag-name> ]
    ```
    
    For example, to rebuild the latest `master` branch, run

    ```
    oc start-build waiverdb-postmerge
    ```

    To build the `feature-foo` branch and push it to `quay.io/factory2/waiverdb:feature-foo`, run

    ```
    oc start-build waiverdb-postmerge -e WAIVERDB_GIT_REF=feature-foo -e FORCE_PUBLISH_IMAGE=true -e WAIVERDB_DEV_IMAGE_TAG=feature-foo
    ```

    For more information about job parameters, see  [waiverdb-build-template.yaml](../pipelines/templates/waiverdb-build-template.yaml).

3. Visualize the build process at `https://console-openshift-console.apps.<CLUSTER>/k8s/ns/waiverdb-test/buildconfigs/waiverdb-postmerge/builds`.
4. Your newly built image will be available at `quay.io/factory2/waiverdb:<tag-name>` if `WAIVERDB_GIT_REF` is `master` or `FORCE_PUBLISH_IMAGE` is `true`. Otherwise the newly built image will be thrown away.
