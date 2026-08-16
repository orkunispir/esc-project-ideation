# Supabase retrieval client

Use this reference when current ESC project precedents are needed for ideation, synthesis, selection, or research. Keep the live retrieval step small and provenance-preserving.

## Decide whether to retrieve

1. Use live search when the answer depends on current project precedents, `scripts/search_esc.py` exists in the working environment, and the runtime already provides the credentials required by the authenticated search function.
2. Otherwise use the supplied ESC context, user notes, or attached records. State the limitation explicitly: `Live corpus search was not run because <reason>.`
3. Never fabricate records, claim exhaustive coverage, or silently treat an unavailable search as a successful search.

## Invoke the client

From the skill folder, run a small machine-readable search with 3–7 results. The client uses `5` by default; apply only relevant filters:

```bash
python3 scripts/search_esc.py \
  --query "community gardening for isolated young adults" \
  --limit 5 \
  --country DE \
  --action "Volunteering Projects" \
  --year 2024 \
  --pretty
```

Use the request’s actual need, target group, place, activity, and intended outcome in `--query`; do not search for “interesting projects.” Omit an optional filter when it would create an unsupported assumption. Keep `--limit` between `3` and `7`. Supply `--country` as a two-letter code such as `DE`. Treat `--country`, `--action`, and `--year` as the client’s mappings to `filter_country`, `filter_action`, and `filter_funding_year`.

## Handle credentials safely

- Let the client read the required `ESC_SUPABASE_URL`, `ESC_SUPABASE_ACCESS_TOKEN`, the optional `ESC_SUPABASE_API_KEY`, and an optional same-origin `ESC_SEARCH_ENDPOINT` override from the runtime environment or secret manager. The client accepts HTTPS `*.supabase.co` origins and loopback URLs for local development, rejects redirects, and refuses cleartext remote, cross-origin, or arbitrary hosts. Do not ask the user to paste credentials or put secrets in the command.
- Use only the least-privileged credential accepted by the authenticated search surface. Never use, request, print, log, or commit a service-role key.
- Do not echo the environment, include project references or private endpoints in generated public documents, or persist credentials in the evidence ledger.

## Convert results into evidence

Parse the returned JSON records. For every record used, preserve the returned `project_identifier`, title, summary, action, funding year, coordinator geography, funding amount, similarity, and project-card URL when present. Add a corresponding `Evidence` row to the skill’s ledger with the record identifier and returned source link as provenance; keep private links private. Record the query, filters, result count, and retrieval date alongside the ledger so another person can reproduce the comparison.

Use the records to identify precedents, recurring mechanisms, gaps, and questions. Search results are precedents, not proof of local need, impact, eligibility, or approval probability. Mark patterns derived from several records as `Inference`, and mark any proposed local explanation or opportunity as `Hypothesis` until validated with people, partners, official guidance, or other appropriate evidence.

## Fail safely

If the script is missing, credentials are unavailable, the call times out, exits non-zero, returns malformed JSON, or returns no usable records, do not read the table directly and do not loop on retries. Inspect the error without revealing secrets; allow at most one bounded retry for a clearly transient failure, then continue with supplied evidence and state the exact limitation. Do not claim that live precedents were considered.

Never substitute `public.esc_projects` table reads, PostgREST table calls, ad-hoc SQL, `psql`, or an unauthenticated RPC call for the client. The client must use the configured authenticated `esc-search` surface. Preserve the returned provenance in private working notes, and redact or omit private source links and infrastructure identifiers from public output.
