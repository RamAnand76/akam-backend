"""analytics_and_backups

Revision ID: 0003
Revises: 0002
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = '0003'
down_revision = '0002'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. analytics_events
    op.create_table(
        'analytics_events',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('anon_id', sa.String(length=36), nullable=False),
        sa.Column('app_version', sa.String(length=32), nullable=False),
        sa.Column('event_name', sa.String(length=64), nullable=False),
        sa.Column('event_timestamp', sa.DateTime(timezone=True), nullable=False),
        sa.Column('properties', sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), 'postgresql'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_analytics_events_anon_id'), 'analytics_events', ['anon_id'], unique=False)
    op.create_index(op.f('ix_analytics_events_event_name'), 'analytics_events', ['event_name'], unique=False)

    # 2. user_backups
    op.create_table(
        'user_backups',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('user_id', sa.String(length=36), nullable=False),
        sa.Column('version', sa.Integer(), nullable=False),
        sa.Column('sha256', sa.String(length=64), nullable=False),
        sa.Column('size_bytes', sa.Integer(), nullable=False),
        sa.Column('storage_path', sa.String(length=512), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_user_backups_user_id'), 'user_backups', ['user_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_user_backups_user_id'), table_name='user_backups')
    op.drop_table('user_backups')
    op.drop_index(op.f('ix_analytics_events_event_name'), table_name='analytics_events')
    op.drop_index(op.f('ix_analytics_events_anon_id'), table_name='analytics_events')
    op.drop_table('analytics_events')
