"""Drop indexes made redundant by their tables' primary keys

Each dropped index leads with the column(s) already covered by its table's
primary key, so it can't serve a lookup the primary key doesn't. EXPLAIN
confirmed the planner ignores them: queries filtering feed_comment by feed_id
sequentially scan the table, because both the index and the primary key lead
with comment_id.

feed_post_index is deliberately kept -- it leads with comment_count, which the
highest-comment-count queries order by.

Revision ID: c7e21f0b4d38
Revises: 3a45b3d1ba9a
Create Date: 2026-08-05 12:41:00.000000

"""
from alembic import op


# revision identifiers, used by Alembic
revision = 'c7e21f0b4d38'
down_revision = '3a45b3d1ba9a'
branch_labels = None
depends_on = None


def upgrade():
    # 170 MB: duplicates feed_comment_pkey (comment_id, feed_id)
    op.drop_index('feed_comment_index', table_name='feed_comment')
    # 22 MB: leads with id, which is the primary key
    op.drop_index('comment_index', table_name='comment')
    # 56 kB: duplicates feed_pkey (id) exactly
    op.drop_index('feed_id_index', table_name='feed')


def downgrade():
    op.create_index('feed_id_index', 'feed', ['id'], unique=False)
    op.create_index('comment_index', 'comment',
        ['id', 'level', 'parent_comment', 'post_id', 'total_word_count',
         'username'], unique=False)
    op.create_index('feed_comment_index', 'feed_comment',
        ['comment_id', 'feed_id', 'feed_rank'], unique=False)
