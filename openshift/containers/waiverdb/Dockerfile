FROM fedora:28
LABEL \
    name="waiverdb" \
    description="WaiverDB application" \
    vendor="WaiverDB developers" \
    license="GPLv2+" \
    build-date=""

# Installing WaiverDB dependencies
RUN dnf -y install python3-gunicorn \
    python3-flask \
    python3-sqlalchemy \
    python3-flask-restful \
    python3-flask-sqlalchemy \
    python3-psycopg2 \
    python3-gssapi \
    python3-mock \
    python3-flask-oidc \
    python3-click \
    python3-flask-migrate \
    python3-stomppy \
    python3-fedmsg \
  && dnf -y clean all

ARG WAIVERDB_GIT_REPO=https://pagure.io/waiverdb.git
ARG WAIVERDB_GIT_REF=master
ARG WAIVERDB_VERSION=
ENV WAIVERDB_VERSION=$WAIVERDB_VERSION

# Installing CA certificate
RUN if [ -n "$WAIVERDB_CACERT_URL" ]; then \
        cd /etc/pki/ca-trust/source/anchors \
        && curl -O --insecure --location "$WAIVERDB_CACERT_URL" \
        && update-ca-trust extract; \
    fi

# Installing WaiverDB
RUN dnf -y install git python3-pip \
  && mkdir -p /usr/local/src \
  && git clone "$WAIVERDB_GIT_REPO" /usr/local/src/waiverdb \
  && cd /usr/local/src/waiverdb \
  && git fetch origin "$WAIVERDB_GIT_REF" \
  && git checkout -f "$WAIVERDB_GIT_REF" \
  && pip3 install --no-deps . \
  && mkdir -p /etc/waiverdb \
  && cp conf/settings.py.example /etc/waiverdb/settings.py \
  && cp conf/client.conf.example /etc/waiverdb/client.conf \
  && dnf -y history undo last \
  && dnf -y clean all \
  # Allow a non-root user to install a custom root CA at run-time
  && cp -r docker/ / \
  && chmod g+w /etc/pki/tls/certs/ca-bundle.crt \
  && cd / && rm -rf /usr/local/src/waiverdb

USER 1001
EXPOSE 8080
ENTRYPOINT ["/docker/docker-entrypoint.sh"]
CMD ["/usr/bin/gunicorn-3", "--bind", "0.0.0.0:8080", "--access-logfile", "-", "--enable-stdio-inheritance", "waiverdb.wsgi:app"]
