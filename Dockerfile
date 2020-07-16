FROM fedora:32
LABEL \
    name="WaiverDB application" \
    vendor="WaiverDB developers" \
    license="GPLv2+" \
    build-date=""

# The caller should build a waiverdb RPM package using ./rpmbuild.sh and then pass it in this arg.
ARG waiverdb_rpm
ARG waiverdb_common_rpm

COPY $waiverdb_rpm /tmp
COPY $waiverdb_common_rpm /tmp

RUN dnf -y install \
    --enablerepo=updates-testing \
    python3-gunicorn \
    /tmp/$(basename $waiverdb_rpm) \
    /tmp/$(basename $waiverdb_common_rpm) \
    && dnf -y clean all \
    && rm -f /tmp/*

COPY docker/ /docker/
# Allow a non-root user to install a custom root CA at run-time
RUN chmod g+w /etc/pki/tls/certs/ca-bundle.crt

USER 1001
EXPOSE 8080
ENTRYPOINT ["/docker/docker-entrypoint.sh"]
CMD ["/usr/bin/gunicorn-3", "--bind", "0.0.0.0:8080", "--access-logfile", "-", "--enable-stdio-inheritance", "waiverdb.wsgi:app"]
