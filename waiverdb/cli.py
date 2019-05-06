# SPDX-License-Identifier: GPL-2.0+
"""
CLI for creating new waivers against test results.
"""
import click
import requests
import json
import configparser
import re
from xmlrpc import client

requests_session = requests.Session()


class OldJSONSubject(click.ParamType):
    """
    Deprecated JSON subject CLI parameter.
    """
    name = 'Deprecated JSON subject'

    def convert(self, value, param, ctx):
        if not isinstance(value, str):
            return value

        try:
            subject = json.loads(value)
        except json.JSONDecodeError as e:
            raise click.ClickException('Invalid JSON object: {}'.format(e))

        if not isinstance(subject, dict):
            raise click.ClickException(
                'Failed to parse JSON. Please use id and type instead of using subject.')

        return subject


def validate_config(config):
    """
    Validates the configuration needed for WaiverDB
    :return: None or ClickException
    """
    # Verify that all necessary config options are set
    config_error = ('The config option "{0}" is required')
    if not config.has_option('waiverdb', 'auth_method'):
        raise click.ClickException(config_error.format('auth_method'))
    auth_method = config.get('waiverdb', 'auth_method')
    if auth_method not in ['OIDC', 'Kerberos', 'dummy']:
        raise click.ClickException('The WaiverDB authentication mechanism of '
                                   '"{0}" is not supported'.format(auth_method))
    required_configs = ['api_url']
    if auth_method == 'OIDC':
        required_configs.append('oidc_id_provider')
        required_configs.append('oidc_client_id')
        required_configs.append('oidc_scopes')
    for required_config in required_configs:
        if not config.has_option('waiverdb', required_config):
            raise click.ClickException(config_error.format(required_config))


def print_result(waiver_id, result_description):
    click.echo('Created waiver {0} for result with {1}'.format(waiver_id, result_description))


def check_response(resp, result_ids):
    if not resp.ok:
        try:
            error_msg = resp.json()['message']
        except (ValueError, KeyError):
            error_msg = resp.text
        raise click.ClickException(
            'Failed to create waivers: {0}'
            .format(error_msg))

    response_data = resp.json()
    if result_ids:
        if len(response_data) != len(result_ids):
            raise RuntimeError(
                'Unexpected number of results in response: {!r}'.format(response_data))

        for result_id, data in zip(result_ids, response_data):
            waiver_id = data['id']
            msg = 'id {0}'.format(result_id)
            print_result(waiver_id, msg)
    else:
        for data in response_data:
            waiver_id = data['id']
            msg = 'subject type {0}, identifier {1} and testcase {2}'.format(
                data['subject_type'], data['subject_identifier'], data['testcase'])
            print_result(waiver_id, msg)


def guess_product_version(toparse, koji_build=False):
    if toparse == 'rawhide' or toparse.startswith('Fedora-Rawhide'):
        return 'fedora-rawhide'
    else:
        product_version = None
        if (toparse.startswith('f') and koji_build):
            product_version = 'fedora-'
        elif toparse.startswith('epel'):
            product_version = 'epel-'
        elif toparse.startswith('el'):
            product_version = 'rhel-'
        elif toparse.startswith('fc') or toparse.startswith('Fedora'):
            product_version = 'fedora-'
        if product_version:
            # seperate the prefix from the number
            result = list(filter(None, '-'.join(re.split(r'(\d+)', toparse)).split('-')))
            if len(result) >= 2:
                try:
                    int(result[1])
                    product_version += result[1]
                    return product_version
                except ValueError:
                    pass
    return None


@click.command(context_settings={'help_option_names': ['-h', '--help']})
@click.option('--config-file', '-C', default='/etc/waiverdb/client.conf',
              type=click.Path(exists=True),
              help='Specify a config file to use')
@click.option('--result-id', '-r', multiple=True, type=int,
              help='Specify one or more results to be waived')
@click.option('--subject', '-s', type=OldJSONSubject(),
              help=('Deprecated. Use --subject-identifier and --subject-type instead. '
                    'Subject for a result to waive.'))
@click.option('--subject-identifier', '-i',
              help='Subject identifier for a result to waive.')
@click.option('--subject-type', '-T',
              help='Subject type for a result to waive.')
@click.option('--testcase', '-t',
              help='Specify a testcase for the subject')
@click.option('--product-version', '-p',
              help='Specify one of PDC\'s product version identifiers.')
@click.option('--waived/--no-waived', default=True,
              help='Whether or not the result is waived')
@click.option('--comment', '-c',
              help='A comment explaining why the result is waived')
@click.option('--username', '-u', default=None,
              help='Username on whose behalf the caller is proxying.')
