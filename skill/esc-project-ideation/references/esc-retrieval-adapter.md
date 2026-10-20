# ESC retrieval adapter

## Status

The skill includes a dependency-free Python 3 CLI at `scripts/esc_search.py`. It calls the authenticated Supabase `esc-search` Edge Function and returns provenance-preserving project records for the skill's evidence ledger.

**This adapter has not been live-verified.** The repository documents the database RPC parameters, but not the deployed Edge Function's exact HTTP JSON body or response shape. The contract below is therefore a **provisional-v1 compatibility contract**, not a claim about the deployed endpoint. Do not describe adapter output as live-verified evidence until someone has tested it against the real function with valid credentials.

The current corpus is the Germany-coordinated ESC slice (1,000 records at the 2026-08-09 handoff), not the full European corpus. A retrieved record is a precedent or data point. It is not proof of local need, eligibility, impact, or approval probability, and absence from a result set is not evidence that no relevant project exists.

## Requirements

- Python 3.8 or newer, standard library only.
- No service-role key, database connection string, or direct table access.
- An HTTPS Supabase project origin and an authenticated user access token.

## Environment

| Variable | Required | Purpose |
|---|---|---|
| `SUPABASE_URL` | yes | Project origin, for example `https://<project-ref>.supabase.co` |
| `SUPABASE_ANON_KEY` | yes | Public/publishable API key sent in the `apikey` header |
| `SUPABASE_ACCESS_TOKEN` | yes | User bearer token sent in `Authorization: Bearer ...` |
| `ESC_SEARCH_FUNCTION` | no | Edge Function name, default `esc-search`; letters, digits, `_`, and `-` only |

Keep values in the environment or a secret manager. Never put credentials in command arguments, committed files, diagnostics, or examples. The adapter refuses a non-HTTPS URL, embedded URL credentials, a URL with a path, and unsafe function names.

`SUPABASE_URL` must be an origin, not a dashboard URL or a URL with a query string. The adapter builds exactly:

```text
https://<project-ref>.supabase.co/functions/v1/esc-search
```

## Invocation

From the repository root:

```bash
export SUPABASE_URL="https://<project-ref>.supabase.co"
export SUPABASE_ANON_KEY="<publishable-anon-key>"
export SUPABASE_ACCESS_TOKEN="<user-access-token>"

python3 skill/esc-project-ideation/scripts/esc_search.py \
  "refugee and migrant integration through sport" \
  --country DE \
  --funding-year 2024 \
  --limit 5
```

If the skill is installed elsewhere, use `<skill-dir>/scripts/esc_search.py`; the script has no repository-relative dependencies.

Use the plain-language query for the need, target group, place, activity, outcome, or any combination. Optional filters are sent without semantic normalization (surrounding whitespace is trimmed):

- `--country <value>` maps to `filter_country`.
- `--action <value>` maps to `filter_action`.
- `--funding-year <year>` maps to `filter_funding_year`; accepted range is 2000–2100.
- `--limit` is 3–7, default 5.
- `--format json` (default) or `--format markdown`.
- `--timeout` is seconds, greater than 0 and at most 60, default 15.

`--help` lists the same surface. Missing settings and invalid arguments fail with a JSON error on stderr and exit code 2; they do not print a traceback.

## Request contract — provisional-v1

The adapter sends one `POST` with:

```json
{
  "query": "<plain-language query>",
  "match_count": 5,
  "filter_country": "DE",
  "filter_action": "<optional action>",
  "filter_funding_year": 2024
}
```

`filter_country`, `filter_action`, and `filter_funding_year` are omitted when not supplied. Headers are:

```text
Accept: application/json
Content-Type: application/json; charset=utf-8
apikey: <SUPABASE_ANON_KEY>
Authorization: Bearer <SUPABASE_ACCESS_TOKEN>
User-Agent: esc-project-ideation-retrieval/provisional-v1
```

The request is sent once with `http.client.HTTPSConnection`, using the configured timeout. Redirects are not followed; any 3xx response is an error. Credentials are therefore never forwarded to another URL.

These parameter names are a compatibility guess derived from the documented RPC signature:

```text
search_esc_projects(query_embedding, match_count, filter_country, filter_action, filter_funding_year)
```

The Edge Function presumably embeds `query` server-side and forwards the filters. That presumption is unverified.

## Response contract — provisional-v1

A successful response must be one of:

1. A JSON array of record objects.
2. A JSON object with a `results` array of record objects.

Extra wrapper keys are ignored. Anything else fails explicitly as `invalid_response`; the adapter does not guess at `data`, `records`, `items`, or other aliases.

