FROM registry.fedoraproject.org/fedora:34 AS builder

RUN dnf -y install --nodocs --setopt=install_weak_deps=false \
        'dnf-command(builddep)' \
        git-core \
        rpm-build \
    && dnf -y clean all

COPY .git /src/.git

WORKDIR /src
RUN git reset --hard HEAD \
    && dnf -y builddep waiverdb.spec \
    && ./rpmbuild.sh -bb \
    && rm /src/rpmbuild-output/*/waiverdb-cli-*
WORKDIR /

FROM registry.fedoraproject.org/fedora:34
LABEL \
    name="waiverdb" \
    maintainer="WaiverDB developers" \
    description="WaiverDB application" \
    vendor="WaiverDB developers" \
    license="GPLv2+"

COPY --from=builder /src/rpmbuild-output /src/rpmbuild-output
COPY conf/settings.py.example /etc/waiverdb/settings.py
COPY conf/client.conf.example /etc/waiverdb/client.conf
COPY docker /docker

# Allow a non-root user to install a custom root CA at run-time
RUN chmod g+w /etc/pki/tls/certs/ca-bundle.crt \
    && dnf -y install \
        python3-gunicorn \
        python3-ldap \
        /src/rpmbuild-output/*/*.rpm \
    && dnf -y clean all \
    && rm -r /src

USER 1001
EXPOSE 8080
ENTRYPOINT ["/docker/docker-entrypoint.sh"]
CMD ["/usr/bin/gunicorn-3", "--bind", "0.0.0.0:8080", "--access-logfile", "-", "--enable-stdio-inheritance", "waiverdb.wsgi:app"]
