# ESC ideation skill — Supabase alignment

## Summary

`esc-project-ideation` is a reasoning and proposal-design layer for the ESC knowledge system. It combines routed creative methods with retrieved project evidence, community validation, feasibility checks, and explicit uncertainty labels.

## Alignment with the planned architecture

- **Google Drive:** remains the human-readable source and working knowledge layer. The skill preserves document provenance but does not synchronize or search Drive automatically.
- **Supabase/Postgres + pgvector:** serves as the semantic retrieval layer for ESC project precedents. The skill understands the `public.esc_projects` table, 384-dimensional embeddings, HNSW search, filters, and the `search_esc_projects(...)` pathway.
- **Authenticated access:** it follows the intended security boundary: query the authenticated `esc-search` Edge Function rather than reading the table directly. RLS and the deny-all direct-read policy remain intact.
- **Large-model harness + custom skills:** this skill fits as a deeper reasoning module after retrieval. Gemini or another lightweight tool can still handle quick reference searches.

## Current gap

The skill contains instructions, not an executable Supabase client or retrieval adapter. Its smoke test used the MVP handoff summary rather than a live database query.

## Intended flow

```text
Drive knowledge → Supabase semantic search → ESC ideation skill → grounded concept → Drive
```

## Next implementation step

Add a small live retrieval adapter that accepts a need, target group, place, activity, and optional country/action/year filters; calls `esc-search`; returns 3–7 source-linked records; and passes them into the skill’s evidence ledger.

The architecture is therefore **conceptually aligned but operationally incomplete**. The remaining larger-scale gaps are multilingual embeddings, full-European ingestion, scheduled sync, and production client/MCP integration.

