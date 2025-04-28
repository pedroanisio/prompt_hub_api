"""
########################################################################
# AI Prompt Service - migrations/versions/initial_migration.py
# 
# Origin: Created as part of the AI Prompt Service project
# Request: Add Postgres 16, add docker. Endpoint should work ad hoc (AS IS) or with session Mode.
# Version: 1.0.0
# Created: 2025-04-27
# 
# Purpose: Initial database migration to create sessions and messages tables
#
# Dependencies: 
# - alembic
# - sqlalchemy
########################################################################
"""
"""Initial migration

Revision ID: 849e5b0f89d2
Revises: 
Create Date: 2025-04-27 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic
revision = '849e5b0f89d2'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create sessions table
    op.create_table(
        'sessions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('ai_provider', sa.String(50), nullable=False),
        sa.Column('model', sa.String(100), nullable=False),
        sa.Column('system_prompt', sa.Text, nullable=False),
        sa.Column('created_at', sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, nullable=False, server_default=sa.func.now()),
    )
    
    # Create messages table
    op.create_table(
        'messages',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('session_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('role', sa.String(50), nullable=False),
        sa.Column('content', sa.Text, nullable=False),
        sa.Column('created_at', sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column('order', sa.Integer, nullable=False),
        sa.ForeignKeyConstraint(['session_id'], ['sessions.id'], ondelete='CASCADE'),
        sa.Index('ix_messages_session_id', 'session_id')
    )
    
    # Add index for faster session lookup by updated_at (for cleanup)
    op.create_index('ix_sessions_updated_at', 'sessions', ['updated_at'])


def downgrade() -> None:
    # Drop tables
    op.drop_table('messages')
    op.drop_table('sessions')