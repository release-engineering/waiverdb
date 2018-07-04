# SPDX-License-Identifier: GPL-2.0+

"""Replace waiver.subject dict with subject_type and subject_identifier

Revision ID: f6bc296ba966
Revises: ce8a1351ecdc
Create Date: 2018-04-24 16:21:42.017640
"""

# revision identifiers, used by Alembic.
revision = 'f6bc296ba966'
down_revision = 'ce8a1351ecdc'

from alembic import op
from sqlalchemy import Column, Text, Integer, null
# These are the "lightweight" SQL expression versions (not using metadata):
from sqlalchemy.sql.expression import table, column, select, update
from waiverdb.models.base import EqualityComparableJSONType
from waiverdb.models.waivers import subject_dict_to_type_identifier, \
    subject_type_identifier_to_dict

def upgrade():
    # Create the columns NULLable first, so that we can populate them
    op.add_column('waiver', Column('subject_identifier', Text, nullable=True))
    op.add_column('waiver', Column('subject_type', Text, nullable=True))

    # Lightweight table definition for producing queries:
    waiver_table = table('waiver',
                         column('id', type_=Integer),
                         column('subject', type_=EqualityComparableJSONType),
                         column('subject_type', type_=Text),
                         column('subject_identifier', type_=Text))

    # Fill in values for the new columns
    connection = op.get_bind()
    rows = connection.execute(select([waiver_table.c.id, waiver_table.c.subject]))
    for waiver_id, subject in rows:
        try:
            subject_type, subject_identifier = subject_dict_to_type_identifier(subject)
        except ValueError:
            # The 'subject' value might be invalid, see: https://pagure.io/waiverdb/issue/210
            # Let's map it to something which is valid but will never match
            # anything Greenwave is looking for.
            # Note that the original, invalid 'subject' value is still
            # preserved in the row in case of downgrade. So we are not losing
            # any data here.
            subject_type, subject_identifier = 'koji_build', ''
        connection.execute(update(waiver_table)
                           .where(waiver_table.c.id == waiver_id)
                           .values(subject_type=subject_type,
                                   subject_identifier=subject_identifier))

    # Now make the columns non-NULLable, and populate indexes
    op.alter_column('waiver', 'subject_type', nullable=False)
    op.alter_column('waiver', 'subject_identifier', nullable=False)
    op.create_index('ix_waiver_subject_identifier', 'waiver', ['subject_identifier'])
    op.create_index('ix_waiver_subject_type', 'waiver', ['subject_type'])
    op.create_index('ix_waiver_subject_type_identifier', 'waiver', ['subject_type', 'subject_identifier'])

    # Make the old column NULLable for newly inserted rows
    # (we keep it around in case of downgrade though)
    op.alter_column('waiver', 'subject', nullable=True)


def downgrade():
    # Lightweight table definition for producing queries:
    waiver_table = table('waiver',
                         column('id', type_=Integer),
                         column('subject', type_=EqualityComparableJSONType),
                         column('subject_type', type_=Text),
                         column('subject_identifier', type_=Text))

    # Fill in the old column for any waivers inserted since the upgrade
    connection = op.get_bind()
    rows = connection.execute(
            select([waiver_table.c.id, waiver_table.c.subject_type, waiver_table.c.subject_identifier])
            .where(waiver_table.c.subject.is_(null())))
    for waiver_id, subject_type, subject_identifier in rows:
        subject = subject_type_identifier_to_dict(subject_type, subject_identifier)
        connection.execute(update(waiver_table)
                           .where(waiver_table.c.id == waiver_id)
                           .values(subject=subject))

    # Drop the new columns
    op.drop_index('ix_waiver_subject_type_identifier', table_name='waiver')
    op.drop_index('ix_waiver_subject_type', table_name='waiver')
    op.drop_index('ix_waiver_subject_identifier', table_name='waiver')
    op.drop_column('waiver', 'subject_type')
    op.drop_column('waiver', 'subject_identifier')

    # Make the old column non-NULLable again
    op.alter_column('waiver', 'subject', nullable=False)
