"""Forensics advanced lab YC-029.5.4

Revision ID: b8e4d9270fa1
Revises: a2b7f5e1c934
Create Date: 2026-07-22 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'b8e4d9270fa1'
down_revision = 'a2b7f5e1c934'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'forensics_suspects',
        sa.Column('case_id', sa.Integer(), nullable=False),
        sa.Column('slug', sa.String(length=60), nullable=False),
        sa.Column('display_name', sa.String(length=120), nullable=False),
        sa.Column('role', sa.String(length=120), nullable=False),
        sa.Column('account', sa.String(length=80), nullable=False),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('is_key', sa.Boolean(), nullable=False,
                  server_default=sa.false()),
        sa.Column('display_order', sa.Integer(), nullable=False,
                  server_default='0'),
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['case_id'], ['forensics_cases.id'],
                                ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('case_id', 'slug',
                            name='uq_forensics_suspect_slug'),
    )
    with op.batch_alter_table('forensics_suspects', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_forensics_suspects_case_id'),
                              ['case_id'], unique=False)
        batch_op.create_index(
            batch_op.f('ix_forensics_suspects_display_order'),
            ['display_order'], unique=False)


def downgrade():
    op.drop_table('forensics_suspects')
