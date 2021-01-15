# Based on the rad-jenkins image, which is in turn based on:
# https://github.com/jenkinsci/docker-jnlp-slave/blob/master/Dockerfile
# https://github.com/jenkinsci/docker-slave/blob/master/Dockerfile

FROM registry.fedoraproject.org/fedora:32
LABEL \
    org.opencontainers.image.title="Jenkins agent image for WaiverDB" \
    org.opencontainers.image.description="Jenkins slave for WaiverDB dev tests" \
    org.opencontainers.image.vendor="WaiverDB Developers" \
    org.opencontainers.image.licenses="GPLv2+"

ARG USER=jenkins
ARG UID=10000
ARG HOME_DIR=/home/jenkins
ARG REMOTING_VERSION=3.36
ARG TINI_VERSION=0.18.0
ARG CA_URLS=""

USER root

RUN dnf -y \
    --setopt=deltarpm=0 \
    --setopt=install_weak_deps=false \
    --setopt=tsflags=nodocs \
    install \
    java-1.8.0-openjdk-headless gettext git-core \
    tar gzip skopeo wget make bind-utils \
    origin-clients python3-jinja2-cli \
    # Jenkins pipeline 'sh' steps seem to require ps
    procps-ng \
    # Tools to build and test waiverdb
    'dnf-command(builddep)' dnf-utils git mock-core-configs \
    postgresql rpmdevtools rpmlint \
    python3-flake8 python3-pylint python3-pytest \
    python3-sphinx python3-sphinxcontrib-httpdomain \
    python3-ldap

# CA Certs
WORKDIR /etc/pki/ca-trust/source/anchors/
RUN for ca_url in ${CA_URLS}; do curl -skO ${ca_url}; done && \
    update-ca-trust

# install build dependencies for WaiverDB
COPY waiverdb.spec /usr/local/src/waiverdb/waiverdb.spec
RUN cd /usr/local/src/waiverdb \
  && dnf -y builddep waiverdb.spec \
  && dnf -y clean all \
  && cd / && rm -rf /usr/local/src/waiverdb

# Setup the user for non-arbitrary UIDs with OpenShift
# https://docs.openshift.org/latest/creating_images/guidelines.html#openshift-origin-specific-guidelines
RUN useradd -d ${HOME_DIR} -u ${UID} -g 0 -m -s /bin/bash ${USER} && \
    chmod -R g+rwx ${HOME_DIR}

# Make /etc/passwd writable for root group
# so we can add dynamic user to the system in entrypoint script
RUN chmod g+rw /etc/passwd

# Retrieve jenkins agent client
RUN curl --create-dirs -sSLo /usr/share/jenkins/agent.jar \
    https://repo.jenkins-ci.org/public/org/jenkins-ci/main/remoting/${REMOTING_VERSION}/remoting-${REMOTING_VERSION}.jar && \
    chmod 755 /usr/share/jenkins && \
    chmod 644 /usr/share/jenkins/agent.jar

# Entry point script to run jenkins agent client
COPY openshift/containers/jenkins-slave/jenkins-agent /usr/local/bin/jenkins-agent
RUN chmod 755 /usr/local/bin/jenkins-agent

# install tini, a tiny but valid init for containers
# install wait-for-it.sh, to allow containers to wait for other services to come up
RUN curl -L -o /usr/local/bin/tini "https://github.com/krallin/tini/releases/download/v${TINI_VERSION}/tini" \
    && chmod +rx /usr/local/bin/tini \
    && curl -L -o /usr/local/bin/wait-for-it "https://raw.githubusercontent.com/vishnubob/wait-for-it/master/wait-for-it.sh" \
    && chmod +rx /usr/local/bin/tini /usr/local/bin/wait-for-it \
    && dnf -y clean all

# For OpenShift we MUST use the UID of the user and not the name.
USER ${UID}
WORKDIR ${HOME_DIR}
ENTRYPOINT ["/usr/local/bin/tini", "--", "jenkins-agent"]
