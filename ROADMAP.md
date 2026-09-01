# Roadmap

Committed doc, not scratch. Kept current by hand as work ships.
**Shipped** = live in production. **Next** = intended, not promised.
**Declined** = decided against, with the reason, so it doesn't get re-proposed.
**Open questions** = unresolved calls, with what would settle them.

## Shipped

- **2026-09** **Off Heroku onto Vercel, with the Postgres database on Neon.** The API is served
  from `hn-api.crystalprism.io` on Vercel; the database moved to the Neon project
  `bitter-star-94554507` (PostgreSQL 18) with no SQL rewritten. `hacker_news_stats` points at
  the new base URL, and its account lookups go to `api.crystalprism.io` — a different service,
  now named as its own constant rather than a literal buried in a fetch. Nightly logical dumps
  run via `~/blob-backups` (`backup.sh` step 2b → `pg/hn-scrape.sql`), restore-verified end to
  end at 562,304 rows.

- **2026-09** **`deepest_comment_tree` no longer 500s on a period with no comments.** It assumed
  at least one row and indexed into an empty result. 125 tests pass, up from 119.

## Declined

- **`scrape_comments`'s level-1 parent lookup ends `.limit(1).one()` and can legitimately match
  zero rows**, which raises rather than returning nothing. Real, but on the scraper path only
  and unreachable from any route. Left deliberately: repairing scraping is out of scope for this
  codebase, which is maintained as a read-only archive of what was already collected. Revisit
  only if scraping is ever restarted.
