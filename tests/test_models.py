# SPDX-License-Identifier: GPL-2.0+

import pytest

from waiverdb.models.waivers import subject_dict_to_type_identifier


@pytest.mark.parametrize('subject,expected_type,expected_identifier', [
    ({'type': 'bodhi_update', 'item': 'FEDORA-2017-7e594f96bb'},
     'bodhi_update', 'FEDORA-2017-7e594f96bb'),
    ({'type': 'koji_build', 'item': 'glibc-2.26-27.fc27'},
     'koji_build', 'glibc-2.26-27.fc27'),
    # The 'brew-build' type is used internally within Red Hat.
    # We treat it as the 'koji_build' subject type.
    ({'type': 'brew-build', 'item': 'nss-softokn-3.36.1-1.0.el8+5'},
     'koji_build', 'nss-softokn-3.36.1-1.0.el8+5'),
    ({'original_spec_nvr': 'glibc-2.26-27.fc27'},
     'koji_build', 'glibc-2.26-27.fc27'),
    ({'productmd.compose.id': 'Fedora-Rawhide-20170508.n.0'},
     'compose', 'Fedora-Rawhide-20170508.n.0'),
])
def test_subject_dict_to_type_identifier(subject, expected_type, expected_identifier):
    subject_type, subject_identifier = subject_dict_to_type_identifier(subject)
    assert subject_type == expected_type
    assert subject_identifier == expected_identifier
