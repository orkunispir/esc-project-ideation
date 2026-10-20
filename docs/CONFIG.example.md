# Private configuration boundary

This repository is public-safe by design. Keep the source-sheet URL, Supabase project reference, runtime keys, and deployment-specific endpoints in a private environment or secret manager. The values below are placeholders, not working credentials.

## Retrieval adapter environment

`skill/esc-project-ideation/scripts/esc_search.py` reads these variables. Use a publishable/anon key and a user access token; never a service-role key.

```dotenv
SUPABASE_URL=https://<project-ref>.supabase.co
SUPABASE_ANON_KEY=<publishable-anon-key>
SUPABASE_ACCESS_TOKEN=<user-access-token>
ESC_SEARCH_FUNCTION=esc-search
```

- `SUPABASE_URL` must be an HTTPS origin with no extra path, query string, fragment, or embedded credentials.
- `SUPABASE_ANON_KEY` is sent in the `apikey` header.
- `SUPABASE_ACCESS_TOKEN` is sent as `Authorization: Bearer ...`. Supply a short-lived authenticated user token and keep it out of shell history where possible.
- `ESC_SEARCH_FUNCTION` is optional and limited to letters, digits, underscores, and hyphens. The default is `esc-search`.
- The adapter refuses redirects and non-HTTPS URLs; it does not support service-role authentication or direct table reads.

## Source context

These values describe the private source and are not read by the adapter:

```dotenv
SUPABASE_PROJECT_REF=<project-ref>
SOURCE_SHEET_URL=<private source-sheet URL>
SOURCE_SHEET_TAB=esc2021
```

Do not commit service-role keys, private source links, project dashboard URLs, or working access tokens. The adapter preserves returned source URLs and project identifiers in its output; keep those values out of public documentation unless intentionally published.

The adapter's HTTP contract is provisional and has not been live-verified. See `skill/esc-project-ideation/references/esc-retrieval-adapter.md` before changing the mapping or treating output as live evidence.
