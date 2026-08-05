"""Index feed_comment by feed_id

Every stats query filters feed_comment by feed_id, but the primary key leads
with comment_id, so none of them could use it -- each one sequentially scanned
all 5.6M rows. EXPLAIN ANALYZE on a representative counting query, measured
with fresh planner statistics:

    no index                    625 ms     0 MB
    (feed_id)                  ~210 ms    38 MB
    (feed_id, comment_id)      ~129 ms   121 MB

The plan uses a bitmap heap scan either way, so the composite's comment_id
column buys only ~80 ms for an extra 83 MB. Single column wins on this
database, which is storage-constrained.

Revision ID: f4b90c1e2a77
Revises: c7e21f0b4d38
Create Date: 2026-08-05 13:02:00.000000

"""
from alembic import op


# revision identifiers, used by Alembic
revision = 'f4b90c1e2a77'
down_revision = 'c7e21f0b4d38'
branch_labels = None
depends_on = None


def upgrade():
    op.create_index('feed_comment_feed_id_index', 'feed_comment', ['feed_id'],
        unique=False)


def downgrade():
    op.drop_index('feed_comment_feed_id_index', table_name='feed_comment')
