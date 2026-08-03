"""Live Classroom YC-033.0

Revision ID: b8c2d3e4f567
Revises: a7d1e5f49b23
Create Date: 2026-08-01 10:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = 'b8c2d3e4f567'
down_revision = 'a7d1e5f49b23'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'live_classes',
        sa.Column('title', sa.String(200), nullable=False),
        sa.Column('slug', sa.String(100), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('instructor_id', sa.Integer(), nullable=False),
        sa.Column('category', sa.String(50), nullable=False,
                  server_default='general'),
        sa.Column('difficulty', sa.String(20), nullable=False,
                  server_default='Easy'),
        sa.Column('start_time', sa.DateTime(timezone=True), nullable=True),
        sa.Column('end_time', sa.DateTime(timezone=True), nullable=True),
        sa.Column('timezone', sa.String(50), nullable=False,
                  server_default='UTC'),
        sa.Column('meeting_provider', sa.String(30), nullable=False,
                  server_default='jitsi'),
        sa.Column('meeting_url', sa.String(500), nullable=True),
        sa.Column('meeting_room', sa.String(100), nullable=True),
        sa.Column('capacity', sa.Integer(), nullable=False,
                  server_default='30'),
        sa.Column('visibility', sa.String(20), nullable=False,
                  server_default='public'),
        sa.Column('status', sa.String(20), nullable=False,
                  server_default='draft'),
        sa.Column('recurring_rule', sa.String(200), nullable=True),
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['instructor_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('slug'),
    )
    with op.batch_alter_table('live_classes') as batch_op:
        batch_op.create_index('ix_live_classes_slug', ['slug'], unique=True)
        batch_op.create_index('ix_live_classes_status', ['status'])
        batch_op.create_index('ix_live_classes_instructor', ['instructor_id'])

    op.create_table(
        'live_enrollments',
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('class_id', sa.Integer(), nullable=False),
        sa.Column('attendance_status', sa.String(20), nullable=False,
                  server_default='registered'),
        sa.Column('joined_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('left_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('attendance_duration', sa.Integer(), nullable=True),
        sa.Column('certificate_eligible', sa.Boolean(), nullable=False,
                  server_default='0'),
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'],
                                ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['class_id'], ['live_classes.id'],
                                ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'class_id', name='uq_enrollment'),
    )
    with op.batch_alter_table('live_enrollments') as batch_op:
        batch_op.create_index('ix_enrollment_user', ['user_id'])
        batch_op.create_index('ix_enrollment_class', ['class_id'])

    op.create_table(
        'live_class_resources',
        sa.Column('class_id', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(200), nullable=False),
        sa.Column('filename', sa.String(255), nullable=True),
        sa.Column('resource_type', sa.String(30), nullable=False,
                  server_default='document'),
        sa.Column('url', sa.String(500), nullable=True),
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['class_id'], ['live_classes.id'],
                                ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    with op.batch_alter_table('live_class_resources') as batch_op:
        batch_op.create_index('ix_resource_class', ['class_id'])


def downgrade():
    op.drop_table('live_class_resources')
    op.drop_table('live_enrollments')
    op.drop_table('live_classes')
