"""Stop comment deletion cascading to child comments

comment.parent_comment was ON DELETE CASCADE, so pruning an aged-out parent
silently deleted its children too -- without merging them into the rollups
first. A full backfill rehearsal against the production dataset lost 1,143
documents from comment_words that way, and shifted the all-time average word
count by a whole word.

SET NULL keeps the child and drops only the broken link, which is the honest
representation: the parent has been pruned. The deepest-tree pins already keep
whole ancestor chains alive, so the one tree that needs its parents keeps them.

Revision ID: e91b4d7c2a08
Revises: d5a71c93e04f
Create Date: 2026-08-05 17:35:00.000000

"""
from alembic import op


# revision identifiers, used by Alembic
revision = 'e91b4d7c2a08'
down_revision = 'd5a71c93e04f'
branch_labels = None
depends_on = None


def upgrade():
    op.drop_constraint('comment_parent_comment_fkey', 'comment',
        type_='foreignkey')

    op.create_foreign_key('comment_parent_comment_fkey', 'comment', 'comment',
        ['parent_comment'], ['id'], ondelete='SET NULL')


def downgrade():
    op.drop_constraint('comment_parent_comment_fkey', 'comment',
        type_='foreignkey')

    op.create_foreign_key('comment_parent_comment_fkey', 'comment', 'comment',
        ['parent_comment'], ['id'], ondelete='CASCADE')
