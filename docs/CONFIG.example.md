# Private configuration boundary

This repository is public-safe by design. Keep the source-sheet URL, Supabase project reference, runtime keys, and deployment-specific endpoints in a private environment or secret manager.

Example values to provide to a future retrieval adapter:

```dotenv
SUPABASE_URL=https://<project-ref>.supabase.co
SUPABASE_PROJECT_REF=<project-ref>
ESC_SEARCH_FUNCTION=esc-search
SOURCE_SHEET_URL=<private source-sheet URL>
SOURCE_SHEET_TAB=esc2021
```

Do not commit service-role keys, private source links, or project dashboard URLs. The adapter should call the authenticated `esc-search` function, preserve source URLs and project identifiers in returned evidence, and keep those values out of logs and public documentation unless intentionally published.
