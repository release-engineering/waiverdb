# SPDX-License-Identifier: GPL-2.0+

import datetime
import re
import logging

import requests
from flask import Blueprint, request, current_app
from flask_restful import Resource, Api, reqparse, marshal_with, marshal
from werkzeug.exceptions import (BadRequest, Forbidden, ServiceUnavailable,
                                 InternalServerError, Unauthorized, BadGateway)
from sqlalchemy.sql.expression import func, and_, or_

from waiverdb import __version__
from waiverdb.models import db
from waiverdb.models.waivers import Waiver, subject_dict_to_type_identifier
from waiverdb.utils import json_collection, jsonp
from waiverdb.fields import waiver_fields
import waiverdb.auth

api_v1 = (Blueprint('api_v1', __name__))
api = Api(api_v1)
requests_session = requests.Session()
log = logging.getLogger(__name__)


def valid_dict(value):
    if not isinstance(value, dict):
        raise ValueError("Must be a valid dict, not %r" % value)
    return value


def get_resultsdb_result(result_id):
    response = requests_session.request('GET', '{0}/results/{1}'.format(
        current_app.config['RESULTSDB_API_URL'], result_id),
        headers={'Content-Type': 'application/json'},
        timeout=60)
    response.raise_for_status()
    return response.json()


def valid_results_list(results):
    expected = {
        'subject': dict,
        'testcase': str,
    }
    for item in results:
        for k, v in item.items():
            if not (k in expected and isinstance(v, expected[k])):
                raise ValueError('Must be a list of dictionaries with "subject" and "testcase"')
    return results


def valid_filter_list(filters):
    if not filters:
        raise ValueError('Must be a list of non-empty dictionaries')
    for item in filters:
        if not isinstance(item, dict) or not item:
            raise ValueError('Must be a list of non-empty dictionaries')
    return filters


def reqparse_since(since):
    """
    Parses the 'since' query parameter, which is expected to be either a
    single ISO8601 timestamp representing the start of a time period::

        2017-02-13T23:37:58.193281

    or a comma-separated pair of timestamps representing the start and end of
    a range::

        2017-02-13T23:37:58.193281,2017-02-16T23:37:58.193281

    Returns a tuple (start, end) of datetime.datetime instances.
    """
    start = None
    end = None
    if ',' in since:
        start, end = since.split(',', 1)
    else:
        start = since
    if start:
        start = datetime.datetime.strptime(start, "%Y-%m-%dT%H:%M:%S.%f")
    if end:
        end = datetime.datetime.strptime(end, "%Y-%m-%dT%H:%M:%S.%f")
    return start, end


def _filter_out_obsolete_waivers(query):
    """
    Filters out obsolete waivers.

    A waiver is obsolete if there exist another one that is more recent with
    same subject, test case name, username and product_version.
    """
    subquery = db.session.query(func.max(Waiver.id)).group_by(
        Waiver.subject_type,
        Waiver.subject_identifier,
        Waiver.testcase,
        Waiver.username,
        Waiver.product_version,
    )
    return query.filter(Waiver.id.in_(subquery))


# RP contains request parsers (reqparse.RequestParser).
#    Parsers are added in each 'resource section' for better readability
RP = {}
RP['create_waiver'] = reqparse.RequestParser()
RP['create_waiver'].add_argument('subject_type', type=str, location='json')
RP['create_waiver'].add_argument('subject_identifier', type=str, location='json')
RP['create_waiver'].add_argument('testcase', type=str, location='json')
# These are accepted for backwards compatibility
RP['create_waiver'].add_argument('subject', type=valid_dict, location='json')
RP['create_waiver'].add_argument('result_id', type=int, location='json')
RP['create_waiver'].add_argument('waived', type=bool, required=True, location='json')
RP['create_waiver'].add_argument('product_version', type=str, required=True, location='json')
RP['create_waiver'].add_argument('comment', type=str, required=True, location='json')
RP['create_waiver'].add_argument('username', type=str, default=None, location='json')

