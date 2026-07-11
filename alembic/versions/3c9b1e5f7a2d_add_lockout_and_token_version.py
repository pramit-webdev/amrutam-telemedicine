"""add lockout and token version fields to users

Revision ID: 3c9b1e5f7a2d
Revises: 2a5a19c0a534
Create Date: 2026-07-12 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '3c9b1e5f7a2d'
down_revision: Union[str, None] = '2a5a19c0a534'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('users', sa.Column('failed_login_attempts', sa.Integer(), nullable=False, server_default=sa.text('0')))
    op.add_column('users', sa.Column('locked_until', sa.DateTime(timezone=True), nullable=True))
    op.add_column('users', sa.Column('token_version', sa.Integer(), nullable=False, server_default=sa.text('0')))


def downgrade() -> None:
    op.drop_column('users', 'token_version')
    op.drop_column('users', 'locked_until')
    op.drop_column('users', 'failed_login_attempts')
