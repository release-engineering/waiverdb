# SPDX-License-Identifier: GPL-2.0+

import datetime
import json

import pytest
from requests import ConnectionError, HTTPError
from mock import patch, Mock

from .utils import create_waiver
from waiverdb import __version__
from waiverdb.models import Waiver


@patch('waiverdb.auth.get_user', return_value=('foo', {}))
def test_create_waiver(mocked_get_user, client, session):
    data = {
        'subject_type': 'koji_build',
        'subject_identifier': 'glibc-2.26-27.fc27',
        'testcase': 'testcase1',
        'product_version': 'fool-1',
        'waived': True,
        'comment': 'it broke',
    }
    r = client.post('/api/v1.0/waivers/', data=json.dumps(data),
                    content_type='application/json')
    res_data = json.loads(r.get_data(as_text=True))
    assert r.status_code == 201
    assert res_data['username'] == 'foo'
    assert res_data['subject'] == {'type': 'koji_build', 'item': 'glibc-2.26-27.fc27'}
    assert res_data['subject_type'] == 'koji_build'
    assert res_data['subject_identifier'] == 'glibc-2.26-27.fc27'
    assert res_data['testcase'] == 'testcase1'
    assert res_data['product_version'] == 'fool-1'
    assert res_data['waived'] is True
    assert res_data['comment'] == 'it broke'


@patch('waiverdb.auth.get_user', return_value=('foo', {}))
def test_create_waiver_with_subject(mocked_get_user, client, session):
    # 'subject' key was the API in Waiverdb < 0.11
    data = {
        'subject': {'type': 'koji_build', 'item': 'glibc-2.26-27.fc27'},
        'subject_identifier': 'glibc-2.26-27.fc27',
        'testcase': 'dist.rpmdeplint',
        'product_version': 'fedora-27',
        'waived': True,
        'comment': 'it really broke',
    }
    r = client.post('/api/v1.0/waivers/', data=json.dumps(data),
                    content_type='application/json')
    res_data = json.loads(r.get_data(as_text=True))
    assert r.status_code == 201
    assert res_data['username'] == 'foo'
    assert res_data['subject'] == {'type': 'koji_build', 'item': 'glibc-2.26-27.fc27'}
    assert res_data['subject_type'] == 'koji_build'
    assert res_data['subject_identifier'] == 'glibc-2.26-27.fc27'
    assert res_data['testcase'] == 'dist.rpmdeplint'
    assert res_data['product_version'] == 'fedora-27'
    assert res_data['waived'] is True
    assert res_data['comment'] == 'it really broke'


@patch('waiverdb.api_v1.get_resultsdb_result')
@patch('waiverdb.auth.get_user', return_value=('foo', {}))
def test_create_waiver_with_result_id(mocked_get_user, mocked_resultsdb, client, session):
    mocked_resultsdb.return_value = {
        'data': {
            'type': ['koji_build'],
            'item': ['somebuild'],
        },
        'testcase': {'name': 'sometest'}
    }

    # 'result_id' key was the API in Waiverdb < 0.6
    data = {
        'result_id': 123,
        'product_version': 'fool-1',
        'waived': True,
        'comment': 'it broke',
    }
    r = client.post('/api/v1.0/waivers/', data=json.dumps(data),
                    content_type='application/json')
    res_data = json.loads(r.get_data(as_text=True))
    assert r.status_code == 201
    assert res_data['username'] == 'foo'
    assert res_data['subject'] == {'type': 'koji_build', 'item': 'somebuild'}
    assert res_data['subject_type'] == 'koji_build'
    assert res_data['subject_identifier'] == 'somebuild'
    assert res_data['testcase'] == 'sometest'
    assert res_data['product_version'] == 'fool-1'
    assert res_data['waived'] is True
    assert res_data['comment'] == 'it broke'


