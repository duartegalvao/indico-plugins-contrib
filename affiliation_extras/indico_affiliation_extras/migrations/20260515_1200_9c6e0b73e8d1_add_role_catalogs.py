"""Add role catalogs

Revision ID: 9c6e0b73e8d1
Revises: 053dd42396ff
Create Date: 2026-05-15 12:00:00.000000
"""

import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision = '9c6e0b73e8d1'
down_revision = '053dd42396ff'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'role_catalogs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        schema='plugin_affiliation_extras',
    )
    op.create_table(
        'affiliation_roles',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('catalog_id', sa.Integer(), nullable=False),
        sa.Column('position', sa.Integer(), nullable=False),
        sa.Column('code', sa.String(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.ForeignKeyConstraint(['catalog_id'], ['plugin_affiliation_extras.role_catalogs.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        schema='plugin_affiliation_extras',
    )
    op.create_index(None, 'affiliation_roles', ['catalog_id'], unique=False, schema='plugin_affiliation_extras')
    op.create_index(
        'ix_uq_affiliation_roles_catalog_id_code_lower',
        'affiliation_roles',
        ['catalog_id', sa.text('lower(code)')],
        unique=True,
        schema='plugin_affiliation_extras',
    )
    op.add_column(
        'affiliation_lists',
        sa.Column('role_catalog_id', sa.Integer(), nullable=True),
        schema='plugin_affiliation_extras',
    )
    op.create_index(None, 'affiliation_lists', ['role_catalog_id'], unique=False, schema='plugin_affiliation_extras')
    op.create_foreign_key(
        None,
        'affiliation_lists',
        'role_catalogs',
        ['role_catalog_id'],
        ['id'],
        source_schema='plugin_affiliation_extras',
        referent_schema='plugin_affiliation_extras',
        ondelete='SET NULL',
    )


def downgrade():
    op.drop_column('affiliation_lists', 'role_catalog_id', schema='plugin_affiliation_extras')
    op.drop_table('affiliation_roles', schema='plugin_affiliation_extras')
    op.drop_table('role_catalogs', schema='plugin_affiliation_extras')
