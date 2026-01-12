FROM quay.io/fedora/python-313:20260107@sha256:41ebd88e1ea61238c4f3a07816dc30c5f97cf3b941178cf1c6c62a6bcbc8d121 AS builder

# builder should use root to install/create all files
USER root

# hadolint ignore=DL3033,DL3041,DL4006,SC2039,SC3040
RUN set -exo pipefail \
    && mkdir -p /mnt/rootfs \
    # install runtime dependencies
    && dnf install -y \
        --installroot=/mnt/rootfs \
        --use-host-config \
        --setopt install_weak_deps=false \
        --nodocs \
        --disablerepo=* \
        --enablerepo=fedora,updates \
        krb5-libs \
        openldap \
        python3 \
    && dnf --installroot=/mnt/rootfs clean all \
    # Install uv
    && curl -LsSf https://astral.sh/uv/install.sh | sh \
    && python3 -m venv /venv

ENV \
    PIP_DEFAULT_TIMEOUT=100 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONFAULTHANDLER=1 \
    PYTHONHASHSEED=random \
    PYTHONUNBUFFERED=1

WORKDIR /build

# Copy only specific files to avoid accidentally including any generated files
# or secrets.
COPY waiverdb ./waiverdb
COPY conf ./conf
COPY docker ./docker
COPY \
    pyproject.toml \
    uv.lock \
    README.md \
    ./

# hadolint ignore=SC1091
RUN set -ex \
    && export PATH=/root/.cargo/bin:"$PATH" \
    && . /venv/bin/activate \
    && uv build --wheel \
    && version=$(uv version --short) \
    && uv pip install --no-cache dist/waiverdb-"$version"-py3*.whl \
    && deactivate \
    && mv /venv /mnt/rootfs \
    && mkdir -p /mnt/rootfs/app /mnt/rootfs/etc/waiverdb \
    && cp -v docker/docker-entrypoint.sh /mnt/rootfs/app/entrypoint.sh \
    && cp conf/settings.py.example /mnt/rootfs/etc/waiverdb/settings.py \
    && cp conf/client.conf.example /mnt/rootfs/etc/waiverdb/client.conf

# This is just to satisfy linters
USER 1001

# --- Final image
FROM scratch
ARG GITHUB_SHA
ARG EXPIRES_AFTER
LABEL \
    summary="WaiverDB application" \
    description="An engine for storing waivers against test results." \
    maintainer="Red Hat, Inc." \
    license="GPLv2+" \
    url="https://github.com/release-engineering/waiverdb" \
    vcs-type="git" \
    vcs-ref=$GITHUB_SHA \
    io.k8s.display-name="WaiverDB" \
    quay.expires-after=$EXPIRES_AFTER

ENV \
    PYTHONFAULTHANDLER=1 \
    PYTHONHASHSEED=random \
    PYTHONUNBUFFERED=1 \
    WEB_CONCURRENCY=8

COPY --from=builder /mnt/rootfs/ /
COPY --from=builder \
    /etc/yum.repos.d/fedora.repo \
    /etc/yum.repos.d/fedora-updates.repo \
    /etc/yum.repos.d/
WORKDIR /app

USER 1001
EXPOSE 8080

# Validate virtual environment
RUN /app/entrypoint.sh python -c 'import waiverdb' \
    && /app/entrypoint.sh gunicorn --version \
    && /app/entrypoint.sh waiverdb --help

ENTRYPOINT ["/app/entrypoint.sh"]
CMD ["gunicorn", "--bind", "0.0.0.0:8080", "--access-logfile", "-", "--enable-stdio-inheritance", "waiverdb.wsgi:app"]
