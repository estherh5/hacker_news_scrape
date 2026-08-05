"""Add rollup tables and feed.rolled_up

Permanent aggregate history so the 'all' time period keeps answering after raw
comments and feed links are pruned to a rolling window.

Revision ID: b8c04e7a1d52
Revises: f4b90c1e2a77
Create Date: 2026-08-05 16:05:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic
revision = 'b8c04e7a1d52'
down_revision = 'f4b90c1e2a77'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('feed_summary',
        sa.Column('feed_id', sa.Integer(), nullable=False),
        sa.Column('post_row_count', sa.Integer(), nullable=False),
        sa.Column('sum_point_count', sa.Integer(), nullable=False),
        sa.Column('sum_comment_count', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['feed_id'], ['feed.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('feed_id'))

    op.create_table('comment_daily_total',
        sa.Column('day', sa.Date(), nullable=False),
        sa.Column('comment_count', sa.Integer(), nullable=False),
        sa.Column('sum_level', sa.Integer(), nullable=False),
        sa.Column('sum_word_count', sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint('day'))

    op.create_table('word_total',
        sa.Column('word', sa.TEXT(), nullable=False),
        sa.Column('ndoc', sa.Integer(), nullable=False),
        sa.Column('nentry', sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint('word'))

    op.create_table('user_total',
        sa.Column('username', sa.TEXT(), nullable=False),
        sa.Column('comment_count', sa.Integer(), nullable=False),
        sa.Column('word_count', sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint('username'))

    op.create_table('post_stat',
        sa.Column('post_id', sa.Integer(), nullable=False),
        sa.Column('max_comment_count', sa.Integer(), nullable=False),
        sa.Column('max_point_count', sa.Integer(), nullable=False),
        sa.Column('best_feed_rank', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['post_id'], ['post.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('post_id'))

    op.create_table('pinned_comment',
        sa.Column('comment_id', sa.Integer(), nullable=False),
        sa.Column('reason', sa.TEXT(), nullable=False),
        sa.ForeignKeyConstraint(['comment_id'], ['comment.id'],
            ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('comment_id'))

    op.add_column('feed', sa.Column('rolled_up', sa.Boolean(),
        nullable=False, server_default='false'))

    # Partial index so the nightly job finds its work without scanning every
    # feed ever recorded
    op.create_index('feed_pending_rollup_index', 'feed', ['created'],
        unique=False, postgresql_where=sa.text('NOT rolled_up'))


def downgrade():
    op.drop_index('feed_pending_rollup_index', table_name='feed')
    op.drop_column('feed', 'rolled_up')
    op.drop_table('pinned_comment')
    op.drop_table('post_stat')
    op.drop_table('user_total')
    op.drop_table('word_total')
    op.drop_table('comment_daily_total')
    op.drop_table('feed_summary')
