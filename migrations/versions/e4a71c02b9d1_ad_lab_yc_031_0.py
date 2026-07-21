"""AD security lab YC-031.0 — ad_custom_domains + certificates.required_labs

Revision ID: e4a71c02b9d1
Revises: d200bdfd207d
Create Date: 2026-07-21 04:20:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'e4a71c02b9d1'
down_revision = 'd200bdfd207d'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'ad_custom_domains',
        sa.Column('key', sa.String(length=64), nullable=False),
        sa.Column('name', sa.String(length=120), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('definition_json', sa.Text(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('created_by', sa.Integer(), nullable=True),
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'],
                                ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    with op.batch_alter_table('ad_custom_domains', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_ad_custom_domains_key'),
                              ['key'], unique=True)

    with op.batch_alter_table('certificates', schema=None) as batch_op:
        batch_op.add_column(
            sa.Column('required_labs', sa.Text(), nullable=True))


def downgrade():
    with op.batch_alter_table('certificates', schema=None) as batch_op:
        batch_op.drop_column('required_labs')

    with op.batch_alter_table('ad_custom_domains', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_ad_custom_domains_key'))
    op.drop_table('ad_custom_domains')
