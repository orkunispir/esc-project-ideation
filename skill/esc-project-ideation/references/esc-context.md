# ESC project context

This reference captures the current direction supplied for the European Solidarity Corps project-finding MVP. It is working context, not an official Programme Guide and not evidence that a proposed project is eligible.

## Purpose

Create a remotely accessible semantic-search MVP for European Solidarity Corps projects, then use the corpus to support grounded project discovery, comparison, and concept development.

## Current corpus

- Source: private Google Sheet `European Solidarity Corps Germany Projects — Enriched`, tab `esc2021` (URL configured privately).
- Scope: 1,000 Germany-coordinated records; this is a Germany slice, not the eventual European corpus.
- Fields: programme, action, funding year, project identifier, title, full project summary, project-card URL, coordinating organisation, coordinator country, participating countries, and funding amount.
- Observed funding years: 2019–2026.
- Observed funding range: €0.00–€557,400.00.
- Current handoff date: 2026-08-09.

## Supabase model

- Project: `Project-Finding` (exact project ref configured privately).
- Table: `public.esc_projects`.
- Idempotent key: `project_identifier`.
- `search_text` combines title, action, organisation, countries, and summary.
- `search_fts` is a future keyword-search path.
- `embedding`: `extensions.vector(384)`.
- Model tag: `gte-small`; all 1,000 rows had embeddings at handoff.
- RPC: `search_esc_projects(query_embedding, match_count, filter_country, filter_action, filter_funding_year)`.
- Authenticated Edge Function: `https://<project-ref>.supabase.co/functions/v1/esc-search`.

## Known verification and limits

- At handoff there were 1,000 rows and 1,000 distinct project identifiers, with no missing summaries or funding amounts.
- Semantic smoke searches for refugee/migrant integration, youth climate action, and 2024 mental-health/inclusion returned relevant results.
- Repeated upsert remained at 1,000 rows and preserved existing embeddings.
- RLS and an explicit deny-all policy protect direct table access; the temporary indexer and `pg_net` setup were removed.
- `gte-small` is English-focused and truncates long inputs after 512 tokens. Evaluate a multilingual model before expanding beyond the Germany slice.
- The next ingestion phase should discover the source API/XHR and support resumable, duplicate-safe import. Frontend, MCP integration, scheduled sync, and production client wrapper are not yet included.

## How to use this context

Treat a retrieved record as a precedent or data point. Use its title, summary, action, year, geography, participating countries, and funding amount to ask better questions:

- Which needs and participant groups are overrepresented or absent?
- Which project mechanisms recur, and where do they fail to explain actual work?
- Which unusual combinations of place, partner role, activity, and outcome deserve validation?
- What can the current Germany slice support, and what requires broader European or local evidence?

Do not infer that a frequent project type is more impactful, that a large grant is a better model, or that a semantically similar record proves eligibility. Keep the source URL and project identifier attached to any precedent used.
