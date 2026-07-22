"""Digital forensics YC-029.5.2

Revision ID: f3a5c1d84720
Revises: e7b3a25d9c41
Create Date: 2026-07-22 08:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'f3a5c1d84720'
down_revision = 'e7b3a25d9c41'
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
        'forensics_cases',
        sa.Column('lab_slug', sa.String(length=150), nullable=False),
        sa.Column('title', sa.String(length=160), nullable=False),
        sa.Column('briefing', sa.Text(), nullable=False),
        sa.Column('workstation_name', sa.String(length=80), nullable=False),
        sa.Column('investigator', sa.String(length=80), nullable=False),
        *_base_columns(),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('lab_slug'),
    )
    with op.batch_alter_table('forensics_cases', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_forensics_cases_lab_slug'),
                              ['lab_slug'], unique=True)

    op.create_table(
        'forensics_evidence',
        sa.Column('case_id', sa.Integer(), nullable=False),
        sa.Column('slug', sa.String(length=80), nullable=False),
        sa.Column('kind', sa.String(length=20), nullable=False),
        sa.Column('filename', sa.String(length=160), nullable=False),
        sa.Column('extension', sa.String(length=20), nullable=False),
        sa.Column('owner', sa.String(length=60), nullable=False),
        sa.Column('size_bytes', sa.Integer(), nullable=False),
        sa.Column('created_at_display', sa.String(length=40), nullable=False),
        sa.Column('modified_at_display', sa.String(length=40), nullable=False),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('is_suspicious', sa.Boolean(), nullable=False),
        sa.Column('is_modified', sa.Boolean(), nullable=False),
        sa.Column('display_order', sa.Integer(), nullable=False),
        *_base_columns(),
        sa.ForeignKeyConstraint(['case_id'], ['forensics_cases.id'],
                                ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('case_id', 'slug',
                            name='uq_forensics_evidence_slug'),
    )
    with op.batch_alter_table('forensics_evidence', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_forensics_evidence_case_id'),
                              ['case_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_forensics_evidence_display_order'),
                              ['display_order'], unique=False)

    op.create_table(
        'forensics_timeline_events',
        sa.Column('case_id', sa.Integer(), nullable=False),
        sa.Column('at_time', sa.String(length=8), nullable=False),
        sa.Column('kind', sa.String(length=20), nullable=False),
        sa.Column('description', sa.String(length=200), nullable=False),
        sa.Column('evidence_slug', sa.String(length=80), nullable=True),
        *_base_columns(),
        sa.ForeignKeyConstraint(['case_id'], ['forensics_cases.id'],
                                ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    with op.batch_alter_table('forensics_timeline_events', schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f('ix_forensics_timeline_events_case_id'),
            ['case_id'], unique=False)


def downgrade():
    op.drop_table('forensics_timeline_events')
    op.drop_table('forensics_evidence')
    op.drop_table('forensics_cases')
