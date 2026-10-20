# ESC Project Ideation

An installable Codex skill for turning European Solidarity Corps project data into grounded project concepts, research questions, and early proposal directions.

The project combines Hermes’ routed creative-ideation method library with the current ESC Supabase MVP. The skill is usable now, and the repository now includes its first executable retrieval adapter: a dependency-free Python 3 CLI that ships inside the skill. The adapter has meaningful offline tests but has **not been live-tested** against the deployed Edge Function, so its HTTP contract remains provisional.

## Repository contents

```text
skill/esc-project-ideation/               Installable skill and 22 creative methods
skill/esc-project-ideation/scripts/       Dependency-free retrieval adapter CLI
skill/esc-project-ideation/references/    Context, methods, templates, and adapter contract
tests/test_esc_search.py                  Offline standard-library adapter tests
docs/                                     ESC/Supabase context, alignment, and smoke test
scripts/check_bundle.sh                   Offline structural validation
NOTICE.md                                 Hermes attribution and licensing boundary
```

## Current architecture

```text
Google Drive knowledge → Supabase/Postgres vector search → esc-search adapter → ESC ideation skill → grounded concept → Drive
```

The current MVP contains 1,000 Germany-coordinated ESC records in Supabase/Postgres with `vector(384)` embeddings, HNSW search, and an authenticated `esc-search` Edge Function. Direct table reads remain protected by RLS.

Exact source-sheet URLs and Supabase project identifiers are intentionally not committed to this public repository. See [`docs/CONFIG.example.md`](docs/CONFIG.example.md) for the private configuration boundary.

## Current capabilities

- Route an ideation request through one named creative method.
- Request 3–7 records (default 5) through the authenticated `esc-search` function with a plain-language query and optional country/action/funding-year filters; fewer or zero records are returned honestly.
- Preserve returned project identifiers, URLs, titles, full summaries, and funding metadata, including zero and Unicode values.
- Emit JSON for agent consumption or a Markdown evidence view with untrusted table values escaped.
- Distinguish a valid zero-record result from an invalid response that lacks required provenance.
- Use ESC project precedents as evidence rather than treating them as proof of need or eligibility.
- Separate evidence, inference, hypothesis, and open questions.
- Produce concept cards, shortlists, research questions, and early concept-note structures.
- Check solidarity mechanism, partners, feasibility, safeguarding, distinctiveness, and failure modes.

## Retrieval adapter

The adapter is at `skill/esc-project-ideation/scripts/esc_search.py` and uses only the Python standard library. It posts once to the configured `/functions/v1/<function>` endpoint (default `esc-search`) using:

```dotenv
SUPABASE_URL=https://<project-ref>.supabase.co
SUPABASE_ANON_KEY=<publishable-anon-key>
SUPABASE_ACCESS_TOKEN=<user-access-token>
# Optional; default is esc-search
ESC_SEARCH_FUNCTION=esc-search
```

Example from the repository root:

```bash
python3 skill/esc-project-ideation/scripts/esc_search.py \
  "refugee and migrant integration through sport" \
  --country DE \
  --funding-year 2024 \
  --limit 5
```

Add `--format markdown` for an evidence-ready rendering. Default JSON is designed for agent use. The query carries the need, target group, place, activity, or outcome; `--country`, `--action`, and `--funding-year` are optional filters. `--limit` must be 3–7 and defaults to 5. `--timeout` defaults to 15 seconds.

The adapter requires HTTPS, refuses redirects rather than forwarding credentials, and sends the publishable key as `apikey` plus the user token as `Authorization: Bearer ...`. Credentials are read only from the environment and are never accepted as command arguments or echoed in diagnostics. It does not support service-role auth or direct table access.

**Provisional contract:** the repository documents the RPC parameters (`query_embedding`, `match_count`, `filter_country`, `filter_action`, `filter_funding_year`) but not the Edge Function HTTP body or response shape. The adapter therefore sends `query`, `match_count`, `filter_country`, `filter_action`, and `filter_funding_year`, and accepts either a direct record array or `{"results": [...]}`. Each selected record must include `project_identifier` and a `project_url` that is an absolute HTTP(S) URL with a host and without userinfo, whitespace, control characters, or an invalid port; other returned fields pass through unchanged. Unsupported shapes and non-finite JSON numbers fail explicitly. The mapping is intentionally small and localized in `build_payload()`, `_extract_records()`, and `_is_valid_source_url()`. See [`skill/esc-project-ideation/references/esc-retrieval-adapter.md`](skill/esc-project-ideation/references/esc-retrieval-adapter.md) for the full contract, errors, and adaptation points.

Output always includes the Germany-slice/precedent-not-proof warning and a note that semantic similarity is a retrieval rank, not confidence. A zero-record result is honest but does not prove that no relevant project exists.

## Current limitations

- **The adapter has not been live-verified.** No live credentials were used, and the deployed Edge Function's request/response contract may differ from the provisional mapping.
- The current corpus is a 1,000-record Germany-coordinated slice, not the full European corpus. Retrieved precedents cannot establish local need, eligibility, impact, or approval probability.
- `gte-small` is English-focused and truncates long inputs after 512 tokens; multilingual retrieval has not been evaluated.
- There is no hybrid semantic/keyword search, MCP wrapper, scheduled sync, or automated Drive integration yet.
- The adapter returns only what the endpoint returns. It does not enrich, score, or infer missing fields.

## Install/use the skill

Copy `skill/esc-project-ideation/` into a Codex personal-skills directory, or invoke it explicitly as `$esc-project-ideation` after installation. The skill’s `agents/openai.yaml` provides the UI metadata. The retrieval script and its contract reference are inside the copied skill directory, so the installation remains self-contained.

## Validate

```bash
bash scripts/check_bundle.sh
python3 -m unittest discover -s tests -p 'test_*.py' -v
python3 skill/esc-project-ideation/scripts/esc_search.py --help
```

The unit tests use synthetic fixtures, an injected transport, and a mocked `http.client.HTTPSConnection` for the real default transport; they make no network calls. In a Codex environment, also run the platform skill validator against `skill/esc-project-ideation/`.

## Roadmap

1. Live-test the adapter against the deployed `esc-search` function with valid user credentials, then harden or correct the provisional request/response mapping.
2. Add hybrid semantic/keyword retrieval and provenance-preserving result formatting beyond the current adapter.
3. Connect retrieved records and generated concepts to Drive documents.
4. Expand ingestion beyond the Germany slice and evaluate multilingual embeddings.

## Licensing

See [`NOTICE.md`](NOTICE.md) and [`skill/esc-project-ideation/references/hermes-attribution.md`](skill/esc-project-ideation/references/hermes-attribution.md). No service-role keys or other secrets are included.