@patch('waiverdb.api_v1.get_resultsdb_result')
@patch('waiverdb.auth.get_user', return_value=('foo', {}))
def test_create_waiver_with_result_for_original_spec_nvr(
        mocked_get_user, mocked_resultsdb, client, session):
    mocked_resultsdb.return_value = {
        'data': {
            'original_spec_nvr': ['somedata'],
        },
        'testcase': {'name': 'sometest'}
    }

    data = {
        'result_id': 123,
        'product_version': 'fool-1',
        'waived': True,
        'comment': 'it broke',
    }
    r = client.post('/api/v1.0/waivers/', data=json.dumps(data),
                    content_type='application/json')
    res_data = json.loads(r.get_data(as_text=True))
    assert r.status_code == 201
    assert res_data['username'] == 'foo'
    assert res_data['subject'] == {'type': 'koji_build', 'item': 'somedata'}
    assert res_data['subject_type'] == 'koji_build'
    assert res_data['subject_identifier'] == 'somedata'
    assert res_data['testcase'] == 'sometest'
    assert res_data['product_version'] == 'fool-1'
    assert res_data['waived'] is True
    assert res_data['comment'] == 'it broke'


@patch('waiverdb.auth.get_user', return_value=('foo', {}))
def test_create_waiver_without_comment(mocked_get_user, client, session):
    data = {
        'subject_type': 'koji_build',
        'subject_identifier': 'glibc-2.26-27.fc27',
        'product_version': 'fool-1',
        'waived': True,
    }
    r = client.post('/api/v1.0/waivers/', data=json.dumps(data),
                    content_type='application/json')
    res_data = json.loads(r.get_data(as_text=True))
    assert r.status_code == 400
    res_data = json.loads(r.get_data(as_text=True))
    assert res_data['message']['comment'] == 'Missing required parameter in the JSON body'


@patch('waiverdb.api_v1.get_resultsdb_result', side_effect=HTTPError(response=Mock(status=404)))
@patch('waiverdb.auth.get_user', return_value=('foo', {}))
def test_create_waiver_with_unknown_result_id(mocked_get_user, mocked_resultsdb, client, session):
    data = {
        'result_id': 123,
        'product_version': 'fool-1',
        'waived': True,
        'comment': 'it broke',
    }
    mocked_resultsdb.return_value.status_code = 404
    r = client.post('/api/v1.0/waivers/', data=json.dumps(data),
                    content_type='application/json')
    res_data = json.loads(r.get_data(as_text=True))
    assert res_data['message'].startswith('Failed looking up result in Resultsdb:')


@patch('waiverdb.auth.get_user', return_value=('foo', {}))
def test_create_waiver_with_no_testcase(mocked_get_user, client):
    data = {
        'subject_type': 'koji_build',
        'subject_identifier': 'glibc-2.26-27.fc27',
        'waived': True,
        'product_version': 'the-best',
        'comment': 'it broke',
    }
    r = client.post('/api/v1.0/waivers/', data=json.dumps(data),
                    content_type='application/json')
    res_data = json.loads(r.get_data(as_text=True))
    assert r.status_code == 400
    assert 'Missing required parameter in the JSON body' in res_data['message']['testcase']


@patch('waiverdb.auth.get_user', return_value=('foo', {}))
def test_create_waiver_with_malformed_subject(mocked_get_user, client):
    data = {
        'subject': 'asd',
        'testcase': 'qqq',
    }
    r = client.post('/api/v1.0/waivers/', data=json.dumps(data),
                    content_type='application/json')
    res_data = json.loads(r.get_data(as_text=True))
    assert r.status_code == 400
    assert 'Must be a valid dict' in res_data['message']['subject']


@patch('waiverdb.auth.get_user', return_value=('foo', {}))
def test_non_superuser_cannot_create_waiver_for_other_users(mocked_get_user, client):
    data = {
        'subject_type': 'koji_build',
        'subject_identifier': 'glibc-2.26-27.fc27',
        'testcase': 'testcase1',
        'product_version': 'fool-1',
        'waived': True,
        'comment': 'it broke',
        'username': 'bar',
    }
    r = client.post('/api/v1.0/waivers/', data=json.dumps(data),
                    content_type='application/json')
    res_data = json.loads(r.get_data(as_text=True))
    assert r.status_code == 403
    assert 'user foo does not have the proxyuser ability' == res_data['message']


@patch('waiverdb.auth.get_user', return_value=('bodhi', {}))
def test_superuser_can_create_waiver_for_other_users(mocked_get_user, client, session):
    data = {
        'subject_type': 'koji_build',
        'subject_identifier': 'glibc-2.26-27.fc27',
        'testcase': 'testcase1',
        'product_version': 'fool-1',
        'waived': True,
        'comment': 'it broke',
        'username': 'bar',
    }
    r = client.post('/api/v1.0/waivers/', data=json.dumps(data),
                    content_type='application/json')
    res_data = json.loads(r.get_data(as_text=True))
    assert r.status_code == 201
    # a waiver should be created for bar by bodhi
    assert res_data['username'] == 'bar'
    assert res_data['proxied_by'] == 'bodhi'