def cli(username, comment, waived, product_version, testcase, subject, subject_identifier,
        subject_type, result_id, config_file):
    """
    Creates new waiver against test results.

    Examples:

    \b
        waiverdb-cli -r 47 -r 48 -p "fedora-28" -c "This is fine"

    \b
        waiverdb-cli -t dist.rpmdeplint -i qclib-1.3.1-3.fc28 -T koji_build \\
            -p "fedora-28" -c "This is expected for non-x86 packages"
    """
    config = configparser.SafeConfigParser()

    config.read(config_file)
    validate_config(config)

    result_ids = result_id

    # Backward compatibility with v0.11.0.
    if subject:
        if subject_identifier or subject_type:
            raise click.ClickException(
                'Please don\'t specify subject when using identifier and type.')
        if result_ids:
            raise click.ClickException('Please specify result_id or subject/testcase. Not both')

        subject_identifier = subject.get("productmd.compose.id")
        if subject_identifier:
            subject_type = "compose"
        else:
            subject_identifier = subject.get("item")
            subject_type = subject.get("type")

    if not comment:
        raise click.ClickException('Please specify comment')
    if result_ids and (testcase or subject_identifier):
        raise click.ClickException('Please specify result_id or id/type/testcase. Not both')
    if not result_ids and not subject_identifier:
        raise click.ClickException('Please specify subject-identifier')
    if not result_ids and not testcase:
        raise click.ClickException('Please specify testcase')
    if not result_ids and not subject_type:
        raise click.ClickException('Please specify subject_type')

    if not product_version and not result_ids:
        # trying to guess the product_version
        if subject_type == 'koji_build':
            try:
                short_prod_version = subject_identifier.split('.')[-1]
                product_version = guess_product_version(short_prod_version, koji_build=True)
            except KeyError:
                pass

        # try to call koji
        if config.has_option('waiverdb', 'koji_base_url'):
            koji_base_url = config.get('waiverdb', 'koji_base_url')
            proxy = client.ServerProxy(koji_base_url)
            try:
                build = proxy.getBuild(subject_identifier)
                if build:
                    target = proxy.getTaskRequest(build['task_id'])[1]
                    product_version = guess_product_version(target, koji_build=True)
            except KeyError:
                pass
            except client.Fault:
                pass

        if subject_type == "compose":
            product_version = guess_product_version(subject_identifier)

    if not product_version:
        raise click.ClickException('Please specify product version using --product-version')

    auth_method = config.get('waiverdb', 'auth_method')
    data_list = []
    if not result_ids:
        data_list.append({
            'subject_identifier': subject_identifier,
            'subject_type': subject_type,
            'testcase': testcase,
            'waived': waived,
            'product_version': product_version,
            'comment': comment,
            'username': username
        })

    # XXX - TODO - remove this in a future release.  (for backwards compat)
    for result_id in result_ids:
        data_list.append({
            'result_id': result_id,
            'waived': waived,
            'product_version': product_version,
            'comment': comment,
            'username': username
        })

    api_url = config.get('waiverdb', 'api_url')
    url = '{0}/waivers/'.format(api_url.rstrip('/'))
    data = json.dumps(data_list)
    common_request_arguments = {
        'data': data,
        'headers': {'Content-Type': 'application/json'},
        'timeout': 60,
    }
    if auth_method == 'OIDC':
        # Try to import this now so the user gets immediate feedback if
        # it isn't installed
        try:
            import openidc_client  # noqa: F401
        except ImportError:
            raise click.ClickException('python-openidc-client needs to be installed')
        # Get the auth token using the OpenID client.
        oidc_client_secret = None
        if config.has_option('waiverdb', 'oidc_client_secret'):
            oidc_client_secret = config.get('waiverdb', 'oidc_client_secret')
        oidc = openidc_client.OpenIDCClient(
            'waiverdb',
            config.get('waiverdb', 'oidc_id_provider'),
            {'Token': 'Token', 'Authorization': 'Authorization'},
            config.get('waiverdb', 'oidc_client_id'),
            oidc_client_secret)
        scopes = config.get('waiverdb', 'oidc_scopes').strip().splitlines()

        resp = oidc.send_request(
            scopes=scopes,
            url=url,
            **common_request_arguments)
        check_response(resp, result_ids)
    elif auth_method == 'Kerberos':
        # Try to import this now so the user gets immediate feedback if
        # it isn't installed
        try:
            import requests_gssapi  # noqa: F401
        except ImportError:
            raise click.ClickException(
                'python-requests-gssapi needs to be installed')
        auth = requests_gssapi.HTTPKerberosAuth(
            mutual_authentication=requests_gssapi.OPTIONAL)
        resp = requests.request(
            'POST', url, auth=auth, **common_request_arguments)
        if resp.status_code == 401:
            msg = resp.json().get(
                'message', ('WaiverDB authentication using GSSAPI failed. Make sure you have a '
                            'valid Kerberos ticket or that you correctly configured your Kerberos '
                            'configuration file. Please check the doc for troubleshooting '
                            'information.'))
            raise click.ClickException(msg)
        check_response(resp, result_ids)
    elif auth_method == 'dummy':
        resp = requests.request(
            'POST', url, auth=('user', 'pass'), **common_request_arguments)
        check_response(resp, result_ids)


if __name__ == '__main__':
    cli()  # pylint: disable=E1120
