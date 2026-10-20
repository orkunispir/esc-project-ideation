# ESC Project Ideation skill — implementation notes

Date: 2026-08-13

## What was built

`esc-project-ideation` is a personal Codex skill for combining Hermes’ routed creative-ideation methods with the current ESC project-finding direction. It is designed for project discovery, concept selection, research questions, and early application shaping.

The adaptation makes the creative method only one half of the workflow. Every direction also needs a solidarity mechanism, community/partner role, evidence label, feasibility test, ethical check, and honest failure mode. The current Supabase/Drive handoff is included as working context, with explicit limits so the skill does not treat semantic similarity as proof of need or eligibility.

## Folder structure

```text
esc-project-ideation/
├── SKILL.md
├── agents/openai.yaml
├── scripts/
│   └── esc_search.py            # dependency-free retrieval adapter CLI
└── references/
    ├── esc-context.md
    ├── esc-retrieval-adapter.md # provisional adapter contract and usage
    ├── esc-method-routing.md
    ├── esc-ideation-rubric.md
    ├── esc-output-templates.md
    ├── hermes-attribution.md
    ├── anti-slop.md
    ├── exercises.md
    ├── full-prompt-library.md
    ├── heuristics.md
    ├── method-catalog.md
    └── methods/                 # 22 copied Hermes method files
```

## Update 2026-10-20 — retrieval adapter

The skill now includes `scripts/esc_search.py`, a Python 3 standard-library CLI. It accepts a plain-language query and optional country/action/funding-year filters, calls the authenticated `/functions/v1/esc-search` endpoint with environment credentials, and preserves returned provenance and funding metadata.

The HTTP/JSON mapping is provisional. The repository documents the RPC parameters but not the Edge Function request body or response shape. The adapter therefore uses `query`, `match_count`, `filter_country`, `filter_action`, and `filter_funding_year`; accepts a direct record array or `{"results": [...]}`; requires `project_identifier` and `project_url`; and fails explicitly on other shapes. Selected source URLs must be absolute HTTP(S) URLs with a host, no userinfo, whitespace, control characters, or invalid port; accepted URLs are preserved exactly. Non-finite JSON numbers are rejected. It refuses non-HTTPS URLs and redirects, never uses service-role credentials, and does not access tables directly.

No live credentials were available. The adapter has not been called against a deployed service, and its `live_verified` output flag remains `false`. Offline unittest coverage uses synthetic records, an injected transport, and a mocked `http.client.HTTPSConnection` to exercise the real default transport.

## Source and adaptation

The Hermes reference library comes from `NousResearch/hermes-agent` at commit `fa83af3f9a42790730b8966ff67e7d9fb627899f`, retrieved 2026-08-13. Its MIT attribution and license text are preserved in `references/hermes-attribution.md`. The main skill instructions and all `esc-*` references are original adaptation work.

## Validation performed

- Previously ran the skill creator’s `quick_validate.py`: passed.
- Verified the copied Hermes reference files against the retrieved source.
- Previously ran the documented smoke test using the supplied `ESC_SUPABASE_MVP_SUMMARY.md`: passed.
- Ran the adapter’s offline unittest suite with synthetic fixtures, an injected transport, and a mocked default HTTPS transport: passed.
- Ran `bash scripts/check_bundle.sh` and the adapter’s `--help` output: passed.
- No secrets, service-role keys, or unsupported eligibility claims are included.
- No live Supabase request was made, and no live verification is claimed.

## Intended next iteration

Run the adapter against live retrieved project records with valid user credentials, correct the provisional request/response mapping if necessary, and then run the skill against those records and local partner notes. Add source-specific query examples only after the Supabase search contract and the full-European corpus are stable. Evaluate multilingual retrieval before expanding beyond the Germany slice.

