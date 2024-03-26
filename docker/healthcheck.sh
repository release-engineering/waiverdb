#!/bin/bash
PODMAN=${PODMAN:-podman}

while ! $PODMAN healthcheck run waiverdb_dev_1; do
    sleep 1
done
