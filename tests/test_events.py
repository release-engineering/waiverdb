# SPDX-License-Identifier: GPL-2.0+

"""This module contains tests for :mod:`waiverdb.events`."""
from __future__ import unicode_literals
from fedora_messaging import api, testing
from flask_restful import marshal
from waiverdb.models import Waiver
from waiverdb.fields import waiver_fields


def test_publish_new_waiver_with_fedmsg(session):
    waiver = Waiver(
        subject_type='koji_build',
        subject_identifier='glibc-2.26-27.fc27',
        testcase='testcase1',
        username='jcline',
        product_version='something',
        waived=True,
        comment='This is a comment',
    )

    sesh = session()
    sesh.add(waiver)
    sesh.flush()

    expected_msg = api.Message(
        topic='waiverdb.waiver.new',
        body=marshal(waiver, waiver_fields)
    )

    with testing.mock_sends(expected_msg):
        sesh.commit()


def test_publish_new_waiver_with_fedmsg_for_proxy_user(session):
    waiver = Waiver(
        subject_type='koji_build',
        subject_identifier='glibc-2.26-27.fc27',
        testcase='testcase1',
        username='jcline',
        product_version='something',
        waived=True,
        comment='This is a comment',
        proxied_by='bodhi'
    )
    sesh = session()
    sesh.add(waiver)
    sesh.flush()

    expected_msg = api.Message(
        topic='waiverdb.waiver.new',
        body=marshal(waiver, waiver_fields)
    )
    with testing.mock_sends(expected_msg):
        sesh.commit()
