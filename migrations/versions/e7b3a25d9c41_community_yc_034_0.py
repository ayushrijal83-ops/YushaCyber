"""Teams, classrooms & community YC-034.0

Revision ID: e7b3a25d9c41
Revises: c4e8b91d6f27
Create Date: 2026-07-21 12:40:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'e7b3a25d9c41'
down_revision = 'c4e8b91d6f27'
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
        'teams',
        sa.Column('name', sa.String(length=60), nullable=False),
        sa.Column('slug', sa.String(length=80), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('logo', sa.String(length=10), nullable=False),
        sa.Column('is_open', sa.Boolean(), nullable=False),
        sa.Column('captain_id', sa.Integer(), nullable=True),
        *_base_columns(),
        sa.ForeignKeyConstraint(['captain_id'], ['users.id'],
                                ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name'),
        sa.UniqueConstraint('slug'),
    )
    with op.batch_alter_table('teams', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_teams_slug'), ['slug'],
                              unique=True)
        batch_op.create_index(batch_op.f('ix_teams_captain_id'),
                              ['captain_id'], unique=False)

    op.create_table(
        'team_members',
        sa.Column('team_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('joined_at', sa.DateTime(timezone=True), nullable=True),
        *_base_columns(),
        sa.ForeignKeyConstraint(['team_id'], ['teams.id'],
                                ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'],
                                ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', name='uq_team_member_user'),
    )
    with op.batch_alter_table('team_members', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_team_members_team_id'),
                              ['team_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_team_members_user_id'),
                              ['user_id'], unique=False)

    op.create_table(
        'team_invites',
        sa.Column('team_id', sa.Integer(), nullable=False),
        sa.Column('inviter_id', sa.Integer(), nullable=False),
        sa.Column('invitee_id', sa.Integer(), nullable=False),
        sa.Column('status', sa.String(length=12), nullable=False),
        *_base_columns(),
        sa.ForeignKeyConstraint(['team_id'], ['teams.id'],
                                ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['inviter_id'], ['users.id'],
                                ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['invitee_id'], ['users.id'],
                                ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('team_id', 'invitee_id',
                            name='uq_team_invite'),
    )
    with op.batch_alter_table('team_invites', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_team_invites_team_id'),
                              ['team_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_team_invites_invitee_id'),
                              ['invitee_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_team_invites_status'),
                              ['status'], unique=False)

    op.create_table(
        'classrooms',
        sa.Column('name', sa.String(length=80), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('teacher_id', sa.Integer(), nullable=False),
        sa.Column('join_code', sa.String(length=12), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        *_base_columns(),
        sa.ForeignKeyConstraint(['teacher_id'], ['users.id'],
                                ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('join_code'),
    )
    with op.batch_alter_table('classrooms', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_classrooms_teacher_id'),
                              ['teacher_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_classrooms_join_code'),
                              ['join_code'], unique=True)

    op.create_table(
        'classroom_members',
        sa.Column('classroom_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        *_base_columns(),
        sa.ForeignKeyConstraint(['classroom_id'], ['classrooms.id'],
                                ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'],
                                ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('classroom_id', 'user_id',
                            name='uq_classroom_member'),
    )
    with op.batch_alter_table('classroom_members', schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f('ix_classroom_members_classroom_id'),
            ['classroom_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_classroom_members_user_id'),
                              ['user_id'], unique=False)

    op.create_table(
        'assignments',
        sa.Column('classroom_id', sa.Integer(), nullable=False),
        sa.Column('subject_type', sa.String(length=12), nullable=False),
        sa.Column('subject_id', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(length=160), nullable=False),
        sa.Column('instructions', sa.Text(), nullable=True),
        sa.Column('due_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_by', sa.Integer(), nullable=True),
        *_base_columns(),
        sa.ForeignKeyConstraint(['classroom_id'], ['classrooms.id'],
                                ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'],
                                ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    with op.batch_alter_table('assignments', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_assignments_classroom_id'),
                              ['classroom_id'], unique=False)

    op.create_table(
        'discussion_threads',
        sa.Column('subject_type', sa.String(length=12), nullable=False),
        sa.Column('subject_id', sa.Integer(), nullable=False),
        sa.Column('author_id', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(length=160), nullable=False),
        sa.Column('body', sa.Text(), nullable=False),
        sa.Column('is_question', sa.Boolean(), nullable=False),
        sa.Column('pinned_reply_id', sa.Integer(), nullable=True),
        *_base_columns(),
        sa.ForeignKeyConstraint(['author_id'], ['users.id'],
                                ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    with op.batch_alter_table('discussion_threads', schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f('ix_discussion_threads_subject_type'),
            ['subject_type'], unique=False)
        batch_op.create_index(
            batch_op.f('ix_discussion_threads_subject_id'),
            ['subject_id'], unique=False)

    op.create_table(
        'discussion_replies',
        sa.Column('thread_id', sa.Integer(), nullable=False),
        sa.Column('author_id', sa.Integer(), nullable=False),
        sa.Column('body', sa.Text(), nullable=False),
        *_base_columns(),
        sa.ForeignKeyConstraint(['thread_id'], ['discussion_threads.id'],
                                ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['author_id'], ['users.id'],
                                ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    with op.batch_alter_table('discussion_replies', schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f('ix_discussion_replies_thread_id'),
            ['thread_id'], unique=False)

    op.create_table(
        'notifications',
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('type', sa.String(length=24), nullable=False),
        sa.Column('title', sa.String(length=160), nullable=False),
        sa.Column('body', sa.String(length=300), nullable=False),
        sa.Column('link', sa.String(length=255), nullable=False),
        sa.Column('is_read', sa.Boolean(), nullable=False),
        *_base_columns(),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'],
                                ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    with op.batch_alter_table('notifications', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_notifications_user_id'),
                              ['user_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_notifications_type'),
                              ['type'], unique=False)
        batch_op.create_index(batch_op.f('ix_notifications_is_read'),
                              ['is_read'], unique=False)

    op.create_table(
        'announcements',
        sa.Column('author_id', sa.Integer(), nullable=True),
        sa.Column('classroom_id', sa.Integer(), nullable=True),
        sa.Column('title', sa.String(length=160), nullable=False),
        sa.Column('body', sa.Text(), nullable=False),
        *_base_columns(),
        sa.ForeignKeyConstraint(['author_id'], ['users.id'],
                                ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['classroom_id'], ['classrooms.id'],
                                ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    with op.batch_alter_table('announcements', schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f('ix_announcements_classroom_id'),
            ['classroom_id'], unique=False)


def downgrade():
    for table in ('announcements', 'notifications', 'discussion_replies',
                  'discussion_threads', 'assignments',
                  'classroom_members', 'classrooms', 'team_invites',
                  'team_members', 'teams'):
        op.drop_table(table)