RP['get_waivers'] = reqparse.RequestParser()
RP['get_waivers'].add_argument('subject_type', location='args')
RP['get_waivers'].add_argument('subject_identifier', location='args')
RP['get_waivers'].add_argument('testcase', location='args')
RP['get_waivers'].add_argument('product_version', location='args')
RP['get_waivers'].add_argument('username', location='args')
RP['get_waivers'].add_argument('include_obsolete', type=bool, default=False, location='args')
# XXX This matches the since query parameter in resultsdb but I think it would
# be good to use two parameters(since and until).
RP['get_waivers'].add_argument('since', type=reqparse_since, location='args')
RP['get_waivers'].add_argument('page', default=1, type=int, location='args')
RP['get_waivers'].add_argument('limit', default=10, type=int, location='args')
RP['get_waivers'].add_argument('proxied_by', location='args')

RP['filter_waivers'] = reqparse.RequestParser()
RP['filter_waivers'].add_argument('filters', type=valid_filter_list, required=True, location='json')
RP['filter_waivers'].add_argument('include_obsolete', type=bool, default=False, location='json')

RP['get_waivers_by_subjects_and_testcase'] = rp = reqparse.RequestParser()
rp.add_argument('results', type=valid_results_list, location='json')
rp.add_argument('testcase', type=str, location='json')
rp.add_argument('product_version', type=str, location='json')
rp.add_argument('username', type=str, location='json')
rp.add_argument('proxied_by', location='json')
rp.add_argument('since', type=reqparse_since, location='json')
rp.add_argument('include_obsolete', type=bool, default=False, location='json')


class DummyJsonRequest(object):
    """
    Can be passed to reqparse.RequestParser.parse_args() instead of current
    request.
    """
    def __init__(self, data):
        self.json = data


