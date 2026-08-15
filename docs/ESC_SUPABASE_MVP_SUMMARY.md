# European Solidarity Corps Supabase MVP

Date: 2026-08-09

> Public-safe handoff: exact source URLs and Supabase infrastructure identifiers are intentionally omitted. Keep them in private deployment configuration.

## Goal

Create a remotely accessible semantic-search MVP for European Solidarity Corps projects using Supabase Postgres and pgvector.

## Source

- Source: private Google Sheet, `European Solidarity Corps Germany Projects — Enriched` (URL kept outside this public repository)
- Tab: `esc2021`
- Imported records: 1,000
- Scope: Germany-coordinated projects; this is the current Germany slice, not the eventual full ~20,000-project European corpus.
- Fields preserved: programme, action, funding year, project identifier, title, full project summary, project-card URL, coordinating organisation, coordinator country, participating countries, and funding amount.

## Supabase project

- Project alias: `Project-Finding`
- Project ref and dashboard URL: configured privately

## Database setup

Table: `public.esc_projects`

- `project_identifier` is unique and is the idempotent upsert key.
- Funding amounts use numeric storage; funding years use `smallint`.
- `search_text` is assembled from title, action, organisation, countries, and summary.
- `search_fts` provides a future keyword-search path.
- `embedding` is `extensions.vector(384)`.
- HNSW vector index uses normalized inner-product search.
- Filter index supports coordinator country, action, and funding year.
- Trigger refreshes `search_text`, timestamps, and clears stale embeddings when indexed content changes.

## Embeddings and search

- Model: Supabase-native `gte-small`.
- All 1,000 rows have embeddings; model tag is stored as `gte-small`.
- Search RPC: `search_esc_projects(query_embedding, match_count, filter_country, filter_action, filter_funding_year)`.
- Authenticated Edge Function endpoint:
  `https://<project-ref>.supabase.co/functions/v1/esc-search`
- The raw table is not directly readable by `anon` or `authenticated`; the search function uses the service role internally.

## Verification

- 1,000 rows and 1,000 distinct project identifiers.
- Zero missing summaries and zero missing funding amounts.
- Funding years: 2019–2026.
- Funding amounts: €0.00–€557,400.00.
- Three semantic smoke searches succeeded with HTTP 200:
  - refugee/migrant integration → relevant inclusion and integration projects;
  - youth climate action → climate projects;
  - mental health/inclusion filtered to 2024 → relevant 2024 projects.
- Repeated upsert kept the table at 1,000 rows and preserved the existing embedding.
- Security advisor: no remaining lints.
- Performance advisor only reports informational “unused index” notices because the indexes are new.

## Cleanup and security

- RLS is enabled and an explicit deny-all policy protects direct client table access.
- The temporary embedding-indexer function was disabled after import.
- The temporary `pg_net` extension used to orchestrate batch indexing was removed.
- No service-role or other secret is included in this handoff.

## Limitations and next steps

- `gte-small` is English-focused and truncates long inputs after 512 tokens; a multilingual model should be evaluated before expanding to all European records.
- The current Sheet contains only 1,000 Germany records. The next ingestion phase should discover the source API/XHR and build a resumable, duplicate-safe full-European import.
- A frontend, MCP integration, scheduled sync, and production client wrapper are not yet included.
