# Short demo

## Prompt

> Use `$esc-project-ideation` to propose one practical ESC direction for a small Brandenburg nonprofit addressing social isolation among rural young adults. Use current corpus precedents if available, separate evidence from assumptions, and give a 7–14 day validation step.

## Optional retrieval call

```bash
python3 skill/esc-project-ideation/scripts/search_esc.py \
  --query 'rural young adults social isolation peer activities' \
  --country DE \
  --limit 5 \
  --pretty
```

## Expected behavior

The skill should:

1. Select and name one creative method, such as **Leverage Points**.
2. Preserve every retrieved project identifier and project-card link in an evidence ledger.
3. Treat the requested target group as user intent, not proof of a local need.
4. Produce a concrete mechanism—for example, a rotating peer-hosted evening activity linked by regional transport—rather than a generic “youth platform.”
5. Propose a small test: interview one local partner and 5–8 young adults, run one hosted evening, and record attendance barriers within 14 days.
6. State an honest failure mode, such as transport being the binding constraint or the activity reproducing an existing offer.

If credentials are absent, the correct behavior is to say `Live corpus search was not run because runtime credentials were unavailable`, continue with clearly labelled hypotheses, and never invent project precedents.

This demonstrates the intended fit: Supabase supplies precedents; the skill supplies method selection, evidence discipline, community grounding, and a testable next action.