def test_get_waiver(client, session):
    # create a new waiver
    waiver = create_waiver(session, subject_type='koji_build',
                           subject_identifier='glibc-2.26-27.fc27',
                           testcase='testcase1', username='foo',
                           product_version='foo-1', comment='bla bla bla')
    r = client.get('/api/v1.0/waivers/%s' % waiver.id)
    res_data = json.loads(r.get_data(as_text=True))
    assert r.status_code == 200
    assert res_data['username'] == waiver.username
    assert res_data['subject'] == {'type': 'koji_build', 'item': 'glibc-2.26-27.fc27'}
    assert res_data['subject_type'] == waiver.subject_type
    assert res_data['subject_identifier'] == waiver.subject_identifier
    assert res_data['testcase'] == waiver.testcase
    assert res_data['product_version'] == waiver.product_version
    assert res_data['waived'] is True
    assert res_data['comment'] == waiver.comment


def test_404_for_nonexistent_waiver(client, session):
    r = client.get('/api/v1.0/waivers/foo')
    assert r.status_code == 404
    res_data = json.loads(r.get_data(as_text=True))
    message = (
        'The requested URL was not found on the server.  If you entered the '
        'URL manually please check your spelling and try again.')
    assert res_data['message'] == message


@patch('waiverdb.api_v1.AboutResource.get', side_effect=ConnectionError)
def test_500(mocked, client, session):
    r = client.get('/api/v1.0/about')
    assert r.status_code == 500
    res_data = json.loads(r.get_data(as_text=True))
    assert res_data['message'] == ''


def test_get_waivers(client, session):
    for i in range(0, 10):
        create_waiver(session, subject_type='koji_build', subject_identifier="%d" % i,
                      testcase="case %d" % i, username='foo %d' % i,
                      product_version='foo-%d' % i, comment='bla bla bla')
    r = client.get('/api/v1.0/waivers/')
    res_data = json.loads(r.get_data(as_text=True))
    assert r.status_code == 200
    assert len(res_data['data']) == 10


def test_pagination_waivers(client, session):
    for i in range(0, 30):
        create_waiver(session, subject_type='koji_build', subject_identifier="%d" % i,
                      testcase="case %d" % i, username='foo %d' % i,
                      product_version='foo-%d' % i, comment='bla bla bla')
    r = client.get('/api/v1.0/waivers/?page=2')
    res_data = json.loads(r.get_data(as_text=True))
    assert r.status_code == 200
    assert len(res_data['data']) == 10
    assert '/waivers/?page=1' in res_data['prev']
    assert '/waivers/?page=3' in res_data['next']
    assert '/waivers/?page=1' in res_data['first']
    assert '/waivers/?page=3' in res_data['last']


def test_obsolete_waivers_are_excluded_by_default(client, session):
    create_waiver(session, subject_type='koji_build',
                  subject_identifier='glibc-2.26-27.fc27',
                  testcase='testcase1', username='foo',
                  product_version='foo-1')
    new_waiver = create_waiver(session, subject_type='koji_build',
                               subject_identifier='glibc-2.26-27.fc27',
                               testcase='testcase1', username='foo',
                               product_version='foo-1', waived=False)
    r = client.get('/api/v1.0/waivers/')
    res_data = json.loads(r.get_data(as_text=True))
    assert r.status_code == 200
    assert len(res_data['data']) == 1
    assert res_data['data'][0]['id'] == new_waiver.id
    assert res_data['data'][0]['waived'] == new_waiver.waived


def test_get_obsolete_waivers(client, session):
    old_waiver = create_waiver(session, subject_type='koji_build',
                               subject_identifier='glibc-2.26-27.fc27',
                               testcase='testcase1', username='foo',
                               product_version='foo-1')
    new_waiver = create_waiver(session, subject_type='koji_build',
                               subject_identifier='glibc-2.26-27.fc27',
                               testcase='testcase1', username='foo',
                               product_version='foo-1', waived=False)
    r = client.get('/api/v1.0/waivers/?include_obsolete=1')
    res_data = json.loads(r.get_data(as_text=True))
    assert r.status_code == 200
    assert len(res_data['data']) == 2
    assert res_data['data'][0]['id'] == new_waiver.id
    assert res_data['data'][1]['id'] == old_waiver.id


