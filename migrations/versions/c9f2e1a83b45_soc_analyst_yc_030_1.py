"""SOC Analyst Simulator YC-030.1

Revision ID: c9f2e1a83b45
Revises: b8e4d9270fa1
Create Date: 2026-07-22 11:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'c9f2e1a83b45'
down_revision = 'b8e4d9270fa1'
branch_labels = None
depends_on = None


def _base_columns():
    return [
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    ]


def upgrade():
    op.create_table(
        'soc_alerts',
        sa.Column('alert_code', sa.String(length=30), nullable=False),
        sa.Column('title', sa.String(length=200), nullable=False),
        sa.Column('alert_type', sa.String(length=40), nullable=False),
        sa.Column('severity', sa.String(length=15), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False,
                  server_default='open'),
        sa.Column('source', sa.String(length=80), nullable=False,
                  server_default='SIEM'),
        sa.Column('assigned_analyst', sa.String(length=80),
                  nullable=True),
        sa.Column('at_time', sa.String(length=30), nullable=False,
                  server_default=''),
        sa.Column('description', sa.Text(), nullable=False,
                  server_default=''),
        sa.Column('case_id', sa.Integer(), nullable=True),
        *_base_columns(),
        sa.ForeignKeyConstraint(['case_id'], ['forensics_cases.id'],
                                ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('alert_code'),
    )
    with op.batch_alter_table('soc_alerts', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_soc_alerts_alert_code'),
                              ['alert_code'], unique=True)
        batch_op.create_index(batch_op.f('ix_soc_alerts_alert_type'),
                              ['alert_type'], unique=False)
        batch_op.create_index(batch_op.f('ix_soc_alerts_severity'),
                              ['severity'], unique=False)
        batch_op.create_index(batch_op.f('ix_soc_alerts_status'),
                              ['status'], unique=False)
        batch_op.create_index(batch_op.f('ix_soc_alerts_case_id'),
                              ['case_id'], unique=False)

    op.create_table(
        'soc_playbooks',
        sa.Column('alert_type', sa.String(length=40), nullable=False),
        sa.Column('title', sa.String(length=160), nullable=False),
        sa.Column('summary', sa.Text(), nullable=False,
                  server_default=''),
        *_base_columns(),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('alert_type'),
    )
    with op.batch_alter_table('soc_playbooks', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_soc_playbooks_alert_type'),
                              ['alert_type'], unique=True)

    op.create_table(
        'soc_playbook_steps',
        sa.Column('playbook_id', sa.Integer(), nullable=False),
        sa.Column('phase', sa.String(length=20), nullable=False),
        sa.Column('title', sa.String(length=160), nullable=False),
        sa.Column('body', sa.Text(), nullable=False, server_default=''),
        sa.Column('display_order', sa.Integer(), nullable=False,
                  server_default='0'),
        *_base_columns(),
        sa.ForeignKeyConstraint(['playbook_id'], ['soc_playbooks.id'],
                                ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    with op.batch_alter_table('soc_playbook_steps', schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f('ix_soc_playbook_steps_playbook_id'),
            ['playbook_id'], unique=False)
        batch_op.create_index(
            batch_op.f('ix_soc_playbook_steps_phase'),
            ['phase'], unique=False)
        batch_op.create_index(
            batch_op.f('ix_soc_playbook_steps_display_order'),
            ['display_order'], unique=False)

    op.create_table(
        'soc_checklist_items',
        sa.Column('case_id', sa.Integer(), nullable=False),
        sa.Column('slug', sa.String(length=60), nullable=False),
        sa.Column('text', sa.String(length=200), nullable=False),
        sa.Column('is_required', sa.Boolean(), nullable=False,
                  server_default=sa.true()),
        sa.Column('display_order', sa.Integer(), nullable=False,
                  server_default='0'),
        *_base_columns(),
        sa.ForeignKeyConstraint(['case_id'], ['forensics_cases.id'],
                                ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('case_id', 'slug',
                            name='uq_soc_checklist_slug'),
    )
    with op.batch_alter_table('soc_checklist_items', schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f('ix_soc_checklist_items_case_id'),
            ['case_id'], unique=False)
        batch_op.create_index(
            batch_op.f('ix_soc_checklist_items_display_order'),
            ['display_order'], unique=False)


def downgrade():
    op.drop_table('soc_checklist_items')
    op.drop_table('soc_playbook_steps')
    op.drop_table('soc_playbooks')
    op.drop_table('soc_alerts')
