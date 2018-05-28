"""Drop user_content_counts table

Revision ID: 3a45b3d1ba9a
Revises: a8da7af96d12
Create Date: 2018-05-29 18:59:02.356758

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic
revision = '3a45b3d1ba9a'
down_revision = 'a8da7af96d12'
branch_labels = None
depends_on = None


def upgrade():
    op.drop_index('user_content_index', table_name='user_content_counts')
    op.drop_table('user_content_counts')


def downgrade():
    op.create_table('user_content_counts',
        sa.Column('feed_id', sa.INTEGER(), autoincrement=False,
            nullable=False),
        sa.Column('username', sa.TEXT(), autoincrement=False, nullable=False),
        sa.Column('comment_count', sa.INTEGER(), autoincrement=False,
            nullable=True),
        sa.Column('word_count', sa.INTEGER(), autoincrement=False,
            nullable=True),
        sa.ForeignKeyConstraint(['feed_id'], ['feed.id'],
            name='user_content_counts_feed_id_fkey'),
        sa.PrimaryKeyConstraint('feed_id', 'username',
            name='user_content_counts_pkey')
    )
    op.create_index('user_content_index', 'user_content_counts',
        ['comment_count', 'feed_id', 'username', 'word_count'], unique=False)
