# SPDX-License-Identifier: GPL-2.0+

from alembic import op
from flask_migrate import upgrade
from mock import patch
from pytest import fixture
from waiverdb.models import db


@fixture
def mock_alter_column():
    """SQLite does not support ALTER COLUMN, mock it to use batch operations."""
    if "sqlite" not in str(db.engine.url).lower():
        return

    with patch.object(op, 'alter_column') as mock_alter:
        def alter_column_mock(table, column, **kwargs):
            with op.batch_alter_table(table, schema=None) as batch_op:
                batch_op.alter_column(column, **kwargs)

        mock_alter.side_effect = alter_column_mock
        yield mock_alter


def test_migrations_upgrade(app, mock_alter_column):
    with app.app_context():
        db.drop_all()
        upgrade()
