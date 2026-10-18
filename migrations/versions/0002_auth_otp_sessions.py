"""auth_otp_sessions

Revision ID: 0002
Revises: 0001
"""
from alembic import op
import sqlalchemy as sa


revision = '0002'
down_revision = '0001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table('otp_codes',
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('email', sa.String(length=320), nullable=False),
    sa.Column('code_hash', sa.String(length=64), nullable=False),
    sa.Column('ip_hash', sa.String(length=64), nullable=False),
    sa.Column('attempts', sa.Integer(), nullable=False),
    sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('consumed_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_otp_codes_email'), 'otp_codes', ['email'], unique=False)
    op.create_index(op.f('ix_otp_codes_ip_hash'), 'otp_codes', ['ip_hash'], unique=False)
    op.create_table('auth_sessions',
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('user_id', sa.String(length=36), nullable=False),
    sa.Column('device_id', sa.String(length=200), nullable=False),
    sa.Column('device_secret_hash', sa.String(length=64), nullable=False),
    sa.Column('revoked_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_auth_sessions_user_id'), 'auth_sessions', ['user_id'], unique=False)
    op.create_table('refresh_tokens',
    sa.Column('jti', sa.String(length=36), nullable=False),
    sa.Column('session_id', sa.String(length=36), nullable=False),
    sa.Column('user_id', sa.String(length=36), nullable=False),
    sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('rotated_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('revoked_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    sa.ForeignKeyConstraint(['session_id'], ['auth_sessions.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('jti')
    )
    op.create_index(op.f('ix_refresh_tokens_session_id'), 'refresh_tokens', ['session_id'], unique=False)
    op.create_index(op.f('ix_refresh_tokens_user_id'), 'refresh_tokens', ['user_id'], unique=False)
    with op.batch_alter_table('users') as batch:
        batch.add_column(sa.Column('email', sa.String(length=320), nullable=True))
        batch.alter_column('device_id', existing_type=sa.String(length=200), nullable=True)
        batch.create_index('ix_users_email', ['email'], unique=True)


def downgrade() -> None:
    with op.batch_alter_table('users') as batch:
        batch.drop_index('ix_users_email')
        batch.alter_column('device_id', existing_type=sa.String(length=200), nullable=False)
        batch.drop_column('email')
    op.drop_index(op.f('ix_refresh_tokens_user_id'), table_name='refresh_tokens')
    op.drop_index(op.f('ix_refresh_tokens_session_id'), table_name='refresh_tokens')
    op.drop_table('refresh_tokens')
    op.drop_index(op.f('ix_auth_sessions_user_id'), table_name='auth_sessions')
    op.drop_table('auth_sessions')
    op.drop_index(op.f('ix_otp_codes_ip_hash'), table_name='otp_codes')
    op.drop_index(op.f('ix_otp_codes_email'), table_name='otp_codes')
    op.drop_table('otp_codes')
