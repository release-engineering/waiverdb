# Build a WaiverDB container image locally
Note: If you are looking to build and test a WaiverDB container image using CI/CD, go to [Test and build an image using WaiverDB C3I pipeline](pipeline-build-and-test-branch.md).

1. Make sure your local machine has `podman` (or Docker) installed. If not, go to [Basic Setup and Use of Podman][1].

2. Go to the root directory of WaiverDB repo, build an image. Replace `<image>` with the image registry/repo:tag you want to use, such as `quay.io/yuxzhu/waiverdb:test`.

    ```
    podman build -t <image> -f ./openshift/containers/waiverdb/Dockerfile .
    ```

3. Push the image to the registry. (Suppose you have the access the registry repository)

    ```
    podman push <image>
    ```

[1]: https://github.com/containers/libpod/blob/master/docs/tutorials/podman_tutorial.md