The response must contain only finite JSON numbers. `NaN`, `Infinity`, `-Infinity`, and exponent overflow such as `1e999` are rejected as `invalid_response` with exit code 3. The diagnostic does not echo the raw value. JSON output is serialized with strict non-finite checks as a defense.

Each selected record must be a JSON object and must include non-empty string values for:

- `project_identifier`
- `project_url`

Those are the required provenance fields. A record missing either one causes the whole response to fail with `invalid_response`, naming the record position and missing field. This is deliberately different from a valid zero-record response.

`project_url` must also be an absolute `http://` or `https://` URL with a host, an optional valid port other than zero, no embedded userinfo, no backslashes, and no whitespace or control characters. The adapter validates the URL but preserves the returned string exactly, including any query string and fragment. A selected record with an invalid URL fails as `invalid_response`, identifying only the record position and field, not the URL value.

Only records selected up to `--limit` are validated. If the endpoint returns more records than the limit, records beyond the limit are ignored and a truncation warning is added.

All other record fields are passed through unchanged in JSON. This preserves full titles and summaries, funding years and amounts (including `0`), programme/action, coordinator and participating countries, coordinating organisation, and any returned similarity value. The adapter does not invent missing fields, derive confidence, or reinterpret similarity as confidence. The Markdown formatter displays a known subset and shows `null` where a field is absent.

The adapter returns at most `--limit` records. Fewer than the limit, including zero, is valid.

## Output

Default JSON is intended for agent consumption:

```json
{
  "ok": true,
  "adapter": {
    "name": "esc-project-ideation/esc_search.py",
    "contract": "provisional-v1",
    "live_verified": false
  },
  "query": "...",
  "filters": {"country": "DE", "action": null, "funding_year": 2024},
  "limit": 5,
  "returned": 1,
  "records": [
    {
      "project_identifier": "<returned identifier>",
      "project_url": "<returned URL>",
      "title": "<returned title>",
      "summary": "<returned full summary>",
      "funding_amount": 0
    }
  ],
  "warnings": [
    "Current corpus coverage is the Germany-coordinated ESC slice ...",
    "Semantic similarity, if the endpoint returns it, is a retrieval rank only ..."
  ]
}
```

The record object above is illustrative; the adapter passes through the actual returned object. `warnings` always include the Germany-slice/precedent-not-proof context and the similarity note. A zero-record result adds a zero-record warning.

`--format markdown` produces an evidence-style page with a safe table and full summaries. It escapes pipes, line breaks, HTML, and common Markdown control characters in untrusted record values so a record cannot break the table. The Markdown form keeps the Germany-slice warning and the similarity note visible.

## Errors and exit codes

Errors are JSON on stderr:

```json
{"ok": false, "error": {"code": "authentication_failed", "message": "Authentication failed (HTTP 401). Check SUPABASE_ACCESS_TOKEN and SUPABASE_ANON_KEY."}}
```

| Exit | Meaning |
|---:|---|
| 0 | Success, including zero or fewer records |
| 1 | Unexpected internal error, reported without a traceback |
| 2 | Invalid arguments or missing/invalid configuration |
| 3 | Invalid, unsupported, or oversized response, including missing/invalid provenance or non-finite numbers |
| 4 | Timeout, transport failure, HTTP error, or refused redirect |

Diagnostics never include the anon key, access token, request headers, response body, or full endpoint. HTTP errors report the status only; transport errors report a generic category. A 401 usually means the user token is missing, expired, or paired with the wrong publishable key.

## Offline tests

The repository tests use synthetic records, an injected transport, and a mocked `http.client.HTTPSConnection` for the real default transport. They make no network calls:

```bash
python3 -m unittest discover -s tests -p 'test_*.py' -v
```

They cover the request method/path/headers/body, filter mapping, default transport timeout/close/redirect/bounded-read behavior, Unicode and zero-funding retention, fewer/zero records, malformed and unsupported responses, non-finite numbers, missing or invalid provenance URLs, missing settings, HTTP 401/403/429/5xx, timeout, redirect refusal, and secret-free diagnostics.

## Adapting to the deployed function

If the real Edge Function differs, change only the narrow mapping points in `scripts/esc_search.py`:

1. `build_payload()` — request field names and optional-filter handling.
2. `_extract_records()` — direct array versus wrapper, and the wrapper key.
3. `REQUIRED_PROVENANCE` — only if the deployed response genuinely has different provenance fields.
4. `_is_valid_source_url()` — only if the deployed source URLs use a different but still verifiable HTTP(S) provenance form.
5. The synthetic tests and this reference — keep them aligned with the changed contract.

Do not add broad alias sets or fallback wrappers. An explicit failure is preferable to silently accepting a shape the adapter does not understand.