class WaiversResource(Resource):
    @jsonp
    def get(self):
        """
        Get waiver records.

        **Sample request**:

        .. sourcecode:: http

           GET /api/v1.0/waivers/ HTTP/1.1
           Host: localhost:5004
           User-Agent: curl/7.51.0
           Accept: application/json

        **Sample response**:

        .. sourcecode:: http

           HTTP/1.1 200 OK
           Content-Type: application/json
           Content-Length: 184
           Server: Werkzeug/0.12.1 Python/2.7.13
           Date: Thu, 16 Mar 2017 13:53:14 GMT

           {
               "data": [],
               "first": "http://localhost:5004/api/v1.0/waivers/?page=1",
               "last": "http://localhost:5004/api/v1.0/waivers/?page=0",
               "next": null,
               "prev": null
           }


        :query int page: The page to get.
        :query int limit: Limit the number of items returned.
        :query string subject_type: Only include waivers for the given subject type.
        :query string subject_identifier: Only include waivers for the given subject identifier.
        :query string testcase: Only include waivers for the given test case name.
        :query string product_version: Only include waivers for the given
            product version.
        :query string username: Only include waivers which were submitted by
            the given user.
        :query string proxied_by: Only include waivers which were proxied on
            behalf of someone else by the given user.
        :query string since: An ISO 8601 formatted datetime (e.g. 2017-03-16T13:40:05+00:00)
            to filter results by. Optionally provide a second ISO 8601 datetime separated
            by a comma to retrieve a range (e.g. 2017-03-16T13:40:05+00:00,
            2017-03-16T13:40:15+00:00)
        :query boolean include_obsolete: If true, obsolete waivers will be included.
        :statuscode 200: If the query was valid and no problems were encountered.
            Note that the response may still contain 0 waivers.
        :statuscode 400: The request was malformed and could not be processed.
        """
        args = RP['get_waivers'].parse_args()
        query = Waiver.query.order_by(Waiver.timestamp.desc())

        if args['subject_type']:
            query = query.filter(Waiver.subject_type == args['subject_type'])
        if args['subject_identifier']:
            query = query.filter(Waiver.subject_identifier == args['subject_identifier'])
        if args['testcase']:
            query = query.filter(Waiver.testcase == args['testcase'])
        if args['product_version']:
            query = query.filter(Waiver.product_version == args['product_version'])
        if args['username']:
            query = query.filter(Waiver.username == args['username'])
        if args['proxied_by']:
            query = query.filter(Waiver.proxied_by == args['proxied_by'])
        if args['since']:
            since_start, since_end = args['since']
            if since_start:
                query = query.filter(Waiver.timestamp >= since_start)
            if since_end:
                query = query.filter(Waiver.timestamp <= since_end)
        if not args['include_obsolete']:
            query = _filter_out_obsolete_waivers(query)

        query = query.order_by(Waiver.timestamp.desc())
        return json_collection(query, args['page'], args['limit'])

    @jsonp
    @marshal_with(waiver_fields)
    def post(self):
        """
        Create a new waiver or multiple waivers.

        To create multiple waivers, pass list of dict instead. Response also
        contains list on success.

        **Sample request**:

        .. sourcecode:: http

           POST /api/v1.0/waivers/ HTTP/1.1
           Host: localhost:5004
           Accept-Encoding: gzip, deflate
           Accept: application/json
           Connection: keep-alive
           User-Agent: HTTPie/0.9.4
           Content-Type: application/json
           Content-Length: 91

           {
               "subject_type": "compose",
               "subject_identifier": "Fedora-9000-19700101.n.18",
               "testcase": "compose.install_no_user",
               "waived": false,
               "product_version": "Parrot",
               "comment": "This is fine"
           }



        **Sample response**:

        .. sourcecode:: http

           HTTP/1.0 201 CREATED
           Content-Length: 228
           Content-Type: application/json
           Date: Thu, 16 Mar 2017 17:42:04 GMT
           Server: Werkzeug/0.12.1 Python/2.7.13

           {
               "comment": "This is fine",
               "id": 15,
               "product_version": "Parrot",
               "subject_type": "compose",
               "subject_identifier": "Fedora-9000-19700101.n.18",
               "testcase": "compose.install_no_user",
               "timestamp": "2017-03-16T17:42:04.209638",
               "username": "jcline",
               "waived": false,
               "proxied_by": null
           }

        :json string subject_type: The type of thing which this waiver is for.
        :json string subject_identifier: The identifier of the thing this
            waiver is for. The semantics of this identifier depend on the
            "subject_type". For example, Koji builds are identified by their NVR.
        :json string testcase: The result testcase for the waiver.
        :json boolean waived: Whether or not the result is waived.
        :json string product_version: The product version string.
        :json string comment: A comment explaining the waiver.
        :json string username: Username on whose behalf the caller is proxying.
        :statuscode 201: The waiver was successfully created.
        """

        user, headers = waiverdb.auth.get_user(request)
        data = request.get_json(force=True)

        if isinstance(data, list):
            result = []
            for sub_data in data:
                sub_request = DummyJsonRequest(sub_data)
                args = RP['create_waiver'].parse_args(sub_request)
                one_result = self._create_waiver(args, user)
                result.append(one_result)
            db.session.add_all(result)
        else:
            args = RP['create_waiver'].parse_args()
            result = self._create_waiver(args, user)
            db.session.add(result)

        db.session.commit()

        return result, 201, headers

    def get_group_membership(self, user):
        try:
            import ldap
        except ImportError:
            raise InternalServerError(('If PERMISSION_MAPPING is defined, '
                                       'python-ldap needs to be installed.'))
        try:
            con = ldap.initialize(current_app.config['LDAP_HOST'])
            results = con.search_s(current_app.config['LDAP_BASE'], ldap.SCOPE_SUBTREE,
                                   f'(memberUid={user})', ['cn'])
            return [group[1]['cn'][0].decode('utf-8') for group in results]
        except ldap.LDAPError:
            log.exception('Some error occured initializing the LDAP connection.')
            raise Unauthorized('Some error occured initializing the LDAP connection.')
        except ldap.SERVER_DOWN:
            log.exception('The LDAP server is not reachable.')
            raise BadGateway('The LDAP server is not reachable.')

    def verify_authorization(self, user, testcase):
        if not current_app.config['PERMISSION_MAPPING']:
            return True
        if not (current_app.config.get('LDAP_HOST') and current_app.config.get('LDAP_BASE')):
            raise InternalServerError(('LDAP_HOST and LDAP_BASE also need to be defined '
                                       'if PERMISSION_MAPPING is defined.'))
        allowed_groups = []
        for testcase_pattern, permission in current_app.config['PERMISSION_MAPPING'].items():
            testcase_match = re.search(testcase_pattern, testcase)
            if testcase_match:
                # checking if the user is allowed
                if user in permission['users']:
                    return True
                allowed_groups += permission['groups']
        group_membership = self.get_group_membership(user)
        if not group_membership:
            raise Unauthorized(f'Couldn\'t find user {user} in LDAP')
        if set(group_membership) & set(allowed_groups):
            return True
        raise Unauthorized(('You are not authorized to submit a waiver '
                            f'for the test case {testcase}'))

    def _create_waiver(self, args, user):
        proxied_by = None
        if args.get('username'):
            if user not in current_app.config['SUPERUSERS']:
                raise Forbidden('user %s does not have the proxyuser ability' % user)
            proxied_by = user
            user = args['username']

        # WaiverDB < 0.6
        if args['result_id']:
            if args['subject'] or args['testcase']:
                raise BadRequest('Only result_id or subject and '
                                 'testcase are allowed.  Not both.')
            try:
                result = get_resultsdb_result(args.pop('result_id'))
            except requests.HTTPError as e:
                if e.response.status_code == 404:
                    raise BadRequest('Result id not found in Resultsdb')
                else:
                    raise ServiceUnavailable('Failed looking up result in Resultsdb: %s' % e)
            except Exception as e:
                raise ServiceUnavailable('Failed looking up result in Resultsdb: %s' % e)
            result_data = result['data']  # ResultsDB "extra data" for the given result
            if 'original_spec_nvr' in result_data:
                args['subject_type'] = 'koji_build'
                args['subject_identifier'] = result_data['original_spec_nvr'][0]
            elif 'type' in result_data and result_data['type'][0] in ['koji_build', 'brew-build']:
                args['subject_type'] = 'koji_build'
                args['subject_identifier'] = result_data['item'][0]
            elif 'type' in result_data:
                args['subject_type'] = result_data['type'][0]
                args['subject_identifier'] = result_data['item'][0]
            else:
                raise BadRequest('It is not possible to submit a waiver by '
                                 'id for this result. Please try again specifying '
                                 'a subject and a testcase.')
            args['testcase'] = result['testcase']['name']

        # WaiverDB < 0.11
        if args['subject']:
            args['subject_type'], args['subject_identifier'] = \
                subject_dict_to_type_identifier(args.pop('subject'))

        # These are not marked required in the RequestParser, because they may
        # be absent in the request but filled in by the backwards
        # compatibility logic above. So we check explicitly here, and give
        # back an error matching what RequestParser would do.
        if not args['subject_type']:
            raise BadRequest({'subject_type': 'Missing required parameter in the JSON body'})
        if not args['subject_identifier']:
            raise BadRequest({'subject_identifier': 'Missing required parameter in the JSON body'})
        if not args['testcase']:
            raise BadRequest({'testcase': 'Missing required parameter in the JSON body'})

        self.verify_authorization(user, args['testcase'])

        # brew-build is an alias for koji_build
        if args['subject_type'] == 'brew-build':
            args['subject_type'] = 'koji_build'

        return Waiver(
            args['subject_type'],
            args['subject_identifier'],
            args['testcase'],
            user,
            args['product_version'],
            args['waived'],
            args['comment'],
            proxied_by)


