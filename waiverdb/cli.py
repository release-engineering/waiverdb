# SPDX-License-Identifier: GPL-2.0+
"""
CLI for creating new waivers against test results.
"""
import click
import requests
import json
import configparser

requests_session = requests.Session()


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
    if auth_method not in ['OIDC', 'Kerberos']:
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


@click.command(context_settings={'help_option_names': ['-h', '--help']})
@click.option('--config-file', '-C', default='/etc/waiverdb/client.conf',
              type=click.Path(exists=True),
              help='Specify a config file to use')
@click.option('--result-id', '-r', multiple=True, type=int,
              help='Specify one or more results to be waived')
@click.option('--product-version', '-p',
              help='Specify one of PDC\'s product version identifiers.')
@click.option('--waived/--no-waived', default=True,
              help='Whether or not the result is waived')
@click.option('--comment', '-c',
              help='A comment explaining why the result is waived')
def cli(comment, waived, product_version, result_id, config_file):
    """
    Creates new waivers against test results.

    Examples:

        waiverdb-cli -r 123 -r 456 -p "fedora-26" -c "It's dead!"

    """
    config = configparser.SafeConfigParser()
    config.read(config_file)
    validate_config(config)

    if not product_version:
        raise click.ClickException('Please specify product version')
    # This name makes more sense for the values of result_id, where as --result-id
    # makes more sense from the cli perspective.
    result_ids = result_id
    if not result_ids:
        raise click.ClickException('Please specify one or more result ids to waive')

    auth_method = config.get('waiverdb', 'auth_method')
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
        for result_id in result_ids:
            data = {
                'result_id': result_id,
                'waived': waived,
                'product_version': product_version,
                'comment': comment
            }
            api_url = config.get('waiverdb', 'api_url')
            scopes = config.get('waiverdb', 'oidc_scopes').strip().splitlines()
            resp = oidc.send_request(
                scopes=scopes,
                url='{0}/waivers/'.format(api_url.rstrip('/')),
                data=json.dumps(data),
                headers={'Content-Type': 'application/json'},
                timeout=60)
            if not resp.ok:
                try:
                    error_msg = resp.json()['message']
                except (ValueError, KeyError):
                    error_msg = resp.text
                raise click.ClickException(
                    'Failed to create waiver for result {0}:\n{1}'
                    .format(result_id, error_msg))
            click.echo('Created waiver {0} for result {1}'.format(
                resp.json()['id'], result_id))
    elif auth_method == 'Kerberos':
        # Try to import this now so the user gets immediate feedback if
        # it isn't installed
        try:
            import requests_kerberos  # noqa: F401
        except ImportError:
            raise click.ClickException('python-requests-kerberos needs to be installed')
        auth = requests_kerberos.HTTPKerberosAuth(mutual_authentication=requests_kerberos.OPTIONAL)
        for result_id in result_ids:
            data = {
                'result_id': result_id,
                'waived': waived,
                'product_version': product_version,
                'comment': comment
            }
            api_url = config.get('waiverdb', 'api_url')
            resp = requests.request('POST', '{0}/waivers/'.format(api_url.rstrip('/')),
                                    data=json.dumps(data), auth=auth,
                                    headers={'Content-Type': 'application/json'},
                                    timeout=60)
            if resp.status_code == 401:
                raise click.ClickException('WaiverDB authentication using Kerberos failed. '
                                           'Make sure you have a valid Kerberos ticket.')
            if not resp.ok:
                try:
                    error_msg = resp.json()['message']
                except (ValueError, KeyError):
                    error_msg = resp.text
                raise click.ClickException(
                    'Failed to create waiver for result {0}:\n{1}'
                    .format(result_id, error_msg))
            click.echo('Created waiver {0} for result {1}'.format(
                resp.json()['id'], result_id))


if __name__ == '__main__':
    cli()  # pylint: disable=E1120