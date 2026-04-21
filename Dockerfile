FROM quay.io/fedora/python-313:20260319@sha256:95100620c772c9f4484923bb8d4e942c8da2a60ee32a84a905d612d7115b1a44 AS builder

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
        cyrus-sasl-gssapi \
        krb5-libs \
        openldap \
        python3 \
    && dnf --installroot=/mnt/rootfs clean all \
    # Install uv
    && curl -LsSf https://astral.sh/uv/install.sh | sh

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

ARG SHORT_COMMIT
ARG COMMIT_TIMESTAMP

# hadolint ignore=SC1091
RUN set -ex \
    && export PATH=/root/.cargo/bin:"$PATH" \
    && uv version "1.4.0.dev$COMMIT_TIMESTAMP+git.$SHORT_COMMIT" \
    && UV_PROJECT_ENVIRONMENT=/venv uv sync --frozen --no-dev --no-editable \
    && mv /venv /mnt/rootfs \
    && mkdir -p /mnt/rootfs/app /mnt/rootfs/etc/waiverdb \
    && cp -v docker/docker-entrypoint.sh /mnt/rootfs/app/entrypoint.sh \
    && cp conf/settings.py.example /mnt/rootfs/etc/waiverdb/settings.py \
    && cp conf/client.conf.example /mnt/rootfs/etc/waiverdb/client.conf

# This is just to satisfy linters
USER 1001

# --- Final image
FROM scratch
LABEL \
    summary="WaiverDB application" \
    description="An engine for storing waivers against test results." \
    maintainer="Red Hat, Inc." \
    license="GPLv2+" \
    url="https://github.com/release-engineering/waiverdb" \
    io.k8s.display-name="WaiverDB"

ENV \
    KRB5CCNAME=FILE:/tmp/krb5cc_waiverdb \
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
