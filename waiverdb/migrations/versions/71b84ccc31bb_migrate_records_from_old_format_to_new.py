"""migrate records from old format to new.

Revision ID: 71b84ccc31bb
Revises: f2772c2c64a6
Create Date: 2018-02-14 12:04:34.688790

"""

# revision identifiers, used by Alembic.
revision = '71b84ccc31bb'
down_revision = 'f2772c2c64a6'

from alembic import op
# These are the "lightweight" SQL expression versions (not using metadata):
from sqlalchemy.sql.expression import table, column, select, update
from sqlalchemy.sql.sqltypes import Integer, Text

import json
import requests

from waiverdb.api_v1 import get_resultsdb_result


def convert_id_to_subject_and_testcase(result_id):
    try:
        result = get_resultsdb_result(result_id)
    except requests.HTTPError as e:
        if e.response.status_code == 404:
            raise RuntimeError('Result id %s not found in Resultsdb' % (result_id)) from e
        else:
            raise RuntimeError('Failed looking up result in Resultsdb') from e
    except Exception as e:
        raise RuntimeError('Failed looking up result in Resultsdb') from e
    if 'original_spec_nvr' in result['data']:
        subject = {'original_spec_nvr': result['data']['original_spec_nvr'][0]}
    else:
        if result['data']['type'][0] == 'koji_build' or \
           result['data']['type'][0] == 'bodhi_update':
            SUBJECT_KEYS = ['item', 'type']
            subject = dict([(k, v[0]) for k, v in result['data'].items()
                            if k in SUBJECT_KEYS])
        else:
            raise RuntimeError('Unable to determine subject for result id %s' % (result_id))
    testcase = result['testcase']['name']
    return (subject, testcase)


def upgrade():
    # Lightweight table definition for producing UPDATE queries.
    waiver_table = table('waiver',
                         column('id', type_=Integer),
                         column('result_id', type_=Integer),
                         column('subject', type_=Text),
                         column('testcase', type_=Text))
    # Get a session asociated with the alembic upgrade operation.
    connection = op.get_bind()
    rows = connection.execute(select([waiver_table.c.id, waiver_table.c.result_id]))
    for waiver_id, result_id in rows:
        subject, testcase = convert_id_to_subject_and_testcase(result_id)
        connection.execute(update(waiver_table)
                           .where(waiver_table.c.id == waiver_id)
                           .values(subject=json.dumps(subject), testcase=testcase))


def downgrade():
    # It shouldn't be possible to downgrade this change.
    # Because the result_id field will not be populated with data anymore.
    # If the user tries to downgrade "result_id" should be not null once again
    # like in the old version of the schema, but the value is not longer available
    raise RuntimeError('Irreversible migration')
