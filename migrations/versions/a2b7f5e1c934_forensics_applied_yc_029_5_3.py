"""Forensics applied lab YC-029.5.3

Revision ID: a2b7f5e1c934
Revises: f3a5c1d84720
Create Date: 2026-07-22 09:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a2b7f5e1c934'
down_revision = 'f3a5c1d84720'
branch_labels = None
depends_on = None


def upgrade():
    # ---- new artifact source table ----
    op.create_table(
        'forensics_artifacts',
        sa.Column('case_id', sa.Integer(), nullable=False),
        sa.Column('source_type', sa.String(length=30), nullable=False),
        sa.Column('at_time', sa.String(length=40), nullable=False),
        sa.Column('data_json', sa.Text(), nullable=False,
                  server_default='{}'),
        sa.Column('is_key', sa.Boolean(), nullable=False,
                  server_default=sa.false()),
        sa.Column('sort_order', sa.Integer(), nullable=False,
                  server_default='0'),
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['case_id'], ['forensics_cases.id'],
                                ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    with op.batch_alter_table('forensics_artifacts', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_forensics_artifacts_case_id'),
                              ['case_id'], unique=False)
        batch_op.create_index(
            batch_op.f('ix_forensics_artifacts_source_type'),
            ['source_type'], unique=False)
        batch_op.create_index(batch_op.f('ix_forensics_artifacts_at_time'),
                              ['at_time'], unique=False)
        batch_op.create_index(batch_op.f('ix_forensics_artifacts_sort_order'),
                              ['sort_order'], unique=False)

    # ---- forensics_cases.mode ----
    with op.batch_alter_table('forensics_cases', schema=None) as batch_op:
        batch_op.add_column(sa.Column(
            'mode', sa.String(length=20), nullable=False,
            server_default='fundamentals'))


def downgrade():
    with op.batch_alter_table('forensics_cases', schema=None) as batch_op:
        batch_op.drop_column('mode')
    op.drop_table('forensics_artifacts')
