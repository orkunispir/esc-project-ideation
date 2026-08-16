# Private configuration boundary

This repository is public-safe by design. Keep the source-sheet URL, Supabase project reference, runtime keys, and deployment-specific endpoints in a private environment or secret manager.

Example values for the checked-in retrieval adapter:

```dotenv
ESC_SUPABASE_URL=https://<project-ref>.supabase.co
ESC_SEARCH_ENDPOINT=https://<project-ref>.supabase.co/functions/v1/esc-search
ESC_SUPABASE_API_KEY=<publishable-or-anon-key-if-required>
ESC_SUPABASE_ACCESS_TOKEN=<short-lived-user-jwt>
SOURCE_SHEET_URL=<private source-sheet URL>
SOURCE_SHEET_TAB=esc2021
```

Do not commit access tokens, service-role keys, private source links, or project dashboard URLs. The adapter calls the authenticated `esc-search` function, preserves returned project-card URLs and project identifiers in evidence, and keeps private values out of logs and public documentation.