def test_obsolete_waivers_with_different_product_version(client, session):
    old_waiver = create_waiver(session, subject_type='koji_build',
                               subject_identifier='glibc-2.26-27.fc27',
                               testcase='testcase1', username='foo',
                               product_version='foo-1')
    new_waiver = create_waiver(session, subject_type='koji_build',
                               subject_identifier='glibc-2.26-27.fc27',
                               testcase='testcase1', username='foo',
                               product_version='foo-2')
    r = client.get('/api/v1.0/waivers/?include_obsolete=0')
    res_data = json.loads(r.get_data(as_text=True))
    assert r.status_code == 200
    assert len(res_data['data']) == 2
    assert res_data['data'][0]['id'] == new_waiver.id
    assert res_data['data'][1]['id'] == old_waiver.id


def test_obsolete_waivers_with_different_username(client, session):
    old_waiver = create_waiver(session, subject_type='koji_build',
                               subject_identifier='glibc-2.26-27.fc27',
                               testcase='testcase1', username='foo',
                               product_version='foo-1')
    new_waiver = create_waiver(session, subject_type='koji_build',
                               subject_identifier='glibc-2.26-27.fc27',
                               testcase='testcase1', username='bar',
                               product_version='foo-1')
    r = client.get('/api/v1.0/waivers/?include_obsolete=0')
    res_data = json.loads(r.get_data(as_text=True))
    assert r.status_code == 200
    assert len(res_data['data']) == 2
    assert res_data['data'][0]['id'] == new_waiver.id
    assert res_data['data'][1]['id'] == old_waiver.id


def test_filtering_waivers_by_subject_type(client, session):
    create_waiver(session, subject_type='koji_build', subject_identifier='glibc-2.26-27.fc27',
                  testcase='testcase', username='foo-1', product_version='foo-1')
    create_waiver(session, subject_type='bodhi_update', subject_identifier='FEDORA-2017-7e594f96bb',
                  testcase='testcase', username='foo-2', product_version='foo-1')

    r = client.get('/api/v1.0/waivers/?subject_type=bodhi_update')
    res_data = json.loads(r.get_data(as_text=True))
    assert r.status_code == 200
    assert len(res_data['data']) == 1
    assert res_data['data'][0]['subject_type'] == 'bodhi_update'


def test_filtering_waivers_by_subject_identifier(client, session):
    create_waiver(session, subject_type='koji_build', subject_identifier='glibc-2.26-27.fc27',
                  testcase='testcase', username='foo-1', product_version='foo-1')
    create_waiver(session, subject_type='koji_build', subject_identifier='kernel-4.15.17-300.fc27',
                  testcase='testcase', username='foo-2', product_version='foo-1')

    r = client.get('/api/v1.0/waivers/?subject_identifier=glibc-2.26-27.fc27')
    res_data = json.loads(r.get_data(as_text=True))
    assert r.status_code == 200
    assert len(res_data['data']) == 1
    assert res_data['data'][0]['subject_identifier'] == 'glibc-2.26-27.fc27'


def test_filtering_waivers_by_testcase(client, session):
    create_waiver(session, subject_type='koji_build', subject_identifier='glibc-2.26-27.fc27',
                  testcase='testcase1', username='foo-1', product_version='foo-1')
    create_waiver(session, subject_type='koji_build', subject_identifier='glibc-2.26-27.fc27',
                  testcase='testcase2', username='foo-2', product_version='foo-1')

    r = client.get('/api/v1.0/waivers/?testcase=testcase1')
    res_data = json.loads(r.get_data(as_text=True))
    assert r.status_code == 200
    assert len(res_data['data']) == 1
    assert res_data['data'][0]['testcase'] == 'testcase1'


def test_filtering_waivers_by_product_version(client, session):
    create_waiver(session, subject_type='koji_build', subject_identifier='glibc-2.26-27.fc27',
                  testcase='testcase1', username='foo-1', product_version='release-1')
    create_waiver(session, subject_type='koji_build', subject_identifier='kernel-4.15.17-300.fc27',
                  testcase='testcase2', username='foo-1', product_version='release-2')
    r = client.get('/api/v1.0/waivers/?product_version=release-1')
    res_data = json.loads(r.get_data(as_text=True))
    assert r.status_code == 200
    assert len(res_data['data']) == 1
    assert res_data['data'][0]['product_version'] == 'release-1'


