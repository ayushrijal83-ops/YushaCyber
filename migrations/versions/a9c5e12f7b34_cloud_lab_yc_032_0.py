"""Cloud security lab YC-032.0 — cloud_custom_scenarios

Revision ID: a9c5e12f7b34
Revises: e4a71c02b9d1
Create Date: 2026-07-21 06:10:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a9c5e12f7b34'
down_revision = 'e4a71c02b9d1'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'cloud_custom_scenarios',
        sa.Column('key', sa.String(length=64), nullable=False),
        sa.Column('name', sa.String(length=120), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('definition_json', sa.Text(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('created_by', sa.Integer(), nullable=True),
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'],
                                ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    with op.batch_alter_table('cloud_custom_scenarios', schema=None) \
            as batch_op:
        batch_op.create_index(batch_op.f('ix_cloud_custom_scenarios_key'),
                              ['key'], unique=True)


def downgrade():
    with op.batch_alter_table('cloud_custom_scenarios', schema=None) \
            as batch_op:
        batch_op.drop_index(batch_op.f('ix_cloud_custom_scenarios_key'))
    op.drop_table('cloud_custom_scenarios')
