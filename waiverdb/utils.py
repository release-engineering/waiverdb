# SPDX-License-Identifier: GPL-2.0+

import functools
import stomp
from flask import request, url_for, jsonify, current_app, Flask
from flask_restx import marshal
from flask_pydantic.exceptions import ValidationError
from waiverdb.fields import waiver_fields
from werkzeug.exceptions import BadRequest, NotFound, HTTPException
from contextlib import contextmanager

VALIDATION_KEYS = frozenset({
    "input", "loc", "msg", "type", "url"
})


def json_collection(query, page=1, limit=10):
    """
    Helper function for Flask request handlers which want to return
    a collection of resources as JSON.
    """
    try:
        p = query.paginate(page=page, per_page=limit)
    except NotFound:
        return {'data': [], 'prev': None, 'next': None, 'first': None, 'last': None}
    pages = {'data': marshal(p.items, waiver_fields)}
    query_pairs = request.args.copy()
    if query_pairs:
        # remove the page number
        query_pairs.pop('page', default=None)
    if p.has_prev:
        pages['prev'] = url_for(request.endpoint, page=p.prev_num, _external=True,
                                **query_pairs)
    else:
        pages['prev'] = None
    if p.has_next:
        pages['next'] = url_for(request.endpoint, page=p.next_num, _external=True,
                                **query_pairs)
    else:
        pages['next'] = None
    pages['first'] = url_for(request.endpoint, page=1, _external=True, **query_pairs)
    pages['last'] = url_for(request.endpoint, page=p.pages, _external=True, **query_pairs)
    return pages


def json_error(error):
    """
    Return error responses in JSON.

    :param error: One of Exceptions. It could be HTTPException, ConnectionError, or
    Timeout.
    :return: JSON error response.

    """
    if not isinstance(error, (BadRequest, NotFound)):
        current_app.logger.warning("%s: %s", type(error).__name__, error)

    if isinstance(error, HTTPException):
        response = jsonify(message=error.description)
        if error.code is not None:
            response.status_code = error.code
    else:
        # Could be ConnectionError or Timeout
        response = jsonify(message=str(error))
        response.status_code = 500

    return response


def handle_validation_error(error: ValidationError):
    errors = (
        error.body_params
        or error.form_params
        or error.path_params
        or error.query_params
    )
    # Keep only interesting stuff and remove objects potentially
    # unserializable in JSON.
    err = [
        {k: v for k, v in e.items() if k in VALIDATION_KEYS}
        for e in errors
    ]
    response = jsonify({"validation_error": err})
    response.status_code = 400
    return response


def jsonp(func):
    """Wraps Jsonified output for JSONP requests."""
    @functools.wraps(func)
    def wrapped(*args, **kwargs):
        callback = request.args.get('callback', False)
        if callback:
            resp = jsonify(func(*args, **kwargs))
            resp.set_data('{}({})'.format(
                str(callback),
                resp.get_data()
            ))
            resp.mimetype = 'application/javascript'
            return resp
        else:
            return func(*args, **kwargs)
    return wrapped


@contextmanager
def stomp_connection():
    """
    Helper function for stomp connection.
    """
    if current_app.config.get('STOMP_CONFIGS'):
        configs = current_app.config.get('STOMP_CONFIGS')
        if 'destination' not in configs or not configs['destination']:
            raise RuntimeError('stomp was configured to publish messages, '
                               'but destination is not configured in STOMP_CONFIGS')
        if 'connection' not in configs or not configs['connection']:
            raise RuntimeError('stomp was configured to publish messages,, '
                               'but connection is not configured in STOMP_CONFIGS')

        conn_args = configs['connection'].copy()
        if 'use_ssl' in conn_args:
            use_ssl = conn_args['use_ssl']
            del conn_args['use_ssl']
        else:
            use_ssl = False

        ssl_args = {'for_hosts': conn_args['host_and_ports']}
        for attr in ('key_file', 'cert_file', 'ca_certs'):
            conn_attr = f'ssl_{attr}'
            if conn_attr in conn_args:
                ssl_args[attr] = conn_args[conn_attr]
                del conn_args[conn_attr]

        conn = stomp.connect.StompConnection11(**conn_args)

        if use_ssl:
            conn.set_ssl(**ssl_args)

        conn.connect(wait=True, **configs.get('credentials', {}))

        try:
            yield conn
        finally:
            conn.disconnect()
    else:
        raise RuntimeError('stomp was configured to publish messages, '
                           'but STOMP_CONFIGS is not configured')


def auth_methods(app: Flask) -> list[str]:
    methods = app.config.get('AUTH_METHODS')
    if methods:
        return methods

    method = app.config.get('AUTH_METHOD')
    if method:
        return [method]

    return []
