#!/bin/bash
set -xeuo pipefail

image=$1

sed -i "s/ build: .*/ image: $image/" docker-compose.yml
echo "Using images:" && grep -E " image:| build: " docker-compose.yml

trap "podman-compose down" QUIT TERM INT HUP EXIT
podman-compose up --no-build -d

tox -e functional -- --driver=Chrome
