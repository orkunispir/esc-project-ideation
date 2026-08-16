# ESC ideation skill — Supabase alignment

## Summary

`esc-project-ideation` is a reasoning and proposal-design layer for the ESC knowledge system. It combines routed creative methods with retrieved project evidence, community validation, feasibility checks, and explicit uncertainty labels.

## Alignment with the planned architecture

- **Google Drive:** remains the human-readable source and working knowledge layer. The skill preserves document provenance but does not synchronize or search Drive automatically.
- **Supabase/Postgres + pgvector:** serves as the semantic retrieval layer for ESC project precedents. The skill understands the `public.esc_projects` table, 384-dimensional embeddings, HNSW search, filters, and the `search_esc_projects(...)` pathway.
- **Authenticated access:** it follows the intended security boundary: query the authenticated `esc-search` Edge Function rather than reading the table directly. RLS and the deny-all direct-read policy remain intact.
- **Large-model harness + custom skills:** this skill fits as a deeper reasoning module after retrieval. Gemini or another lightweight tool can still handle quick reference searches.

## Current state

The skill now includes a zero-dependency retrieval client that calls the authenticated `esc-search` surface and validates the returned evidence shape. Offline mocked tests pass. The documented ideation smoke test still used the MVP handoff summary; an authenticated live adapter-to-evidence run remains pending.

## Intended flow

```text
Drive knowledge → Supabase semantic search → ESC ideation skill → grounded concept → Drive
```

## Next implementation step

Run an authorized live search with a short-lived user JWT, verify that 3–7 source-linked records pass through the adapter unchanged, and feed them into the skill’s evidence ledger. Then connect the reviewed output to the private Drive workflow.

The architecture is now **implemented locally but not yet live-verified end to end**. The remaining larger-scale gaps are multilingual embeddings, full-European ingestion, scheduled sync, Drive output automation, and production MCP integration.
