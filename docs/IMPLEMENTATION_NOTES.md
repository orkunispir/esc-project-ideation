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
│   └── search_esc.py
└── references/
    ├── esc-context.md
    ├── esc-method-routing.md
    ├── esc-ideation-rubric.md
    ├── esc-output-templates.md
    ├── supabase-retrieval.md
    ├── hermes-attribution.md
    ├── anti-slop.md
    ├── exercises.md
    ├── full-prompt-library.md
    ├── heuristics.md
    ├── method-catalog.md
    └── methods/                 # 22 copied Hermes method files
```

## Source and adaptation

The Hermes reference library comes from `NousResearch/hermes-agent` at commit `fa83af3f9a42790730b8966ff67e7d9fb627899f`, retrieved 2026-08-13. Its MIT attribution and license text are preserved in `references/hermes-attribution.md`. The main skill instructions and all `esc-*` references are original adaptation work.

## Validation performed

- Ran the skill creator’s `quick_validate.py`: passed.
- Verified the copied Hermes reference files against the retrieved source.
- Ran the documented smoke test using the supplied `ESC_SUPABASE_MVP_SUMMARY.md`: passed.
- No secrets, service-role keys, or unsupported eligibility claims are included.

## Intended next iteration

Run the authenticated client against live project records with a short-lived user JWT, then pass 3–7 retrieved precedents into the evidence ledger alongside local partner notes. Keep source-specific query examples private until the search contract and corpus coverage are stable. Evaluate multilingual retrieval before expanding beyond the Germany slice.
