"""SOC Case Management YC-030.3.5

Revision ID: e5b9a3d27f14
Revises: d4a8f2c16e93
Create Date: 2026-07-25 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = 'e5b9a3d27f14'
down_revision = 'd4a8f2c16e93'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'soc_cases',
        sa.Column('case_code', sa.String(length=60), nullable=False),
        sa.Column('title', sa.String(length=200), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False,
                  server_default='new'),
        sa.Column('severity', sa.String(length=20), nullable=False,
                  server_default='medium'),
        sa.Column('assigned_analyst', sa.String(length=80),
                  nullable=True),
        sa.Column('closed_at', sa.String(length=40), nullable=True),
        sa.Column('linked_alert_codes_json', sa.Text(), nullable=False,
                  server_default='[]'),
        sa.Column('linked_evidence_json', sa.Text(), nullable=False,
                  server_default='[]'),
        sa.Column('progress', sa.Integer(), nullable=False,
                  server_default='0'),
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True),
                  nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True),
                  nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('case_code'),
    )
    with op.batch_alter_table('soc_cases', schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f('ix_soc_cases_case_code'),
            ['case_code'], unique=True)
        batch_op.create_index(
            batch_op.f('ix_soc_cases_status'),
            ['status'], unique=False)
        batch_op.create_index(
            batch_op.f('ix_soc_cases_severity'),
            ['severity'], unique=False)

    op.create_table(
        'soc_case_notes',
        sa.Column('soc_case_id', sa.Integer(), nullable=False),
        sa.Column('author', sa.String(length=80), nullable=False,
                  server_default='analyst'),
        sa.Column('text', sa.Text(), nullable=False),
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True),
                  nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True),
                  nullable=False),
        sa.ForeignKeyConstraint(['soc_case_id'], ['soc_cases.id'],
                                ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    with op.batch_alter_table('soc_case_notes', schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f('ix_soc_case_notes_soc_case_id'),
            ['soc_case_id'], unique=False)


def downgrade():
    op.drop_table('soc_case_notes')
    op.drop_table('soc_cases')
