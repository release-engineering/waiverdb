FROM fedora:28
LABEL \
    name="WaiverDB application" \
    vendor="WaiverDB developers" \
    license="GPLv2+" \
    build-date=""

# The caller should build a waiverdb RPM package using ./rpmbuild.sh and then pass it in this arg.
ARG waiverdb_rpm
ARG waiverdb_common_rpm
# The caller can optionally provide a cacert url
ARG cacert_url=undefined

COPY $waiverdb_rpm /tmp
COPY $waiverdb_common_rpm /tmp

RUN dnf -y install \
    --enablerepo=updates-testing \
    python3-gunicorn \
    /tmp/$(basename $waiverdb_rpm) \
    /tmp/$(basename $waiverdb_common_rpm) \
    && dnf -y clean all \
    && rm -f /tmp/*

RUN if [ "$cacert_url" != "undefined" ]; then \
        cd /etc/pki/ca-trust/source/anchors \
        && curl -O --insecure $cacert_url \
        && update-ca-trust extract; \
    fi

USER 1001
EXPOSE 8080

CMD ["/usr/bin/gunicorn-3", "--bind", "0.0.0.0:8080", "--access-logfile", "-", "--enable-stdio-inheritance", "waiverdb.wsgi:app"]


