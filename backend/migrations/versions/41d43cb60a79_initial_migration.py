"""Initial migration

Revision ID: 41d43cb60a79
Revises: 
Create Date: 2025-02-09 13:43:44.886302

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '41d43cb60a79'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # Add user_email with a default value for existing rows
    op.add_column('journal_entry', sa.Column('user_email', sa.String(), nullable=True, server_default='default@example.com'))

    # Remove the default value after applying it to existing rows
    op.alter_column('journal_entry', 'user_email', server_default=None, nullable=False)


def downgrade():
    # Reverse the migration
    op.drop_column('journal_entry', 'user_email')

    # ### end Alembic commands ###
