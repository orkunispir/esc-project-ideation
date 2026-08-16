# Supabase integration runbook

This runbook is for the credential-safe adapter/backend snapshot. It documents how to prepare a local environment and how an authorized operator may perform a live read-only check. It does not modify the active Supabase project and does not store any runtime value in the repository.

## Safety boundary

- Use a short-lived user JWT, never a service-role key.
- Keep project references, source-sheet URLs, dashboard URLs, and keys in a private shell or secret manager.
- Do not paste tokens into commits, issues, logs, test fixtures, or Drive documents intended for sharing.
- The adapter must call the authenticated esc-search surface. It must not read public.esc_projects directly from a public client.
- CI is offline-only. The live section below is manual and was not run in this increment.
- Inside the Edge Function, modern `sb_secret_...` keys are sent to PostgREST only through `apikey`; legacy service-role JWTs retain the legacy `Authorization` header for compatibility. Neither key type is exposed to the caller.

## Expected local contract

The adapter reads runtime configuration from the environment and sends a bounded search request:

    {
      "query": "youth climate action",
      "match_count": 5,
      "filter_country": null,
      "filter_action": null,
      "filter_funding_year": null
    }

The current adapter validates a response object with query, model, filters, count, and results. Each result is expected to preserve:

    project_identifier
    project_title
    project_summary
    results_platform_project_card
    action
    coordinator_country
    funding_year
    funding_amount
    similarity

The transport and response validation live in skill/esc-project-ideation/scripts/search_esc.py and are described in skill/esc-project-ideation/references/supabase-retrieval.md. The adapter fails clearly on missing configuration, unauthorized responses, malformed JSON, timeouts, and invalid input.

## Placeholder environment setup

Copy `.env.example` to an ignored local file, or export the values in a private shell. The values below are intentionally placeholders:

    export ESC_SUPABASE_URL='https://<project-ref>.supabase.co'
    export ESC_SEARCH_ENDPOINT='https://<project-ref>.supabase.co/functions/v1/esc-search'
    export ESC_SUPABASE_ACCESS_TOKEN='<short-lived-user-jwt>'
    export ESC_SUPABASE_API_KEY='<publishable-or-anon-key-if-required>'

The adapter requires `ESC_SUPABASE_URL` and derives the function endpoint from it. `ESC_SEARCH_ENDPOINT` is an optional same-origin override. Remote URLs must use HTTPS on a `*.supabase.co` host; loopback HTTP is reserved for local development, and redirects are rejected. `ESC_SUPABASE_ACCESS_TOKEN` is required at request time. `ESC_SUPABASE_API_KEY` is optional and must never be a service-role key.

`docs/CONFIG.example.md` and `.env.example` use the adapter’s exact environment-variable names with placeholders. Do not copy real values into either tracked file.

Check that the variables are present without printing their values:

    test -n "${ESC_SUPABASE_URL:-}"
    test -n "${ESC_SUPABASE_ACCESS_TOKEN:-}"
    printf '%s\n' 'private Supabase configuration is present'

For the manual `curl` checks below, derive the endpoint when only the project URL is configured:

    if [[ -z "${ESC_SEARCH_ENDPOINT:-}" ]]; then
      ESC_SEARCH_ENDPOINT="${ESC_SUPABASE_URL%/}/functions/v1/esc-search"
    fi

## Offline verification

Run these commands before any live check:

    python3 -m unittest discover -s tests -p 'test_*.py' -v
    node supabase/tests/request_test.ts
    bash scripts/check_bundle.sh

The test suite should mock transport and use synthetic response data. It must pass with ESC_SUPABASE_URL, ESC_SEARCH_ENDPOINT, and ESC_SUPABASE_ACCESS_TOKEN unset. If an implementation requires any of those variables during import, move the configuration lookup into the request path or make the dependency injectable.

Inspect the adapter’s supported flags before using it:

    python3 skill/esc-project-ideation/scripts/search_esc.py --help

The intended local command is:

    python3 skill/esc-project-ideation/scripts/search_esc.py --query 'youth climate action' --limit 5 --pretty

Optional filters are `--country`, `--action`, and `--year`; use a two-letter country code such as `DE`. Keep a comparison set small, normally 3–7 records. The adapter takes the endpoint and token from the environment and must not echo the token.

## Manual live read-only verification

This section is a procedure for a user-authorized run. It is not a test result for this increment.

1. Obtain a short-lived JWT from an existing authenticated user session. Do not request or record a service-role key.
2. Export the placeholder variables with private, real values in the current shell only.
3. Prepare an optional API-key header without printing the key:

       esc_api_key_header=()
       if [[ -n "${ESC_SUPABASE_API_KEY:-}" ]]; then
         esc_api_key_header=(--header "apikey: ${ESC_SUPABASE_API_KEY}")
       fi

4. Verify the auth boundary. Send the optional API-key header but omit the user JWT. The request should return an unauthorized status; do not add the response body to the repository.

       curl --silent --show-error --output /dev/null --write-out '%{http_code}\n' "${esc_api_key_header[@]}" --header 'Content-Type: application/json' --data '{"query":"youth climate action","match_count":5}' "${ESC_SEARCH_ENDPOINT}"

5. Then make the authenticated bounded request:

       curl --fail-with-body --silent --show-error "${esc_api_key_header[@]}" --header "Authorization: Bearer ${ESC_SUPABASE_ACCESS_TOKEN}" --header 'Content-Type: application/json' --data '{"query":"youth climate action","match_count":5}' "${ESC_SEARCH_ENDPOINT}"

6. Confirm manually that the response is a bounded JSON result set and that each returned precedent retains its project identifier and provenance fields.
7. Run the adapter command from the previous section and compare its validated output with the function response.
8. Record only a redacted outcome privately: date, query class, HTTP status class, result count, and whether provenance was preserved. Never commit the JWT, endpoint, project reference, source URL, or raw response.

Expected outcomes:

| Check | Expected result |
|---|---|
| No Authorization header | Unauthorized response |
| User JWT | Successful bounded response or a clearly reported empty result |
| Excessive match_count | Rejected or safely capped |
| Optional filters | Applied without bypassing the authenticated function |
| Direct table access | Not used by the adapter |
| Logs | No token, key, source link, or infrastructure identifier |

## Handoff to the ideation skill

After a successful authorized read-only check, pass only 3–7 validated records into the evidence workflow. Keep the following attached to every precedent:

- project identifier;
- title and summary;
- action and funding year;
- coordinator geography;
- funding amount when returned;
- source/project-card provenance when returned;
- retrieval query and filters.

The skill must label what is directly retrieved as evidence, what is inferred from comparison as inference, and what still needs partner/community validation as hypothesis. Similarity is not proof of local need, impact, eligibility, or approval probability.

## Troubleshooting

- 401 or 403: refresh the user session and confirm the JWT is current; do not switch to a service-role key.
- Empty results: reduce the query specificity or check filters; do not infer that the corpus contains no relevant work.
- Malformed response: compare the function snapshot and adapter contract, then fix normalization locally before retrying live.
- Timeout: test with the offline mock and inspect the request count/limit; do not add retries that could hide an auth or contract error.
- Secret detected by the bundle check: remove it from the working tree and rotate the credential if it was ever committed or logged.
