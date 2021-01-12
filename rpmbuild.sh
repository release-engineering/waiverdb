#!/bin/bash

# SPDX-License-Identifier: GPL-2.0+

# Builds a development (S)RPM from the current git revision.

set -e

if [ $# -eq 0 ] ; then
    echo "Usage: $1 -bs|-bb <rpmbuild-options...>" >&2
    echo "Hint: -bs builds SRPM, -bb builds RPM, refer to rpmbuild(8)" >&2
    exit 1
fi

SELF=$(readlink -f -- "$0")
HERE=$(dirname -- "$SELF")

source "$HERE"/version.sh

name=waiverdb
workdir="$(mktemp -d)"
trap "rm -rf $workdir" EXIT
outdir="$(readlink -f ./rpmbuild-output)"
mkdir -p "$outdir"

git archive --format=tar HEAD | tar -C "$workdir" -xf -
if [ -n "$WAIVERDB_RPM_RELEASE" ] ; then
    # need to hack the version in the spec
    sed --regexp-extended --in-place \
        -e "/^Version:/cVersion: ${WAIVERDB_RPM_VERSION}" \
        -e "/^Release:/cRelease: ${WAIVERDB_RPM_RELEASE}%{?dist}" \
        -e "/^Source0:/cSource0: waiverdb-${WAIVERDB_RPM_VERSION}.${WAIVERDB_RPM_RELEASE}.tar.gz" \
        "$workdir/${name}.spec"
    # also hack the Python module version
    sed --regexp-extended --in-place \
        -e "/^__version__ = /c\\__version__ = '$WAIVERDB_VERSION'" \
        "$workdir/waiverdb/__init__.py"
fi
( cd "$workdir" && python3 setup.py sdist )
mv "$workdir"/dist/*.tar.gz "$workdir"

rpmbuild \
    --define "_topdir $workdir" \
    --define "_sourcedir $workdir" \
    --define "_specdir $workdir" \
    --define "_rpmdir $outdir" \
    --define "_srcrpmdir $outdir" \
    "$@" "$workdir/${name}.spec"
