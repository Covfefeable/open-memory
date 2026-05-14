"""Add unlocked memory compression index

Revision ID: 8f1a2c3d4e5f
Revises: 119cd6574994
Create Date: 2026-05-14 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '8f1a2c3d4e5f'
down_revision = '119cd6574994'
branch_labels = None
depends_on = None


def upgrade():
    op.create_index(
        'ix_memories_unlocked_user_created_at',
        'memories',
        ['user_id', 'created_at'],
        unique=False,
        postgresql_where=sa.text('locked = false'),
    )


def downgrade():
    op.drop_index(
        'ix_memories_unlocked_user_created_at',
        table_name='memories',
        postgresql_where=sa.text('locked = false'),
    )