def test_filtering_waivers_by_username(client, session):
    create_waiver(session, subject_type='koji_build', subject_identifier='glibc-2.26-27.fc27',
                  testcase='testcase1', username='foo', product_version='foo-1')
    create_waiver(session, subject_type='koji_build', subject_identifier='kernel-4.15.17-300.fc27',
                  testcase='testcase2', username='bar', product_version='foo-2')
    r = client.get('/api/v1.0/waivers/?username=foo')
    res_data = json.loads(r.get_data(as_text=True))
    assert r.status_code == 200
    assert len(res_data['data']) == 1
    assert res_data['data'][0]['username'] == 'foo'


def test_filtering_waivers_by_since(client, session):
    before1 = (datetime.datetime.utcnow() - datetime.timedelta(seconds=100)).isoformat()
    before2 = (datetime.datetime.utcnow() - datetime.timedelta(seconds=99)).isoformat()
    after = (datetime.datetime.utcnow() + datetime.timedelta(seconds=100)).isoformat()
    create_waiver(session, subject_type='koji_build', subject_identifier='glibc-2.26-27.fc27',
                  testcase='testcase1', username='foo', product_version='foo-1')
    r = client.get('/api/v1.0/waivers/?since=%s' % before1)
    res_data = json.loads(r.get_data(as_text=True))
    assert r.status_code == 200
    assert len(res_data['data']) == 1
    assert res_data['data'][0]['subject_identifier'] == 'glibc-2.26-27.fc27'
    assert res_data['data'][0]['testcase'] == 'testcase1'

    r = client.get('/api/v1.0/waivers/?since=%s,%s' % (before1, after))
    res_data = json.loads(r.get_data(as_text=True))
    assert r.status_code == 200
    assert len(res_data['data']) == 1
    assert res_data['data'][0]['subject_identifier'] == 'glibc-2.26-27.fc27'
    assert res_data['data'][0]['testcase'] == 'testcase1'

    r = client.get('/api/v1.0/waivers/?since=%s' % (after))
    res_data = json.loads(r.get_data(as_text=True))
    assert r.status_code == 200
    assert len(res_data['data']) == 0

    r = client.get('/api/v1.0/waivers/?since=%s,%s' % (before1, before2))
    res_data = json.loads(r.get_data(as_text=True))
    assert r.status_code == 200
    assert len(res_data['data']) == 0


def test_filtering_waivers_by_malformed_since(client, session):
    r = client.get('/api/v1.0/waivers/?since=123')
    res_data = json.loads(r.get_data(as_text=True))
    assert r.status_code == 400
    assert res_data['message']['since'] == \
        "time data '123' does not match format '%Y-%m-%dT%H:%M:%S.%f'"

    r = client.get('/api/v1.0/waivers/?since=%s,badend' % datetime.datetime.utcnow().isoformat())
    res_data = json.loads(r.get_data(as_text=True))
    assert r.status_code == 400
    assert res_data['message']['since'] == \
        "time data 'badend' does not match format '%Y-%m-%dT%H:%M:%S.%f'"

    r = client.get('/api/v1.0/waivers/?since=%s,too,many,commas'
                   % datetime.datetime.utcnow().isoformat())
    res_data = json.loads(r.get_data(as_text=True))
    assert r.status_code == 400
    assert res_data['message']['since'] == \
        "time data 'too,many,commas' does not match format '%Y-%m-%dT%H:%M:%S.%f'"


def test_filtering_waivers_by_proxied_by(client, session):
    create_waiver(session, subject_type='koji_build', subject_identifier='glibc-2.26-27.fc27',
                  testcase='testcase1', username='foo-1', product_version='foo-1',
                  proxied_by='bodhi')
    create_waiver(session, subject_type='koji_build', subject_identifier='kernel-4.15.17-300.fc27',
                  testcase='testcase2', username='foo-2', product_version='foo-1')
    r = client.get('/api/v1.0/waivers/?proxied_by=bodhi')
    res_data = json.loads(r.get_data(as_text=True))
    assert r.status_code == 200
    assert len(res_data['data']) == 1
    assert res_data['data'][0]['subject'] == {'type': 'koji_build', 'item': 'glibc-2.26-27.fc27'}
    assert res_data['data'][0]['testcase'] == 'testcase1'


