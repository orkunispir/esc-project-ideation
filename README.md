# ESC Project Ideation

An installable Codex skill for turning European Solidarity Corps project data into grounded project concepts, research questions, and early proposal directions.

The project combines Hermes’ routed creative-ideation method library with the current ESC Supabase MVP. It is deliberately a complete current-state scaffold: the skill and documentation are usable now, while the live retrieval adapter remains the next implementation step.

## Repository contents

```text
skill/esc-project-ideation/     Installable skill and 22 creative methods
docs/                           ESC/Supabase context, alignment, and smoke test
scripts/check_bundle.sh         Offline structural validation
NOTICE.md                       Hermes attribution and licensing boundary
```

## Current architecture

```text
Google Drive knowledge → Supabase/Postgres vector search → ESC ideation skill → grounded concept → Drive
```

The current MVP contains 1,000 Germany-coordinated ESC records in Supabase/Postgres with `vector(384)` embeddings, HNSW search, and an authenticated `esc-search` Edge Function. Direct table reads remain protected by RLS.

## Current capabilities

- Route an ideation request through one named creative method.
- Use ESC project precedents as evidence rather than treating them as proof of need or eligibility.
- Separate evidence, inference, hypothesis, and open questions.
- Produce concept cards, shortlists, research questions, and early concept-note structures.
- Check solidarity mechanism, partners, feasibility, safeguarding, distinctiveness, and failure modes.

## Current limitation

The skill contains the retrieval instructions but no executable Supabase client or MCP wrapper. A future adapter should call `esc-search`, apply country/action/year filters, return 3–7 source-linked records, and pass them into the skill’s evidence ledger.

## Install/use the skill

Copy `skill/esc-project-ideation/` into a Codex personal-skills directory, or invoke it explicitly as `$esc-project-ideation` after installation. The skill’s `agents/openai.yaml` provides the UI metadata.

## Validate

```bash
bash scripts/check_bundle.sh
```

In a Codex environment, also run the platform skill validator against `skill/esc-project-ideation/`.

## Roadmap

1. Implement and live-test the authenticated Supabase retrieval adapter.
2. Add hybrid semantic/keyword retrieval and provenance-preserving result formatting.
3. Connect retrieved records and generated concepts to Drive documents.
4. Expand ingestion beyond the Germany slice and evaluate multilingual embeddings.

## Licensing

See [`NOTICE.md`](NOTICE.md) and [`skill/esc-project-ideation/references/hermes-attribution.md`](skill/esc-project-ideation/references/hermes-attribution.md). No service-role keys or other secrets are included.

