"""Learning analytics YC-033.0 — analytics_events

Revision ID: c4e8b91d6f27
Revises: a9c5e12f7b34
Create Date: 2026-07-21 11:40:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'c4e8b91d6f27'
down_revision = 'a9c5e12f7b34'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'analytics_events',
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('event_type', sa.String(length=40), nullable=False),
        sa.Column('subject_type', sa.String(length=40), nullable=False),
        sa.Column('subject_id', sa.Integer(), nullable=True),
        sa.Column('meta_json', sa.Text(), nullable=False),
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'],
                                ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    with op.batch_alter_table('analytics_events', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_analytics_events_user_id'),
                              ['user_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_analytics_events_event_type'),
                              ['event_type'], unique=False)


def downgrade():
    with op.batch_alter_table('analytics_events', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_analytics_events_event_type'))
        batch_op.drop_index(batch_op.f('ix_analytics_events_user_id'))
    op.drop_table('analytics_events')
