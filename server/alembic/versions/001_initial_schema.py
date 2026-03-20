"""initial schema

Revision ID: 001
Revises: 
Create Date: 2026-03-01

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute('CREATE EXTENSION IF NOT EXISTS "pgcrypto"')
    
    op.create_table(
        'users',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('email', sa.String(255), unique=True, nullable=False),
        sa.Column('ssh_pub_key', sa.Text, nullable=True),
        sa.Column('google_id', sa.String(255), unique=True, nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),
    )
    op.create_index('idx_users_email', 'users', ['email'])
    op.create_index('idx_users_google_id', 'users', ['google_id'])
    
    op.create_table(
        'tunnels',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('slug', sa.String(32), unique=True, nullable=False),
        sa.Column('owner_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('owner_email', sa.String(255), nullable=True),
        sa.Column('assigned_port', sa.Integer, nullable=False),
        sa.Column('local_port', sa.Integer, nullable=False),
        sa.Column('local_url', sa.String(255), nullable=True),
        sa.Column('status', sa.String(16), nullable=False, server_default='pending'),
        sa.Column('ttl_seconds', sa.Integer, nullable=False, server_default='7200'),
        sa.Column('auth_domain', sa.String(255), nullable=True),
        sa.Column('password_hash', sa.String(255), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_active', sa.DateTime(timezone=True), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('fault_injection', postgresql.JSONB, nullable=True),
        sa.Column('blocked_countries', postgresql.ARRAY(sa.String(2)), server_default='{}'),
        sa.Column('total_requests', sa.Integer, server_default='0'),
        sa.Column('total_bytes', sa.BigInteger, server_default='0'),
    )
    op.create_index('idx_tunnels_slug', 'tunnels', ['slug'])
    op.create_index('idx_tunnels_status', 'tunnels', ['status'])
    op.create_index('idx_tunnels_owner_id', 'tunnels', ['owner_id'])
    
    op.create_table(
        'request_logs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('tunnel_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('tunnels.id', ondelete='CASCADE'), nullable=False),
        sa.Column('method', sa.String(10), nullable=False),
        sa.Column('path', sa.Text, nullable=False),
        sa.Column('query_params', postgresql.JSONB, server_default='{}'),
        sa.Column('req_headers', postgresql.JSONB, server_default='{}'),
        sa.Column('req_body', sa.Text, nullable=True),
        sa.Column('status_code', sa.Integer, nullable=True),
        sa.Column('res_headers', postgresql.JSONB, server_default='{}'),
        sa.Column('res_body', sa.Text, nullable=True),
        sa.Column('latency_ms', sa.Integer, nullable=True),
        sa.Column('visitor_ip', sa.String(45), nullable=True),
        sa.Column('country_code', sa.String(2), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),
    )
    op.create_index('idx_request_logs_tunnel_id', 'request_logs', ['tunnel_id'])
    op.create_index('idx_request_logs_created_at', 'request_logs', ['created_at'])
    op.create_index('idx_request_logs_status_code', 'request_logs', ['status_code'])
    
    op.create_table(
        'tunnel_stats',
        sa.Column('tunnel_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('tunnels.id', ondelete='CASCADE'), primary_key=True),
        sa.Column('total_requests', sa.Integer, server_default='0'),
        sa.Column('unique_ips', sa.Integer, server_default='0'),
        sa.Column('total_bytes', sa.BigInteger, server_default='0'),
        sa.Column('avg_latency_ms', sa.Integer, server_default='0'),
        sa.Column('country_breakdown', postgresql.JSONB, server_default='{}'),
        sa.Column('method_breakdown', postgresql.JSONB, server_default='{}'),
        sa.Column('status_breakdown', postgresql.JSONB, server_default='{}'),
        sa.Column('peak_rps', sa.Integer, server_default='0'),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),
    )
    
    op.execute('''
        CREATE OR REPLACE FUNCTION update_updated_at_column()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = NOW();
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    ''')
    op.execute('''
        CREATE TRIGGER set_tunnels_updated_at
            BEFORE UPDATE ON tunnels
            FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
    ''')


def downgrade() -> None:
    op.execute('DROP TRIGGER IF EXISTS set_tunnels_updated_at ON tunnels')
    op.execute('DROP FUNCTION IF EXISTS update_updated_at_column()')
    op.drop_table('tunnel_stats')
    op.drop_table('request_logs')
    op.drop_index('idx_tunnels_owner_id', table_name='tunnels')
    op.drop_index('idx_tunnels_status', table_name='tunnels')
    op.drop_index('idx_tunnels_slug', table_name='tunnels')
    op.drop_table('tunnels')
    op.drop_index('idx_users_google_id', table_name='users')
    op.drop_index('idx_users_email', table_name='users')
    op.drop_table('users')
