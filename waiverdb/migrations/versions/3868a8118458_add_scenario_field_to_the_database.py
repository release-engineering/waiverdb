"""Add scenario field to the database

Revision ID: 3868a8118458
Revises: f6bc296ba966
Create Date: 2020-10-20 18:08:50.709804

"""

# revision identifiers, used by Alembic.
revision = '3868a8118458'
down_revision = 'f6bc296ba966'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.add_column('waiver', sa.Column('scenario', sa.String(length=255), nullable=True))


def downgrade():
    op.drop_column('waiver', 'scenario')
