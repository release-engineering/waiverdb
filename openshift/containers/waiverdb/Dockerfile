FROM fedora:32
LABEL \
    name="waiverdb" \
    maintainer="WaiverDB developers" \
    description="WaiverDB application" \
    vendor="WaiverDB developers" \
    license="GPLv2+"

COPY . /usr/local/src/waiverdb/

# Allow a non-root user to install a custom root CA at run-time
RUN cp -r /usr/local/src/waiverdb/docker/ / \
  && chmod g+w /etc/pki/tls/certs/ca-bundle.crt

# Installing WaiverDB
RUN dnf -y install \
    python3-gunicorn \
    python3-ldap \
    python3-pip \
    findutils \
    rpm-build \
  && cd /usr/local/src/waiverdb \
  # install dependencies defined in RPM spec file
  && rpm --query --requires --specfile ./waiverdb.spec | grep --invert-match waiverdb | xargs -d '\n' dnf -y install \
  # install using --no-deps option to ensure nothing comes from PyPi
  && pip3 install --no-deps . \
  && mkdir -p /etc/waiverdb \
  && cp conf/settings.py.example /etc/waiverdb/settings.py && cp conf/client.conf.example /etc/waiverdb/client.conf \
  && dnf -y autoremove findutils rpm-build && dnf -y clean all && cd / && rm -rf /usr/local/src/waiverdb

USER 1001
EXPOSE 8080
ENTRYPOINT ["/docker/docker-entrypoint.sh"]
CMD ["/usr/bin/gunicorn-3", "--bind", "0.0.0.0:8080", "--access-logfile", "-", "--enable-stdio-inheritance", "waiverdb.wsgi:app"]
