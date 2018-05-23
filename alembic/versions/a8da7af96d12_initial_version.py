"""Initial version

Revision ID: a8da7af96d12
Revises:
Create Date: 2018-05-29 18:23:49.305548

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic
revision = 'a8da7af96d12'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('feed',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('created', sa.TIMESTAMP(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('feed_id_index', 'feed', ['id'], unique=False)
    op.create_table('post',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('created', sa.TIMESTAMP(), nullable=False),
        sa.Column('link', sa.TEXT(), nullable=False),
        sa.Column('title', sa.TEXT(), nullable=False),
        sa.Column('type',
            sa.Enum('article', 'ask', 'job', 'show', name='post_type'),
            nullable=False),
        sa.Column('username', sa.TEXT(), nullable=True),
        sa.Column('website', sa.TEXT(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('post_index', 'post', ['id', 'username'], unique=False)
    op.create_table('comment',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('content', sa.TEXT(), nullable=False),
        sa.Column('created', sa.TIMESTAMP(), nullable=False),
        sa.Column('level', sa.Integer(), nullable=False),
        sa.Column('parent_comment', sa.Integer(), nullable=True),
        sa.Column('post_id', sa.Integer(), nullable=False),
        sa.Column('total_word_count', sa.Integer(), nullable=False),
        sa.Column('username', sa.TEXT(), nullable=False),
        sa.Column('word_counts', postgresql.TSVECTOR(), nullable=False),
        sa.ForeignKeyConstraint(['parent_comment'], ['comment.id'],
            ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['post_id'], ['post.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('comment_index', 'comment',
        ['id', 'level', 'parent_comment', 'post_id', 'total_word_count',
        'username'], unique=False)
    op.create_table('feed_post',
        sa.Column('feed_id', sa.Integer(), nullable=False),
        sa.Column('post_id', sa.Integer(), nullable=False),
        sa.Column('comment_count', sa.Integer(), nullable=False),
        sa.Column('feed_rank', sa.Integer(), nullable=False),
        sa.Column('point_count', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['feed_id'], ['feed.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['post_id'], ['post.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('feed_id', 'post_id')
    )
    op.create_index('feed_post_index', 'feed_post',
        ['comment_count', 'feed_id', 'feed_rank', 'point_count', 'post_id'],
        unique=False)
    op.create_table('user_content_counts',
        sa.Column('feed_id', sa.Integer(), nullable=False),
        sa.Column('username', sa.TEXT(), nullable=False),
        sa.Column('comment_count', sa.Integer(), nullable=True),
        sa.Column('word_count', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['feed_id'], ['feed.id'], ),
        sa.PrimaryKeyConstraint('feed_id', 'username')
    )
    op.create_index('user_content_index', 'user_content_counts',
        ['comment_count', 'feed_id', 'username', 'word_count'], unique=False)
    op.create_table('feed_comment',
        sa.Column('comment_id', sa.Integer(), nullable=False),
        sa.Column('feed_id', sa.Integer(), nullable=False),
        sa.Column('feed_rank', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['comment_id'], ['comment.id'],
            ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['feed_id'], ['feed.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('comment_id', 'feed_id')
    )
    op.create_index('feed_comment_index', 'feed_comment',
        ['comment_id', 'feed_id', 'feed_rank'], unique=False)


def downgrade():
    op.drop_index('feed_comment_index', table_name='feed_comment')
    op.drop_table('feed_comment')
    op.drop_index('user_content_index', table_name='user_content_counts')
    op.drop_table('user_content_counts')
    op.drop_index('feed_post_index', table_name='feed_post')
    op.drop_table('feed_post')
    op.drop_index('comment_index', table_name='comment')
    op.drop_table('comment')
    op.drop_index('post_index', table_name='post')
    op.drop_table('post')
    op.drop_index('feed_id_index', table_name='feed')
    op.drop_table('feed')
