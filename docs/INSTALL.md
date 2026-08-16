# Short install guide

## 1. Get the project

```bash
git clone https://github.com/orkunispir/esc-project-ideation.git
cd esc-project-ideation
```

Install or import only `skill/esc-project-ideation/` into the personal-skills area used by your Codex or ChatGPT Work environment. The folder already contains `SKILL.md`, UI metadata, references, attribution, and the retrieval client. After installation, invoke it as `$esc-project-ideation`.

In ChatGPT Work, open the sidebar, select **Plugins**, then open **Skills** to manage personal skills. The exact import controls may vary by account rollout.

## 2. Optional live retrieval

Python 3.11+ is sufficient; the client has no third-party dependencies. Keep real values in a private shell or secret manager:

```bash
export ESC_SUPABASE_URL='https://<project-ref>.supabase.co'
export ESC_SUPABASE_ACCESS_TOKEN='<short-lived-user-jwt>'
export ESC_SUPABASE_API_KEY='<publishable-or-anon-key-if-required>'
```

Never use a service-role or secret key in the client. Test a bounded search:

```bash
python3 skill/esc-project-ideation/scripts/search_esc.py \
  --query 'rural youth social isolation' \
  --country DE \
  --limit 5 \
  --pretty
```

Without live credentials, the skill can still use attached records, partner notes, and official guidance; it must say that live corpus search was not run.

## 3. Verify the checkout

```bash
python3 -m unittest discover -s tests -p 'test_*.py' -v
node supabase/tests/request_test.ts
bash scripts/check_bundle.sh
```

Node 24 is only needed for the Edge Function contract tests. Deployment and the authenticated live smoke test are separate operator steps documented in [`SUPABASE_INTEGRATION.md`](SUPABASE_INTEGRATION.md).
