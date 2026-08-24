#!/bin/bash
set -xeuo pipefail

image=$1

sed -i "s/ build: .*/ image: $image/" docker-compose.yml
echo "Using images:" && grep -E " image:| build: " docker-compose.yml

compose() {
    uvx podman-compose "$@"
}

trap "compose down" QUIT TERM INT HUP EXIT

# Use --no-deps to avoid podman-compose hanging on
# `podman wait --condition=healthy` (containers/podman#28192).
compose --verbose up --no-build --no-deps -d --pull=missing

# Wait for services to be ready.
curl --retry 50 --retry-delay 1 --retry-max-time 60 --retry-all-errors -sf http://127.0.0.1:5004/healthcheck

uvx --with tox-uv tox -e functional -- --driver=Chrome
