#!/bin/bash
set -e
# SPDX-License-Identifier: GPL-2.0+

# Generate a version number from the current code base.

name=waiverdb
if [ "$(git tag | wc -l)" -eq 0 ] ; then
    # if this is a shallow git clone, get the latest version from spec file
    lastversion="$(sed -n '/^Version:/{s/.*:\s*//;p;q}' waiverdb.spec)"
    revbase=""
    commitcount=99
else
    lasttag="$(git describe --tags --abbrev=0 HEAD)"
    lastversion="${lasttag##${name}-}"
    revbase="^$lasttag"
    commitcount=$(git rev-list "$revbase" HEAD | wc -l)
fi

if [ "$(git rev-list "$revbase" HEAD | wc -l)" -eq 0 ] ; then
    # building a tag
    rpmver=""
    rpmrel=""
    version="$lastversion"
else
    # git builds count as a pre-release of the next version
    version="$lastversion"
    version="${version%%[a-z]*}" # strip non-numeric suffixes like "rc1"
    # increment the last portion of the version
    version="${version%.*}.$((${version##*.} + 1))"
    commitsha=$(git rev-parse --short HEAD)
    rpmver="${version}"
    rpmrel="0.git.${commitcount}.${commitsha}"
    version="${version}.dev${commitcount}+git.${commitsha}"
fi

export WAIVERDB_VERSION=$version
export WAIVERDB_RPM_VERSION=$rpmver
export WAIVERDB_RPM_RELEASE=$rpmrel
export WAIVERDB_CONTAINER_VERSION=${version/+/-}