class WaiverResource(Resource):
    @jsonp
    @marshal_with(waiver_fields)
    def get(self, waiver_id):
        """
        Get a single waiver by waiver ID.

        :param int waiver_id: The waiver's database ID.

        :statuscode 200: The waiver was found and returned.
        :statuscode 404: No waiver exists with that ID.
        """
        try:
            return Waiver.query.get_or_404(waiver_id)
        except Exception as NotFound:
            raise type(NotFound)('Waiver not found')


class FilteredWaiversResource(Resource):

    @marshal_with(waiver_fields, envelope='data')
    def post(self):
        """
        Get waiver records, filtered by some criteria.

        This API behaves the same way as :http:get:`/api/v1.0/waivers/`, but it
        allows for longer or more complex filter criteria that cannot be
        expressed in the query string.

        Note that the response is not paginated (that is, *all* waivers are
        returned in the 'data' key, even if there is a large number of them).

        **Sample request**:

        .. sourcecode:: http

           POST /api/v1.0/waivers/+filtered HTTP/1.1
           Accept: application/json
           Content-Type: application/json

           {
                "filters": [
                    {
                        "subject_type": "compose",
                        "subject_identifier": "Fedora-9000-19700101.n.18",
                        "testcase": "compose.install_no_user"
                    },
                    {
                        "subject_type": "koji_build",
                        "subject_identifier": "gzip-1.9-1.fc28",
                        "testcase": "dist.rpmlint"
                    }
                ]
           }

        **Sample response**:

        .. sourcecode:: none

           HTTP/1.1 200 OK
           Content-Type: application/json

           {
                "data": [
                    {
                        "id": 15,
                        "comment": "The tests broke",
                        "product_version": "fedora-27",
                        "subject_type": "compose",
                        "subject_identifier": "Fedora-9000-19700101.n.18",
                        "testcase": "compose.install_no_user",
                        "timestamp": "2017-03-16T17:42:04.209638",
                        "username": "jcline",
                        "waived": true,
                        "proxied_by": null
                    }
                ]
           }

        :json list filters: List of filter dicts. If the list contains
            multiple filter dicts, they are combined with logical OR. Within
            each filter dict, the criteria are combined with logical AND. Keys
            within the filter dict are the same as the filtering
            parameters accepted by :http:get:`/api/v1.0/waivers/`.
        :json boolean include_obsolete: If true, obsolete waivers will be included.
        :statuscode 200: Returns matching waivers, if any.
        :statuscode 400: The request was malformed (invalid filter critera).
        """
        args = RP['filter_waivers'].parse_args()
        query = Waiver.query.order_by(Waiver.timestamp.desc())
        clauses = []
        for filter_ in args['filters']:
            inner_clauses = []
            if 'subject_type' in filter_:
                inner_clauses.append(Waiver.subject_type == filter_['subject_type'])
            if 'subject_identifier' in filter_:
                inner_clauses.append(Waiver.subject_identifier == filter_['subject_identifier'])
            if 'testcase' in filter_:
                inner_clauses.append(Waiver.testcase == filter_['testcase'])
            if 'product_version' in filter_:
                inner_clauses.append(Waiver.product_version == filter_['product_version'])
            if 'username' in filter_:
                inner_clauses.append(Waiver.username == filter_['username'])
            if 'proxied_by' in filter_:
                inner_clauses.append(Waiver.proxied_by == filter_['proxied_by'])
            if 'since' in filter_:
                try:
                    since_start, since_end = reqparse_since(filter_['since'])
                except ValueError as e:
                    raise BadRequest({'since': str(e)})
                if since_start:
                    inner_clauses.append(Waiver.timestamp >= since_start)
                if since_end:
                    inner_clauses.append(Waiver.timestamp <= since_end)
            clauses.append(and_(*inner_clauses))
        query = query.filter(or_(*clauses))
        if not args['include_obsolete']:
            subquery = db.session.query(func.max(Waiver.id))\
                .group_by(Waiver.subject_type, Waiver.subject_identifier, Waiver.testcase)
            query = query.filter(Waiver.id.in_(subquery))
        return query.all()


