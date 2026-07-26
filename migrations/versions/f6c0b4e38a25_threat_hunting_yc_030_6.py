"""Threat Hunting YC-030.6

Revision ID: f6c0b4e38a25
Revises: e5b9a3d27f14
Create Date: 2026-07-26 10:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = 'f6c0b4e38a25'
down_revision = 'e5b9a3d27f14'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'soc_hunts',
        sa.Column('slug', sa.String(80), nullable=False),
        sa.Column('title', sa.String(200), nullable=False),
        sa.Column('hypothesis', sa.Text(), nullable=False, server_default=''),
        sa.Column('description', sa.Text(), nullable=False, server_default=''),
        sa.Column('difficulty', sa.String(20), nullable=False, server_default='Expert'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('case_id', sa.Integer(), nullable=True),
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['case_id'], ['forensics_cases.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('slug'),
    )
    with op.batch_alter_table('soc_hunts') as b:
        b.create_index(b.f('ix_soc_hunts_slug'), ['slug'], unique=True)
        b.create_index(b.f('ix_soc_hunts_case_id'), ['case_id'])

    op.create_table(
        'soc_iocs',
        sa.Column('hunt_id', sa.Integer(), nullable=False),
        sa.Column('ioc_type', sa.String(30), nullable=False),
        sa.Column('value', sa.String(300), nullable=False),
        sa.Column('description', sa.Text(), nullable=False, server_default=''),
        sa.Column('is_malicious', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('mitre_technique', sa.String(20), nullable=True),
        sa.Column('display_order', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['hunt_id'], ['soc_hunts.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    with op.batch_alter_table('soc_iocs') as b:
        b.create_index(b.f('ix_soc_iocs_hunt_id'), ['hunt_id'])
        b.create_index(b.f('ix_soc_iocs_ioc_type'), ['ioc_type'])


def downgrade():
    op.drop_table('soc_iocs')
    op.drop_table('soc_hunts')
