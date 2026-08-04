# SPDX-License-Identifier: GPL-2.0+

import time

import click
from flask.cli import FlaskGroup
from sqlalchemy.exc import OperationalError

from waiverdb.app import create_app
from waiverdb.models import db


@click.group(cls=FlaskGroup, create_app=create_app)
def cli():
    pass


@cli.command(name='wait-for-db')
def wait_for_db():
    """
    Wait until database server is reachable.
    """
    poll_interval = 10  # seconds
    while True:
        try:
            db.engine.connect()
        except OperationalError as e:
            click.echo(f'Failed to connect to database: {e}')
            click.echo(f'Sleeping for {poll_interval} seconds...')
            time.sleep(poll_interval)
            click.echo('Retrying...')
        else:
            break


if __name__ == '__main__':
    cli()  # pylint: disable=E1120