class GetWaiversBySubjectsAndTestcases(Resource):
    @jsonp
    def post(self):
        """
        **Deprecated.** Use :http:post:`/api/v1.0/waivers/+filtered` instead.

        Instead of making a deprecated request like this:

        .. sourcecode:: http

           POST /api/v1.0/waivers/+by-subjects-and-testcases HTTP/1.1
           Content-Type: application/json

           {
                "results": [
                    {
                        "subject": {"productmd.compose.id": "Fedora-9000-19700101.n.18"},
                        "testcase": "compose.install_no_user"
                    },
                    {
                        "subject": {"item": "gzip-1.9-1.fc28", "type": "koji_build"},
                        "testcase": "dist.rpmlint"
                    }
                ]
           }

        make the following equivalent request:

        .. sourcecode:: http

           POST /api/v1.0/waivers/+filtered HTTP/1.1
           Content-Type: application/json

           {
                "filters": [
                    {
                        "subject_type": "compose",
                        "subject_identifier": "Fedora-9000-19700101.n.18",
                        "testcase": "compose.install_no_user"
                    },
                    {
                        "subject_type": "koji_build",
                        "subject_identifier": "gzip-1.9-1.fc28",
                        "testcase": "dist.rpmlint"
                    }
                ]
           }
        """
        args = RP['get_waivers_by_subjects_and_testcase'].parse_args()
        query = Waiver.query.order_by(Waiver.timestamp.desc())
        if args['results']:
            query = Waiver.by_results(query, args['results'])
        if args['product_version']:
            query = query.filter(Waiver.product_version == args['product_version'])
        if args['username']:
            query = query.filter(Waiver.username == args['username'])
        if args['proxied_by']:
            query = query.filter(Waiver.proxied_by == args['proxied_by'])
        if args['since']:
            since_start, since_end = args['since']
            if since_start:
                query = query.filter(Waiver.timestamp >= since_start)
            if since_end:
                query = query.filter(Waiver.timestamp <= since_end)
        if not args['include_obsolete']:
            query = _filter_out_obsolete_waivers(query)

        query = query.order_by(Waiver.timestamp.desc())
        return {'data': marshal(query.all(), waiver_fields)}


class AboutResource(Resource):
    @jsonp
    def get(self):
        """
        Returns the current running version and the method used for authentication.

        **Sample response**:

        .. sourcecode:: none

          HTTP/1.0 200 OK
          Content-Length: 55
          Content-Type: application/json
          Date: Tue, 31 Oct 2017 04:29:19 GMT
          Server: Werkzeug/0.11.10 Python/2.7.13

          {
            "auth_method": "OIDC",
            "version": "0.3.1"
          }

        :statuscode 200: Currently running waiverdb software version and authentication
                         are returned.
        """
        return {'version': __version__, 'auth_method': current_app.config['AUTH_METHOD']}


class MonitorResource(Resource):
    def get(self):
        from waiverdb.monitor import MonitorAPI
        return MonitorAPI().get()


# set up the Api resource routing here
api.add_resource(WaiversResource, '/waivers/')
api.add_resource(WaiverResource, '/waivers/<int:waiver_id>')
api.add_resource(FilteredWaiversResource, '/waivers/+filtered')
api.add_resource(GetWaiversBySubjectsAndTestcases, '/waivers/+by-subjects-and-testcases')
api.add_resource(AboutResource, '/about', strict_slashes=False)
api.add_resource(MonitorResource, '/metrics')
