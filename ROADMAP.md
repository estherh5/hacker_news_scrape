# Roadmap

Committed doc, not scratch. Kept current by hand as work ships.
**Shipped** = live in production. **Next** = intended, not promised.
**Declined** = decided against, with the reason, so it doesn't get re-proposed.
**Open questions** = unresolved calls, with what would settle them.

## Shipped

- **2026-10** **Scraping restarted: hourly, from HN's official API, on GitHub Actions.**
  `hacker_news.py#scrape_loop` now reads `hacker-news.firebaseio.com/v0` (topstories, first 90,
  then each post's comment tree depth-first) instead of parsing the HTML pages. Timestamps are
  exact, every reply records its true parent (the HTML parser attached replies to the first
  comment one level up, and crashed in `.limit(1).one()` when there was none), and a run writes
  in one transaction or not at all; a snapshot under `MIN_POSTS` raises instead of committing an
  empty feed. `.github/workflows/scrape.yml` runs at :07 every hour: scrape, `prune_db` (the
  8-day rollup, unscheduled since Heroku went away), `check_db_size` (fails over 400 MB, against
  Neon free's 0.5 GB cap). Any failed, timed-out or cancelled step reports to flare as app
  `hn-scrape`, and the run re-enables its own schedule so GitHub's 60-day inactivity rule cannot
  switch it off. Hour/day/week API responses now cache for 5 minutes at the edge; `all` keeps the
  1-day cache. A live run takes ~45s for 90 posts and ~13k comments. Website is now the bare
  hostname (no `github.com/<user>` form), and job posts are typed `job` (the old parser stored
  them as `article`).

- **2026-09** **SQLAlchemy pinned below 2.1 (4fc0ba8), deployed with the edge cache.** Production
  serves `49bafb1` on `hn-api.crystalprism.io`, auto-assign back on; a repeat request answers
  `x-vercel-cache: HIT`. Verified 2026-09-30.
- **2026-09** **Security: SQL fragments allowlisted, all-history queries cached at the edge.**
  `all_period_users`, `all_period_posts` and `all_period_average` now take a key into
  `USER_ORDERS` / `POST_ORDERS` / `AVERAGES` in `hacker_news/hacker_news.py` instead of raw SQL,
  so nothing but those dicts is ever formatted into a `text()` query. `server.py#cache_at_edge`
  marks every 200 GET `s-maxage=86400, stale-while-revalidate=604800` (errors are never cached),
  so repeat hits on the expensive all-history queries are served from Vercel's CDN; the archive
  has not changed since scraping stopped in 2024-05. CORS `*` stays: the API is public, read-only
  and credential-free, so an origin list would stop no one who can run `curl`. 128 tests pass.

- **2026-09** **Pushes to `main` deploy.** The Vercel project is now git-connected (production
  branch `main`); before this, only `vercel --prod` deployed it, and a push produced no build.
  The first git build took the API down for ~5 minutes: `SQLAlchemy~=2.0` resolved to 2.1, whose
  default `postgresql://` driver is psycopg 3 (not installed), so every request 500'd. Production
  was rolled back to the 2026-09-01 build, and `requirements.txt` now pins `SQLAlchemy~=2.0.0`
  (4fc0ba8, not yet deployed — see the dated item under `## Next`).

- **2026-09** **Heroku decommissioned.** The `hn-scrape` app, its `essential-0` Postgres add-on
  and its scheduler were destroyed on 2026-09-04 after three days of parallel running with zero
  real traffic (the only post-cutover requests were Googlebot and msnbot hitting the raw
  `hn-scrape.herokuapp.com` hostname). A final pre-destroy dump was taken and row-matched against
  Neon on every table. Two Heroku scheduler jobs died with the app: `management.py backup_db`
  (superseded by `~/blob-backups` step 2b) and `management.py prune_db`, which pruned feeds older
  than 8 days and had been a no-op since scraping stopped in 2024-05.

- **2026-09** **Off Heroku onto Vercel, with the Postgres database on Neon.** The API is served
  from `hn-api.crystalprism.io` on Vercel; the database moved to the Neon project
  `bitter-star-94554507` (PostgreSQL 18) with no SQL rewritten. `hacker_news_stats` points at
  the new base URL, and its account lookups go to `api.crystalprism.io` — a different service,
  now named as its own constant rather than a literal buried in a fetch. Nightly logical dumps
  run via `~/blob-backups` (`backup.sh` step 2b → `pg/hn-scrape.sql`), restore-verified end to
  end at 562,304 rows.

- **2026-09** **`deepest_comment_tree` no longer 500s on a period with no comments.** It assumed
  at least one row and indexed into an empty result. 125 tests pass, up from 119.

## Next

- [from 2026-10-30] [needs data] **Re-measure Neon after 48h of hourly scraping.** The steady
  state was estimated at ~370-400 MB (one `feed_comment` row per comment per hourly feed, kept 8
  days) against the free plan's 0.5 GB, and ~21 CU-hours/month of the 100. Read
  `pg_database_size` and the project's compute usage; if storage is on course past ~400 MB, cut
  `retention.RETENTION_DAYS` or stop storing a `feed_comment` row for every feed.
- **Alert when no scrape has landed for hours.** A run that never starts (schedule disabled,
  Actions outage) reaches nobody: the workflow's flare step only fires for runs that start.
  flare has no heartbeat check, so this needs either a flare feature or an external check on the
  newest `feed.created`.

## Declined

