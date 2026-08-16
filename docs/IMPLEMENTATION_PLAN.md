# Implementation plan

This plan covers the next increment of the ESC project-ideation system. It treats the live Supabase backend as an existing dependency and keeps the public repository safe to share. It does not authorize changes to the active Supabase project, Drive corpus, or deployment configuration.

## Target outcome

Turn the existing authenticated vector-search surface into a reproducible, provenance-preserving retrieval path that the ideation skill can use as evidence. The first usable result is not a full application writer. It is a small adapter that can retrieve a bounded comparison set, preserve the fields needed to inspect each precedent, and make uncertainty visible.

## State at the start of this increment

| Area | State | Boundary |
|---|---|---|
| ESC ideation skill | Complete public-safe skill with 22 Hermes methods and ESC grounding rules | No claim that a precedent proves local need, impact, or eligibility |
| Supabase backend | Existing live backend with protected direct table access and an authenticated search surface | No project reference, key, or endpoint is committed |
| Adapter/backend snapshot | Python adapter, tests, schema, function snapshot, and retrieval reference are implemented | The checked-in contract must remain aligned with the live response shape |
| Offline verification | Python, TypeScript request-contract, structural, and skill checks pass locally | No network, JWT, Drive, or Supabase dependency |
| Live verification | Not performed in this increment | Requires a user-supplied short-lived JWT and private runtime configuration |

## Dependency-aware milestones

### M0 — Public-safe contract and handoff

Status: complete.

Deliverables:

- Stable paths for the adapter, tests, backend snapshot, and retrieval reference.
- Placeholder-only configuration examples.
- A CI job that runs local unit tests and structural checks.
- Clear separation between completed facts, offline checks, live verification, and future work.

Exit gate: the repository contains no real project references, source links, keys, or user tokens, and scripts/check_bundle.sh retains the 22-method assertion.

### M1 — Adapter contract

Depends on: M0 and the function/schema snapshots.

Status: complete locally; live authentication remains M3.

Define the smallest stable interface in search_esc.py and references/supabase-retrieval.md:

- Inputs: natural-language query, bounded result count, and optional country/action/funding-year filters.
- Authentication: a user JWT supplied at runtime; never a service-role key in the adapter or tests.
- Transport: authenticated request to the esc-search surface; endpoint is read from environment configuration.
- Output: a validated list of records containing project identifier, title, summary, action, funding year, coordinator country, funding amount, similarity, and project-card provenance when returned.
- Errors: distinguish missing configuration, invalid JWT/unauthorized response, malformed response, timeout, and empty result set.
- Logging: record query shape and counts only; redact Authorization headers, tokens, source URLs, and infrastructure identifiers.

Exit gate: the offline test suite can exercise success, empty result, malformed response, unauthorized response, and timeout cases with mocked transport only.

### M2 — Reproducibility and offline fixtures

Depends on: M1.

Status: complete locally.

Make the adapter and backend snapshot reviewable without network access:

- Keep a small synthetic fixture in the test module or a non-sensitive local fixture file.
- Test filter serialization, result normalization, provenance preservation, and error mapping deterministically.
- Keep supabase/schema.sql, supabase/config.toml, and the Edge Function snapshot aligned with the documented contract.
- Use only pinned or standard-library dependencies in CI unless a lockfile is added deliberately.
- Make `python3 -m unittest discover -s tests -p 'test_*.py' -v`, `node supabase/tests/request_test.ts`, and `bash scripts/check_bundle.sh` the canonical local checks.

Exit gate: CI passes with secrets removed and network access unavailable.

### M3 — Authenticated live verification

Depends on: M1 and M2; requires an explicit user decision to run against the live service.

Run the live check manually using a short-lived user JWT supplied outside the repository. Verify:

1. An unauthenticated request is rejected.
2. An authenticated request returns a bounded result set.
3. Optional filters reach the search contract and are reflected in the result behavior.
4. Returned records retain identifiers and provenance fields.
5. The adapter does not bypass the Edge Function or read the protected table directly.
6. Logs and failure output contain no token, key, private source link, or project reference.

Exit gate: record the date, test shape, status code class, result count, and redacted outcome in a private engineering note. Do not add the JWT or infrastructure identifiers to this repository. This gate is intentionally not marked complete here.

### M4 — Retrieval-to-evidence pipeline

Depends on: M3 passing, or an explicit decision to proceed with offline fixtures only.

Connect normalized retrieval results to the ideation skill:

- Select 3–7 records rather than dumping the corpus into a prompt.
- Attach project identifier and source provenance to every precedent.
- Convert retrieved facts into an evidence ledger with separate evidence, inference, hypothesis, and open-question labels.
- Route one creative method, then run the ESC grounding pass for need, solidarity mechanism, partners, feasibility, ethics, and failure mode.
- Preserve the difference between similarity, frequency, local need, and programme eligibility.

Exit gate: a local fixture can produce one concept card and an evidence ledger without inventing partners, needs, outcomes, or eligibility language.

### M5 — Drive output

Depends on: M4 and an approved private Drive workflow.

Write the retrieval/evidence package to a private Drive destination:

- Store the query, filters, timestamp, and model/adapter version.
- Store retrieved provenance alongside the evidence ledger.
- Store the generated concept separately from source records so it cannot be mistaken for corpus data.
- Preserve a human-review step before sharing or using an output in an application.

Exit gate: a reviewer can trace each factual precedent from the concept card back to its private source record without exposing credentials in the repository or logs.

### M6 — Corpus expansion and evaluation

Depends on: M4 for evaluation design; M5 for operational output feedback.

- Discover the source API/XHR and make ingestion resumable and duplicate-safe.
- Expand beyond the Germany slice only after country and language coverage are measured.
- Compare English-focused and multilingual embedding options on a labeled retrieval set.
- Add hybrid semantic/keyword retrieval and evaluate filters separately from semantic ranking.
- Measure recall@k/precision@k on reviewer-labeled queries, provenance completeness, duplicate rate, latency, and failure behavior.
- Revisit the evidence rubric when retrieval begins to influence real proposal preparation.

Exit gate: the team can explain where retrieval is reliable, where it is language- or corpus-biased, and which claims still require local or official evidence.

## Execution order

    M0 public-safe contract
            ↓
    M1 adapter contract
            ↓
    M2 offline reproducibility
            ↓
    M3 user-authorized live auth test
            ↓
    M4 retrieval → evidence pipeline
            ↓
    M5 private Drive output
            ↓
    M6 corpus expansion and evaluation

M4 may be prototyped with fixtures while M3 is pending, but production claims must wait for the live auth gate. M6 should not be used to justify local needs or eligibility without the evidence and official-guidance checks described by the skill.

## Risks and decisions

| Risk | Decision or mitigation |
|---|---|
| Public leakage of infrastructure or source details | Placeholder-only configuration; bundle scan for common URL/token shapes; keep runtime values outside Git |
| Adapter accidentally bypasses RLS | Permit only the authenticated function path; never embed a service-role key; test unauthorized behavior |
| Semantic similarity is mistaken for need or impact | Preserve evidence labels and require partner/community validation |
| English-focused embeddings miss German or multilingual meaning | Evaluate multilingual retrieval before broad corpus expansion |
| Large prompts make provenance hard to inspect | Retrieve 3–7 records and keep source metadata attached to each record |
| Live verification is confused with CI | Keep live checks manual and user-authorized; CI has no Supabase secrets or network test |
