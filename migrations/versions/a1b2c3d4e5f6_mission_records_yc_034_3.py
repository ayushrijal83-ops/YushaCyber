"""Mission records YC-034.3

Revision ID: a1b2c3d4e5f6
Revises: b8c2d3e4f567
Create Date: 2026-08-08 00:00:00.000000

"""
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = 'a1b2c3d4e5f6'
down_revision = 'b8c2d3e4f567'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'mission_records',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('mission_id', sa.String(length=64), nullable=False),
        sa.Column('status', sa.String(length=16), nullable=False),
        sa.Column('objectives_completed', sa.Integer(), nullable=False),
        sa.Column('objectives_total', sa.Integer(), nullable=False),
        sa.Column('xp_earned', sa.Integer(), nullable=False),
        sa.Column('hints_used', sa.Integer(), nullable=False),
        sa.Column('attempts', sa.Integer(), nullable=False),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'mission_id', name='uq_mission_record_user_mission'),
    )
    with op.batch_alter_table('mission_records', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_mission_records_user_id'),
                              ['user_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_mission_records_mission_id'),
                              ['mission_id'], unique=False)


def downgrade():
    op.drop_table('mission_records')
