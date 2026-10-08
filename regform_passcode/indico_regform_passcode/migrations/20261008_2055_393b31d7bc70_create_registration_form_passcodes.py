# This file is part of the third-party Indico plugins.
# Copyright (C) 2026 CERN
#
# The third-party Indico plugins are free software; you can
# redistribute them and/or modify them under the terms of the;
# MIT License see the LICENSE file for more details.

"""Create registration form passcodes

Revision ID: 393b31d7bc70
Revises:
Create Date: 2026-10-08 20:55:40.703669
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.sql.ddl import CreateSchema, DropSchema


# revision identifiers, used by Alembic.
revision = '393b31d7bc70'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.execute(CreateSchema('plugin_regform_passcode'))
    op.create_table(
        'passcodes',
        sa.Column('regform_id', sa.Integer(), autoincrement=False, nullable=False),
        sa.Column('passcode', sa.String(), nullable=False),
        sa.Column('version', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['regform_id'], ['event_registration.forms.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('regform_id'),
        schema='plugin_regform_passcode',
    )


def downgrade():
    op.drop_table('passcodes', schema='plugin_regform_passcode')
    op.execute(DropSchema('plugin_regform_passcode'))
