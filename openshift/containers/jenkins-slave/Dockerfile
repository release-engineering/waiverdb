#FIXME: The Pipeline is currently using this Dockerfile to produce images. The one located at the project root is not changed in case of breaking anything.
FROM docker-registry.upshift.redhat.com/devops-automation/rad-slave-fedora:latest
LABEL name="waiverdb-jenkins-slave" \
      description="Jenkins slave for WaiverDB dev tests" \
      vendor="WaiverDB Developers" \
      license="GPLv2+"

USER root

ARG TINI_VERSION=0.18.0

RUN dnf -y install 'dnf-command(builddep)' dnf-utils git mock-core-configs tar gzip skopeo \
    wget postgresql make rpmdevtools rpmlint \
    python3-flake8 python3-pylint python3-pytest \
    python3-sphinx python3-sphinxcontrib-httpdomain \
    python3-ldap \
    origin-clients \
  # install tini, a tiny but valid init for containers
  && wget -O /usr/local/bin/tini "https://github.com/krallin/tini/releases/download/v${TINI_VERSION}/tini" \
  && chmod +rx /usr/local/bin/tini \
  # install wait-for-it.sh, to allow containers to wait for other services to come up
  && wget -O /usr/local/bin/wait-for-it "https://raw.githubusercontent.com/vishnubob/wait-for-it/master/wait-for-it.sh" \
  && chmod +rx /usr/local/bin/tini /usr/local/bin/wait-for-it \
  # clean up
  && dnf clean all

# install build dependencies for WaiverDB
COPY waiverdb.spec /usr/local/src/waiverdb/waiverdb.spec
RUN cd /usr/local/src/waiverdb \
  && dnf -y builddep waiverdb.spec \
  && dnf clean all \
  && cd / && rm -rf /usr/local/src/waiverdb
WORKDIR /var/lib/jenkins/
ENTRYPOINT ["/usr/local/bin/tini", "--", "jenkins-slave"]
USER 1000
