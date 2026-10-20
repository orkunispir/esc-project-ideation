# ESC ideation skill — Supabase alignment

## Summary

`esc-project-ideation` is a reasoning and proposal-design layer for the ESC knowledge system. It combines routed creative methods with retrieved project evidence, community validation, feasibility checks, and explicit uncertainty labels.

The skill now also ships a first executable retrieval adapter. It is a dependency-free Python 3 CLI inside `skill/esc-project-ideation/scripts/esc_search.py`, with focused offline tests and a provisional HTTP/JSON contract.

## Current state

- The adapter accepts a plain-language query plus optional country, action, and funding-year filters and a limit of 3–7 records (default 5).
- It authenticates with `SUPABASE_URL`, `SUPABASE_ANON_KEY`, and `SUPABASE_ACCESS_TOKEN` from the environment and posts once to the configured `/functions/v1/<function>` endpoint (default `esc-search`).
- It returns JSON by default or Markdown on request, preserving returned identifiers, URLs, titles, summaries, and funding metadata, including zero values.
- It validates response shape, finite JSON numbers, and required provenance (`project_identifier` plus an absolute HTTP(S) `project_url`) instead of silently dropping malformed records.
- It refuses insecure URLs and redirects, does not support service-role credentials, and does not read tables directly.
- The adapter's HTTP body and response mapping is **provisional** because the repository documents the RPC parameters but not the deployed Edge Function's JSON contract. It has meaningful offline tests but has **not been live-verified** with real credentials.

The earlier skill smoke test remains a historical offline exercise based on the MVP handoff summary; it does not exercise the adapter.

## Alignment with the architecture

- **Google Drive:** remains the human-readable source and working knowledge layer. The skill preserves document provenance but does not synchronize or search Drive automatically.
- **Supabase/Postgres + pgvector:** serves as the semantic retrieval layer for ESC project precedents. The skill understands the `public.esc_projects` table, 384-dimensional embeddings, HNSW search, filters, and the `search_esc_projects(...)` pathway.
- **Authenticated access:** the adapter follows the intended security boundary: query the authenticated `esc-search` Edge Function rather than reading the table directly. RLS and the deny-all direct-read policy remain intact.
- **Large-model harness + custom skills:** this skill fits as a deeper reasoning module after retrieval. Gemini or another lightweight tool can still handle quick reference searches.

## Intended flow

```text
Drive knowledge → Supabase semantic search → esc-search adapter → ESC ideation skill → grounded concept → Drive
```

## Remaining gaps

The architecture is **conceptually aligned and partially operational**, not complete. Remaining work:

1. Live-test the adapter against the deployed function and correct the provisional request/response mapping if needed.
2. Expand beyond the current 1,000-record Germany-coordinated slice and evaluate multilingual embeddings; `gte-small` is English-focused and truncates long inputs.
3. Add hybrid semantic/keyword retrieval, MCP integration, scheduled sync, and production Drive integration.
4. Treat retrieved precedents as evidence of what has been funded or described, never as proof of local need, eligibility, impact, or approval probability.
