"""Mark feeds whose comment links have been thinned

Hourly scraping filled the 8-day window with ~200 feeds of ~10k comment links
each, and feed_comment reached 233 MB of a 400 MB budget (Neon free: 0.5 GB).
retention.thin_old_feeds drops the redundant links of most feeds once they are
past the 'day' window; this flag lets it skip feeds it has already done.

Revision ID: a3c6e8f20d15
Revises: e91b4d7c2a08
Create Date: 2026-11-18 18:30:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic
revision = 'a3c6e8f20d15'
down_revision = 'e91b4d7c2a08'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('feed', sa.Column('links_thinned', sa.Boolean(),
        nullable=False, server_default='false'))


def downgrade():
    op.drop_column('feed', 'links_thinned')
