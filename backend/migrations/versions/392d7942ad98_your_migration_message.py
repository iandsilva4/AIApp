"""Your migration message

Revision ID: 392d7942ad98
Revises: 
Create Date: 2025-02-09 14:43:40.178393

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '392d7942ad98'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # Add the new column without NOT NULL
    op.add_column('journal_entry', sa.Column('user_email', sa.String(), nullable=True))
    
    # Populate the new column with a default value
    op.execute("UPDATE journal_entry SET user_email = 'default@example.com'")

    # Alter the column to make it NOT NULL
    op.alter_column('journal_entry', 'user_email', nullable=False)

def downgrade():
    # Drop the column in the downgrade
    op.drop_column('journal_entry', 'user_email')

    # ### end Alembic commands ###
