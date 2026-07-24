"""SOC Alert Investigation YC-030.2

Revision ID: d4a8f2c16e93
Revises: c9f2e1a83b45
Create Date: 2026-07-24 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = 'd4a8f2c16e93'
down_revision = 'c9f2e1a83b45'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('soc_alerts', schema=None) as batch_op:
        batch_op.add_column(sa.Column(
            'expected_classification', sa.String(length=20),
            nullable=True))
        batch_op.add_column(sa.Column(
            'expected_root_cause', sa.String(length=200),
            nullable=True))


def downgrade():
    with op.batch_alter_table('soc_alerts', schema=None) as batch_op:
        batch_op.drop_column('expected_root_cause')
        batch_op.drop_column('expected_classification')