def test_jsonp(client, session):
    waiver = create_waiver(session, subject_type='koji_build',
                           subject_identifier='glibc-2.26-27.fc27',
                           testcase='testcase1', username='foo', product_version='foo-1')
    r = client.get('/api/v1.0/waivers/%s?callback=jsonpcallback' % waiver.id)
    assert r.mimetype == 'application/javascript'
    assert 'jsonpcallback' in r.get_data(as_text=True)


def test_healthcheck(client):
    r = client.get('healthcheck')
    assert r.status_code == 200
    assert r.get_data(as_text=True) == 'Health check OK'


def test_filtering_waivers_with_post(client, session):
    filters = []
    for i in range(1, 51):
        filters.append({'subject_type': 'koji_build',
                        'subject_identifier': 'python2-2.7.14-%d.fc27' % i,
                        'testcase': 'case %d' % i})
        create_waiver(session, subject_type='koji_build',
                      subject_identifier='python2-2.7.14-%d.fc27' % i,
                      testcase='case %d' % i, username='person',
                      product_version='fedora-27', comment='bla bla bla')
    # Unrelated waiver which should not be included
    create_waiver(session, subject_type='koji_build',
                  subject_identifier='glibc-2.26-27.fc27',
                  testcase='dist.rpmdeplint', username='person',
                  product_version='fedora-27', comment='bla bla bla')
    r = client.post('/api/v1.0/waivers/+filtered',
                    data=json.dumps({'filters': filters}),
                    content_type='application/json')
    res_data = json.loads(r.get_data(as_text=True))
    assert r.status_code == 200
    assert len(res_data['data']) == 50
    assert all(w['subject_identifier'].startswith('python2-2.7.14') for w in res_data['data'])


def test_filtering_with_missing_filter(client, session):
    r = client.post('/api/v1.0/waivers/+filtered',
                    data=json.dumps({'somethingelse': 'what'}),
                    content_type='application/json')
    res_data = json.loads(r.get_data(as_text=True))
    assert r.status_code == 400
    assert res_data['message']['filters'] == 'Missing required parameter in the JSON body'


def test_waivers_by_subjects_and_testcases(client, session):
    """
    This tests that users can get waivers by sending a POST request with a long
    list of result subject/testcase.
    """
    results = []
    for i in range(1, 51):
        results.append({'subject': {'type': 'koji_build', 'item': '%d' % i},
                        'testcase': 'case %d' % i})
        create_waiver(session, subject_type='koji_build', subject_identifier="%d" % i,
                      testcase="case %d" % i, username='foo %d' % i,
                      product_version='foo-%d' % i, comment='bla bla bla')
    data = {
        'results': results
    }
    r = client.post('/api/v1.0/waivers/+by-subjects-and-testcases', data=json.dumps(data),
                    content_type='application/json')
    res_data = json.loads(r.get_data(as_text=True))
    assert r.status_code == 200
    assert len(res_data['data']) == 50
    subject_identifiers = []
    testcases = []
    for i in reversed(range(1, 51)):
        subject_identifiers.append('%d' % i)
        testcases.append('case %d' % i)
    assert [w['subject_identifier'] for w in res_data['data']] == subject_identifiers
    assert set([w['testcase'] for w in res_data['data']]) == set(testcases)
    assert all(w['username'].startswith('foo') for w in res_data['data'])
    assert all(w['product_version'].startswith('foo-') for w in res_data['data'])


@pytest.mark.parametrize("results", [
    [{'item': {'subject.test1': 'subject1'}}],  # Unexpected key
    [{'subject': 'subject1'}],  # Unexpected key type
])
def test_waivers_by_subjects_and_testcases_with_bad_results_parameter(client, session, results):
    data = {'results': results}
    r = client.post('/api/v1.0/waivers/+by-subjects-and-testcases', data=json.dumps(data),
                    content_type='application/json')
    res_data = json.loads(r.get_data(as_text=True))
    assert r.status_code == 400
    assert res_data['message']['results'] == \
        'Must be a list of dictionaries with "subject" and "testcase"'


