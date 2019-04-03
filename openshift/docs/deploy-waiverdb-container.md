# Deploy WaiverDB to OpenShift manually
NOTE: This instruction should only be used to deploy a test environment of WaiverDB. Production deployment shouldn't use the OpenShift manifests in this document.

1. To create an environment from the template, process the template file `openshift/waiverdb-test-template.yaml` and apply it:

    ```
    oc process -f openshift/waiverdb-test-template.yaml -p TEST_ID=<test-id> -p WAIVERDB_APP_IMAGE=quay.io/factory2/waiverdb:0.1.2.dev24-git.94c0119 | oc apply -f -
    ```

    where `<test-id>` should be a unique string to identify your deployed environment, and `WAIVERDB_APP_IMAGE` should be the WaiverDB image you want to run.

2. To clean up the environment, use a selector on the environment label:

    ```
    oc delete dc,deploy,pod,configmap,secret,svc,route -l environment=test-<test-id>
    ```

    where `<test-id>` should equal to the string given in step 1.
