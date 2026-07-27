"""Blue Team Assessment YC-030.7

Revision ID: a7d1e5f49b23
Revises: f6c0b4e38a25
Create Date: 2026-07-27 10:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = 'a7d1e5f49b23'
down_revision = 'f6c0b4e38a25'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'soc_assessment_results',
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('assessment_slug', sa.String(80), nullable=False),
        sa.Column('score', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('max_score', sa.Integer(), nullable=False, server_default='100'),
        sa.Column('grade', sa.String(30), nullable=False, server_default=''),
        sa.Column('completion_seconds', sa.Integer(), nullable=True),
        sa.Column('certificate_id_str', sa.String(40), nullable=True),
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'assessment_slug',
                            name='uq_assessment_result'),
    )
    with op.batch_alter_table('soc_assessment_results') as batch_op:
        batch_op.create_index('ix_soc_assessment_user', ['user_id'])
        batch_op.create_index('ix_soc_assessment_slug', ['assessment_slug'])


def downgrade():
    op.drop_table('soc_assessment_results')
