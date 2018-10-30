#!/bin/bash

# Dynamically associate a username to OpenShift assigned UIDs.
# See: https://docs.openshift.org/latest/creating_images/guidelines.html#openshift-origin-specific-guidelines

export USER_ID=$(id -u)
export GROUP_ID=$(id -g)

# Skip for root user
if [ x"$USER_ID" != x"0" ]; then
    echo "jenkins:x:${USER_ID}:${GROUP_ID}:jenkins:${HOME}:/bin/bash" >> /etc/passwd
fi

exec "$@"
