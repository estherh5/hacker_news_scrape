"""Index comment.parent_comment

comment.parent_comment is a self-referencing foreign key with ON DELETE
CASCADE and no index, so every comment deletion sequentially scanned the whole
comment table looking for children. Measured against the production dataset,
deleting 1,123 comments took 84 seconds; the retention job deletes comments on
every run.

Revision ID: d5a71c93e04f
Revises: b8c04e7a1d52
Create Date: 2026-08-05 17:05:00.000000

"""
from alembic import op


# revision identifiers, used by Alembic
revision = 'd5a71c93e04f'
down_revision = 'b8c04e7a1d52'
branch_labels = None
depends_on = None


def upgrade():
    op.create_index('comment_parent_comment_index', 'comment',
        ['parent_comment'], unique=False)


def downgrade():
    op.drop_index('comment_parent_comment_index', table_name='comment')