def test_waivers_by_subjects_and_testcases_with_unrecognized_subject_type(client, session):
    create_waiver(session, subject_type='koji_build',
                  subject_identifier='python3-flask-0.12.2-1.fc29',
                  testcase='dist.rpmdeplint', username='person',
                  product_version='fedora-29', comment='bla bla bla')
    # This doesn't match any of the known subject types which we understand
    # for backwards compatibility. So if you tried to submit a waiver with a
    # subject like this, Waiverdb would reject it. But if the caller is just
    # *searching* and not *submitting* then instead of giving back an error
    # Waiverdb should just return an empty result set.
    data = {'results': [
        {'subject': {'item': 'python3-flask-0.12.2-1.fc29'}, 'testcase': 'dist.rpmdeplint'},
    ]}
    r = client.post('/api/v1.0/waivers/+by-subjects-and-testcases', data=json.dumps(data),
                    content_type='application/json')
    res_data = json.loads(r.get_data(as_text=True))
    assert r.status_code == 200
    assert res_data['data'] == []


@pytest.mark.parametrize("results", [
    [],
    [{}],
])
def test_waivers_by_subjects_and_testcases_with_empty_results_parameter(client, session, results):
    create_waiver(session, subject_type='koji_build', subject_identifier='glibc-2.26-27.fc27',
                  testcase='testcase1', username='foo-1', product_version='foo-1')
    data = {'results': results}
    r = client.post('/api/v1.0/waivers/+by-subjects-and-testcases', data=json.dumps(data),
                    content_type='application/json')
    res_data = json.loads(r.get_data(as_text=True))
    assert r.status_code == 200
    assert len(res_data['data']) == 1


def test_waivers_by_subjects_and_testcases_with_malformed_since(client, session):
    data = {'since': 123}
    r = client.post('/api/v1.0/waivers/+by-subjects-and-testcases', data=json.dumps(data),
                    content_type='application/json')
    res_data = json.loads(r.get_data(as_text=True))
    assert r.status_code == 400
    assert res_data['message']['since'] == "argument of type 'int' is not iterable"

    data = {'since': 'asdf'}
    r = client.post('/api/v1.0/waivers/+by-subjects-and-testcases', data=json.dumps(data),
                    content_type='application/json')
    res_data = json.loads(r.get_data(as_text=True))
    assert r.status_code == 400
    assert res_data['message']['since'] == \
        "time data 'asdf' does not match format '%Y-%m-%dT%H:%M:%S.%f'"


@pytest.mark.parametrize('trailing_slash', ('', '/'))
def test_about_endpoint(client, trailing_slash):
    r = client.get('/api/v1.0/about' + trailing_slash)
    assert r.status_code == 200

    output = json.loads(r.get_data(as_text=True))
    assert output['version'] == __version__
    assert output['auth_method'] == client.application.config['AUTH_METHOD']


@pytest.mark.usefixtures('enable_cors')
def test_cors_about(client, session):
    r = client.get('/api/v1.0/about')

    assert 'Access-Control-Allow-Origin' in list(r.headers.keys())
    assert 'Access-Control-Allow-Headers' in list(r.headers.keys())
    assert 'Access-Control-Allow-Method' in list(r.headers.keys())
    assert r.headers['Access-Control-Allow-Origin'] == 'https://bodhi.fedoraproject.org'
    assert r.headers['Access-Control-Allow-Headers'] == 'Content-Type'
    assert r.headers['Access-Control-Allow-Method'] == 'POST, OPTIONS'

    output = json.loads(r.get_data(as_text=True))
    assert r.status_code == 200
    assert output['version'] == __version__


def test_no_cors_about(client, session):
    r = client.get('/api/v1.0/about')

    assert 'Access-Control-Allow-Origin' not in list(r.headers.keys())
    assert 'Access-Control-Allow-Headers' not in list(r.headers.keys())
    assert 'Access-Control-Allow-Method' not in list(r.headers.keys())

    output = json.loads(r.get_data(as_text=True))
    assert r.status_code == 200
    assert output['version'] == __version__


