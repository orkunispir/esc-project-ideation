# ESC Project Ideation

The live Supabase backend exists, and this repository now includes a credential-safe adapter/backend snapshot around it. The public package combines that integration boundary with a grounded ESC ideation skill, an implementation plan, an integration runbook, and offline-only CI checks.

The repository is designed as a buildable handoff. It keeps private source-sheet URLs, Supabase project references, keys, and dashboard URLs out of the public tree. Live verification is a separate, user-owned step that requires a short-lived user JWT.

## What is complete

- The `esc-project-ideation` skill combines Hermes’ 22 routed creative methods with the ESC/Supabase project-finding context.
- The existing backend snapshot represents the current Germany-coordinated ESC corpus, vector retrieval path, row-level protection, and authenticated `esc-search` surface.
- The credential-safe adapter and reproducible backend files are checked in at these stable paths:

  ```text
  skill/esc-project-ideation/scripts/search_esc.py
  tests/test_search_esc.py
  supabase/schema.sql
  supabase/config.toml
  supabase/functions/esc-search/index.ts
  skill/esc-project-ideation/references/supabase-retrieval.md
  ```

- `docs/IMPLEMENTATION_PLAN.md` defines the dependency-aware path from the adapter contract to corpus evaluation.
- `docs/SUPABASE_INTEGRATION.md` describes local, offline, and user-authorized live verification without publishing credentials.
- `docs/INSTALL.md` is the short installation and configuration guide.
- `examples/DEMO.md` shows the intended retrieval-to-evidence behavior in one small example.
- `.github/workflows/validate.yml` runs Python unit tests and structural checks without Supabase secrets or network-dependent tests.

## Current architecture

```text
Private Drive corpus
        │
        ▼
Supabase/Postgres vector search
        │ authenticated esc-search surface
        ▼
Credential-safe retrieval adapter
        │ provenance-preserving evidence
        ▼
ESC ideation skill
        │ grounded concept / research direction
        ▼
Private Drive output
```

The current MVP context describes 1,000 Germany-coordinated ESC records, `vector(384)` embeddings, HNSW retrieval, protected direct table access, and an authenticated search function. These facts describe the supplied handoff; they are not an eligibility claim or a substitute for current official programme guidance.

## Verification boundaries

### Completed state

The repository contains the public-safe skill, attribution, ESC context, implementation documentation, and validation scaffold. The live backend is an existing dependency of the project. Exact infrastructure identifiers are intentionally represented only by placeholders.

### Local/offline verification

Run:

```bash
python3 -m unittest discover -s tests -p 'test_*.py' -v
node supabase/tests/request_test.ts
bash scripts/check_bundle.sh
```

These checks use local fixtures and file structure only. They must not require a Supabase URL, JWT, key, Drive connection, or network access.

### Live verification — not run in this increment

The authenticated smoke test is deliberately not claimed as complete here. It requires a user JWT and private endpoint configuration supplied at execution time. Follow [`docs/SUPABASE_INTEGRATION.md`](docs/SUPABASE_INTEGRATION.md) when the user is ready to perform that check.

### Future work

The remaining increments are to connect retrieval to the evidence ledger, produce private Drive outputs, expand ingestion beyond the Germany slice, and evaluate multilingual and hybrid retrieval. The gates and dependencies are recorded in [`docs/IMPLEMENTATION_PLAN.md`](docs/IMPLEMENTATION_PLAN.md).

## Install and use the skill

Follow [`docs/INSTALL.md`](docs/INSTALL.md), then invoke the installed skill as `$esc-project-ideation`. Retrieval is optional: the skill still works with supplied notes and documents when live credentials are unavailable, and must label that limitation.

See [`examples/DEMO.md`](examples/DEMO.md) for a short prompt, retrieval command, and expected evidence-grounded output shape.

## Public-safe configuration

Copy [`.env.example`](.env.example) to an ignored local environment file, or use [`docs/CONFIG.example.md`](docs/CONFIG.example.md) as a placeholder-only reference. Do not commit service-role keys, user JWTs, private source links, project references, or deployment-specific URLs.

## Licensing

See [`NOTICE.md`](NOTICE.md) and [`skill/esc-project-ideation/references/hermes-attribution.md`](skill/esc-project-ideation/references/hermes-attribution.md). No service-role keys or other secrets are included.
