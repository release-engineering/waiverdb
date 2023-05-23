# SPDX-License-Identifier: GPL-2.0+

import logging

import requests
from flask import (
    Blueprint,
    Response,
    current_app,
    escape,
    redirect,
    render_template,
    request,
    url_for,
)
from flask_oidc import OpenIDConnect
from flask_pydantic import validate
from flask_restful import Resource, Api, marshal_with, marshal
from werkzeug.exceptions import (
    BadRequest,
    Forbidden,
    ServiceUnavailable,
    Unauthorized,
)
from sqlalchemy.sql.expression import func, and_, or_
from waiverdb import __version__
from waiverdb.authorization import match_testcase_permissions, verify_authorization
from waiverdb.models import db
from waiverdb.models.waivers import Waiver, subject_dict_to_type_identifier
from waiverdb.models.requests import (
    GetWaivers, CreateWaiver, FilterWaivers, GetWaiversBySubjectAndTestcase, GetPermissions,
    parse_since, WaiverFilter, CreateWaiverList
)
from waiverdb.utils import json_collection, jsonp
from waiverdb.fields import waiver_fields
import waiverdb.auth

api_v1 = (Blueprint('api_v1', __name__))
api = Api(api_v1)
requests_session = requests.Session()
log = logging.getLogger(__name__)
oidc = OpenIDConnect()


def get_resultsdb_result(result_id):
    response = requests_session.request('GET', '{0}/results/{1}'.format(
        current_app.config['RESULTSDB_API_URL'], result_id),
        headers={'Content-Type': 'application/json'},
        timeout=60)
    response.raise_for_status()
    return response.json()


def permissions():
    """
    Return PERMISSIONS configuration.
    PERMISSION_MAPPING converted to the new format.
    """
    permissions_config = current_app.config.get('PERMISSIONS')
    if permissions_config:
        return permissions_config

    permission_mapping = current_app.config.get('PERMISSION_MAPPING')
    if permission_mapping:
        return [
            {
                "name": testcase_pattern,
                "maintainers": [props["maintainer"]] if "maintainer" in props else [],
                "_testcase_regex_pattern": testcase_pattern,
                "groups": props.get("groups", []),
                "users": props.get("users", []),
            }
            for testcase_pattern, props in permission_mapping.items()
        ]

    return []


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
        Waiver.scenario,
        Waiver.username,
        Waiver.product_version,
    )
    return query.filter(Waiver.id.in_(subquery))


def _verify_authorization(user, testcase):
    if not permissions():
        return True

    ldap_host = current_app.config.get('LDAP_HOST')
    ldap_searches = current_app.config.get('LDAP_SEARCHES')
    if not ldap_searches:
        ldap_base = current_app.config.get('LDAP_BASE')
        if ldap_base:
            ldap_search_string = current_app.config.get('LDAP_SEARCH_STRING', '(memberUid={user})')
            ldap_searches = [{'BASE': ldap_base, 'SEARCH_STRING': ldap_search_string}]
    return verify_authorization(user, testcase, permissions(), ldap_host, ldap_searches)


def _authorization_warning_from_exception(e: Unauthorized, testcase: str):
    permissions_url = url_for('api_v1.permissionsresource', testcase=testcase)
    return (
        f"{escape(str(e))}<br>"
        f"<a href={permissions_url}>See who has permission to"
        f" waive {escape(testcase)} test case."
        "</a>"
    )


def _authorization_warning(request):
    testcase = request.args.get("testcase")
    if testcase:
        user, _headers = waiverdb.auth.get_user(request)
        try:
            _verify_authorization(user, testcase)
        except Unauthorized as e:
            return _authorization_warning_from_exception(e, testcase)
    return None