@pytest.mark.usefixtures('enable_cors')
def test_cors_waivers(client, session):
    for i in range(0, 3):
        create_waiver(session, subject_type='koji_build', subject_identifier="%d" % i,
                      testcase="case %d" % i, username='foo %d' % i,
                      product_version='foo-%d' % i, comment='bla bla bla')
    r = client.get('/api/v1.0/waivers/')

    assert 'Access-Control-Allow-Origin' in list(r.headers.keys())
    assert 'Access-Control-Allow-Headers' in list(r.headers.keys())
    assert 'Access-Control-Allow-Method' in list(r.headers.keys())
    assert r.headers['Access-Control-Allow-Origin'] == 'https://bodhi.fedoraproject.org'
    assert r.headers['Access-Control-Allow-Headers'] == 'Content-Type'
    assert r.headers['Access-Control-Allow-Method'] == 'POST, OPTIONS'

    res_data = json.loads(r.get_data(as_text=True))
    assert r.status_code == 200
    assert len(res_data['data']) == 3


def test_no_cors_waivers(client, session):
    for i in range(0, 3):
        create_waiver(session, subject_type='koji_build', subject_identifier="%d" % i,
                      testcase="case %d" % i, username='foo %d' % i,
                      product_version='foo-%d' % i, comment='bla bla bla')
    r = client.get('/api/v1.0/waivers/')

    assert 'Access-Control-Allow-Origin' not in list(r.headers.keys())
    assert 'Access-Control-Allow-Headers' not in list(r.headers.keys())
    assert 'Access-Control-Allow-Method' not in list(r.headers.keys())

    res_data = json.loads(r.get_data(as_text=True))
    assert r.status_code == 200
    assert len(res_data['data']) == 3


@patch('waiverdb.auth.get_user', return_value=('foo', {}))
def test_create_multiple_waivers(mocked_get_user, client, session):
    item1 = {
        'subject_type': 'koji_build',
        'subject_identifier': 'glibc-2.26-27.fc27',
        'testcase': 'testcase1',
        'product_version': 'fool-1',
        'waived': True,
        'comment': 'it broke',
    }
    item2 = {
        'subject_type': 'koji_build',
        'subject_identifier': 'kernel-4.15.17-300.fc27',
        'testcase': 'testcase2',
        'product_version': 'fool-2',
        'waived': False,
        'comment': 'fixed',
    }
    data = [item1, item2]

    r = client.post('/api/v1.0/waivers/', data=json.dumps(data),
                    content_type='application/json')

    res_data = json.loads(r.get_data(as_text=True))
    assert r.status_code == 201
    assert isinstance(res_data, list)
    assert len(res_data) == 2

    actual_item1 = {k: v for k, v in res_data[0].items() if k in item1}
    actual_item2 = {k: v for k, v in res_data[1].items() if k in item2}
    assert actual_item1 == item1
    assert actual_item2 == item2

    # Transaction was not rolled back.
    assert session.query(Waiver).count() == 2


@patch('waiverdb.auth.get_user', return_value=('foo', {}))
def test_create_multiple_waivers_rollback_on_error(mocked_get_user, client, session):
    item1 = {
        'subject_type': 'koji_build',
        'subject_identifier': 'glibc-2.26-27.fc27',
        'testcase': 'testcase1',
        'product_version': 'fool-1',
        'waived': True,
        'comment': 'it broke',
    }
    item2 = {}
    data = [item1, item2]

    r = client.post('/api/v1.0/waivers/', data=json.dumps(data),
                    content_type='application/json')

    assert r.status_code == 400

    # Transaction was rolled back.
    assert session.query(Waiver).count() == 0


@patch('waiverdb.auth.get_user', return_value=('foo', {}))
def test_create_waiver_with_arbitrary_subject_type(mocked_get_user, client, session):
    data = {
        'subject_type': 'kind-of-magic',
        'subject_identifier': 'glibc-2.26-27.fc27',
        'testcase': 'testcase1',
        'product_version': 'fool-1',
        'waived': True,
        'comment': 'it broke',
    }
    r = client.post('/api/v1.0/waivers/', data=json.dumps(data),
                    content_type='application/json')
    res_data = json.loads(r.get_data(as_text=True))
    assert r.status_code == 201
    assert res_data['username'] == 'foo'
    assert res_data['subject'] == {'type': 'kind-of-magic', 'item': 'glibc-2.26-27.fc27'}
    assert res_data['subject_type'] == 'kind-of-magic'
    assert res_data['subject_identifier'] == 'glibc-2.26-27.fc27'
    assert res_data['testcase'] == 'testcase1'
    assert res_data['product_version'] == 'fool-1'
    assert res_data['waived'] is True
    assert res_data['comment'] == 'it broke'