class WaiversResource(Resource):
    @jsonp
    @validate(query=GetWaivers)
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
        :query string scenario: Only include waivers for the given scenario name.
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

        args = GetWaivers.parse_obj(request.args)

        query = Waiver.query.order_by(Waiver.timestamp.desc())

        if args.subject_type:
            query = query.filter(Waiver.subject_type == args.subject_type)
        if args.subject_identifier:
            query = query.filter(Waiver.subject_identifier == args.subject_identifier)
        if args.testcase:
            query = query.filter(Waiver.testcase == args.testcase)
        if args.scenario:
            query = query.filter(Waiver.scenario == args.scenario)
        if args.product_version:
            query = query.filter(Waiver.product_version == args.product_version)
        if args.username:
            query = query.filter(Waiver.username == args.username)
        if args.proxied_by:
            query = query.filter(Waiver.proxied_by == args.proxied_by)
        if args.since:
            since_start, since_end = parse_since(args.since)
            if since_start:
                query = query.filter(Waiver.timestamp >= since_start)
            if since_end:
                query = query.filter(Waiver.timestamp <= since_end)
        if not args.include_obsolete:
            query = _filter_out_obsolete_waivers(query)

        query = query.order_by(Waiver.timestamp.desc())
        return json_collection(query, args.page, args.limit)

    @jsonp
    @validate(body=CreateWaiverList)
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
               "scenario": null,
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
        :json string scenario: The result scenario for the waiver.
        :json boolean waived: Whether or not the result is waived.
        :json string product_version: The product version string.
        :json string comment: A comment explaining the waiver.
        :json string username: Username on whose behalf the caller is proxying.
        :statuscode 201: The waiver was successfully created.
        """

        user, headers = waiverdb.auth.get_user(request)
        data = request.get_json(force=True)

        data = CreateWaiverList.parse_obj(data).__root__
        if isinstance(data, list):
            result = [self._create_waiver(sub_data, user) for sub_data in data]
            db.session.add_all(result)
        else:
            result = self._create_waiver(data, user)
            db.session.add(result)

        db.session.commit()

        return result, 201, headers

    @staticmethod
    def _create_waiver(args: CreateWaiver, user):
        proxied_by = None
        if args.username:
            if user not in current_app.config['SUPERUSERS']:
                raise Forbidden('user %s does not have the proxyuser ability' % user)
            proxied_by = user
            user = args.username

        # WaiverDB < 0.6
        if args.result_id is not None:
            try:
                result = get_resultsdb_result(args.result_id)
            except requests.HTTPError as e:
                if e.response.status_code == 404:
                    raise BadRequest('Result id not found in Resultsdb')
                else:
                    raise ServiceUnavailable('Failed looking up result in Resultsdb: %s' % e)
            except Exception as e:
                raise ServiceUnavailable('Failed looking up result in Resultsdb: %s' % e)
            result_data = result['data']  # ResultsDB "extra data" for the given result
            if 'original_spec_nvr' in result_data:
                args.subject_type = 'koji_build'
                args.subject_identifier = result_data['original_spec_nvr'][0]
            elif 'type' in result_data and result_data['type'][0] in ['koji_build', 'brew-build']:
                args.subject_type = 'koji_build'
                args.subject_identifier = result_data['item'][0]
            elif 'type' in result_data:
                args.subject_type = result_data['type'][0]
                args.subject_identifier = result_data['item'][0]
            else:
                raise BadRequest('It is not possible to submit a waiver by '
                                 'id for this result. Please try again specifying '
                                 'a subject and a testcase.')
            args.testcase = result['testcase']['name']
            if 'scenario' in result_data:
                args.scenario = result_data['scenario'][0]

        # WaiverDB < 0.11
        if args.subject:
            args.subject_type, args.subject_identifier = \
                subject_dict_to_type_identifier(args.subject)

        _verify_authorization(user, args.testcase)

        # brew-build is an alias for koji_build
        if args.subject_type == 'brew-build':
            args.subject_type = 'koji_build'

        return Waiver(
            args.subject_type,
            args.subject_identifier,
            args.testcase,
            user,
            args.product_version,
            args.waived,
            args.comment,
            proxied_by,
            args.scenario
        )


class WaiversNewResource(WaiversResource):
    @oidc.require_login
    def get(self):
        """
        HTML form to create a waiver.

        Default form input field values can be passed as request query parameters.

        :query string subject_type: The type of thing which this waiver is for.
        :query string subject_identifier: The identifier of the thing this
            waiver is for. The semantics of this identifier depend on the
            "subject_type". For example, Koji builds are identified by their NVR.
        :query string testcase: The result testcase for the waiver.
        :query string scenario: The result scenario for the waiver.
        :query string product_version: The product version string.
        :query string comment: A comment explaining the waiver.

        :statuscode 200: The HTML with the form is returned.
        """
        warning = request.args.get("error") or _authorization_warning(request)
        new_waiver_id = request.args.get("new_waiver_id")
        new_waiver_url = None
        if new_waiver_id is not None:
            new_waiver_url = url_for('api_v1.waiverresource', waiver_id=new_waiver_id)
        html = render_template(
            'new_waiver.html',
            warning=warning,
            error=request.args.get("error"),
            new_waiver_url=new_waiver_url,
            request_args=request.args,
        )
        return Response(html, mimetype='text/html')


class WaiversCreateResource(WaiversResource):
    @oidc.require_login
    @validate()
    def get(self, query: CreateWaiver):
        user = oidc.user_getfield(current_app.config["OIDC_USERNAME_FIELD"])
        try:
            result = self._create_waiver(query, user)
        except Unauthorized as e:
            error = _authorization_warning_from_exception(e, query.testcase)
            url = url_for(
                "api_v1.waiversnewresource",
                error=error,
                **request.args,
            )
            return redirect(url)

        db.session.add(result)
        db.session.commit()

        url = url_for(
            "api_v1.waiversnewresource",
            new_waiver_id=result.id,
            **request.args,
        )
        return redirect(url)


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
    @validate(body=FilterWaivers)
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
                        "scenario": null,
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
        args = FilterWaivers.parse_obj(request.get_json(force=True))
        query = Waiver.query.order_by(Waiver.timestamp.desc())
        clauses = []
        filter_: WaiverFilter
        for filter_ in args.filters:
            inner_clauses = []
            if filter_.subject_type:
                inner_clauses.append(Waiver.subject_type == filter_.subject_type)
            if filter_.subject_identifier:
                inner_clauses.append(Waiver.subject_identifier == filter_.subject_identifier)
            if filter_.testcase:
                inner_clauses.append(Waiver.testcase == filter_.testcase)
            if filter_.scenario:
                inner_clauses.append(Waiver.scenario == filter_.scenario)
            if filter_.product_version:
                inner_clauses.append(Waiver.product_version == filter_.product_version)
            if filter_.username:
                inner_clauses.append(Waiver.username == filter_.username)
            if filter_.proxied_by:
                inner_clauses.append(Waiver.proxied_by == filter_.proxied_by)
            if filter_.since:
                since_start, since_end = parse_since(filter_.since)
                if since_start:
                    inner_clauses.append(Waiver.timestamp >= since_start)
                if since_end:
                    inner_clauses.append(Waiver.timestamp <= since_end)
            clauses.append(and_(*inner_clauses))
        query = query.filter(or_(*clauses))
        if not args.include_obsolete:
            subquery = db.session.query(func.max(Waiver.id))\
                .group_by(Waiver.subject_type, Waiver.subject_identifier, Waiver.testcase)
            query = query.filter(Waiver.id.in_(subquery))
        return query.all()


class GetWaiversBySubjectsAndTestcases(Resource):
    @jsonp
    @validate(body=GetWaiversBySubjectAndTestcase)
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
        data = request.get_json(force=True)
        args = GetWaiversBySubjectAndTestcase.parse_obj(data)
        query = Waiver.query.order_by(Waiver.timestamp.desc())
        if args.results:
            query = Waiver.by_results(query, args.results)
        if args.product_version:
            query = query.filter(Waiver.product_version == args.product_version)
        if args.username:
            query = query.filter(Waiver.username == args.username)
        if args.proxied_by:
            query = query.filter(Waiver.proxied_by == args.proxied_by)
        if args.since:
            since_start, since_end = parse_since(args.since)
            if since_start:
                query = query.filter(Waiver.timestamp >= since_start)
            if since_end:
                query = query.filter(Waiver.timestamp <= since_end)
        if not args.include_obsolete:
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


class ConfigResource(Resource):
    @jsonp
    def get(self):
        """
        Returns the current configuration (PERMISSION_MAPPING and SUPERUSERS).

        **Note:** PERMISSION_MAPPING is **deprecated**,
        use :http:get:`/api/v1.0/permissions` instead.

        **Sample response**:

        .. sourcecode:: none

          HTTP/1.0 200 OK
          Content-Length: 55
          Content-Type: application/json
          Date: Tue, 31 Oct 2017 04:29:19 GMT
          Server: Werkzeug/0.11.10 Python/2.7.13

          {
            "permission_mapping": {
                "^kernel-qe": {
                    "groups": ["devel", "qa"],
                    "users": []
                }
            },
            "superusers": ["alice", "bob"]
          }

        :statuscode 200: Configuration is returned.
        """
        return {
            'permission_mapping': current_app.config.get('PERMISSION_MAPPING'),
            'superusers': current_app.config.get('SUPERUSERS'),
        }


class PermissionsResource(Resource):
    @jsonp
    @validate(query=GetPermissions)
    def get(self):
        """
        Returns the waiver permissions.

        **Sample response**:

        .. sourcecode:: none

          HTTP/1.0 200 OK
          Content-Length: 999
          Content-Type: application/json
          Server: gunicorn/20.0.4
          Date: Wed, 10 Mar 2021 08:00:00 GMT

          [
              {
                  "name": "kernel-qe",
                  "maintainers": ["alice@example.com"],
                  "testcases": ["kernel-qe.*"],
                  "groups": ["devel", "qa"],
                  "users": ["alice@example.com"]
              },
              {
                  "name": "Greenwave Tests",
                  "maintainers": ["greenwave-dev@example.com"],
                  "testcases": ["greenwave-tests.*"],
                  "groups": [],
                  "users": ["HTTP/greenwave-dev.tests.example.com"]
              }
          ]

        :json string testcase: If specified, only permissions for given test case is returned.
        :statuscode 200: Permissions are returned.
        """
        args = GetPermissions.parse_obj(request.args)
        testcase = args.testcase
        if testcase:
            return list(match_testcase_permissions(testcase, permissions()))

        return permissions()


class MonitorResource(Resource):
    def get(self):
        from waiverdb.monitor import MonitorAPI
        return MonitorAPI().get()


# set up the Api resource routing here
api.add_resource(WaiversResource, '/waivers/')
api.add_resource(WaiversNewResource, '/waivers/new')
api.add_resource(WaiversCreateResource, '/waivers/create')
api.add_resource(WaiverResource, '/waivers/<int:waiver_id>')
api.add_resource(FilteredWaiversResource, '/waivers/+filtered')
api.add_resource(GetWaiversBySubjectsAndTestcases, '/waivers/+by-subjects-and-testcases')
api.add_resource(AboutResource, '/about', strict_slashes=False)
api.add_resource(ConfigResource, '/config', strict_slashes=False)
api.add_resource(PermissionsResource, '/permissions', strict_slashes=False)
api.add_resource(MonitorResource, '/metrics')
