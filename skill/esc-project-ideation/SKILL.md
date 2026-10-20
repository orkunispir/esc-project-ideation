---
name: esc-project-ideation
description: Grounded creative ideation for European Solidarity Corps and nonprofit solidarity-project concepts, research directions, project selection, and concept-note preparation. Use when the user wants meaningful ESC project ideas, variations on an existing concept, help choosing between project directions, a research question from the project corpus, or a fundable concept shaped from community needs and evidence.
---

# ESC Project Ideation

Combine a routed creative method with evidence from the European Solidarity Corps project context. The goal is a specific, meaningful project direction that could be investigated and built—not a generic list of grant-sounding ideas.

## Core contract

- Use exactly one creative-ideation method per response unless the user explicitly asks for a combination. Add the ESC grounding pass below; that pass is evaluation and evidence work, not a second ideation method.
- Route before generating. Identify the phase, project domain, specificity, project stage, and requested output. Do not begin with an unstructured list of ideas.
- Make the solidarity mechanism explicit: who participates, which community benefits, what participants actually do, and what changes because of the work.
- Prefer real places, groups, partner types, activities, materials, time horizons, and mechanisms over categories such as “an innovative platform for youth empowerment.”
- Separate evidence, inference, and hypothesis. A similar project in the corpus is a precedent, not proof of local need, eligibility, impact, or approval probability.
- Include at least one grounded direction with a credible first validation step. Other directions may be more experimental, but none may be strange without a reason to exist.
- When the user selects a direction, stop ideating and help build that direction into a research plan, project concept, or application component.

## Read the right references

Read `references/esc-context.md` first when the request concerns the current ESC project-finding MVP or its corpus. Read `references/esc-retrieval-adapter.md` before using the installed retrieval script; its HTTP contract is provisional and has not been live-verified. Read `references/esc-method-routing.md` for every ideation request, then load only the one selected method from `references/methods/`. Read `references/esc-ideation-rubric.md` and `references/esc-output-templates.md` when producing or comparing project concepts. Apply `references/anti-slop.md` to the creative layer; it is inherited from Hermes and must be supplemented with the ESC-specific checks here.

The remaining `references/` files are the copied Hermes method library: `method-catalog.md`, `heuristics.md`, `full-prompt-library.md`, and `exercises.md`. Use them selectively. Do not load every method file for one answer.

## Workflow

### 1. Frame the request

Extract:

- **Phase:** generating, expanding, selecting, unblocking, subverting, refining, or synthesizing.
- **Domain:** solidarity system/community, project artifact or tool, research question, service, or application concept.
- **Specificity:** no context, broad domain, named project, or concrete problem.
- **Stage:** discovery, partner/community validation, concept design, application preparation, or delivery/learning.
- **Output:** idea set, variations, shortlist, research question, concept card, theory of change, or next-step plan.

If the phase or intended object is genuinely ambiguous, ask one short clarifying question. If the user supplied a project, dataset, or problem, do not ask them to repeat it.

### 2. Establish an evidence base

Use the strongest available source in this order:

1. User-provided observations, interviews, partner knowledge, or local facts.
2. Retrieved ESC project records or other supplied project documents.
3. Current official programme guidance when discussing eligibility, priorities, deadlines, or scoring.
4. Clearly labelled hypotheses when no evidence is available.

When credentials are configured, use the installed adapter to retrieve a small, relevant comparison set:

```bash
python3 <skill-dir>/scripts/esc_search.py "<need, target group, place, activity, or outcome>" \
  --country <country> --action "<action>" --funding-year <year> --limit 5
```

The query should carry the need, target group, place, activity, and outcome; the optional filters are only for country/action/year. Use `--format markdown` when an evidence-ready rendering is useful. The adapter defaults to JSON, preserves returned identifiers, URLs, titles, full summaries, and funding amounts (including zero), and fails rather than guessing when required provenance is missing or a selected source URL is not an absolute HTTP(S) URL. It has a **provisional, not live-verified** HTTP contract; read `references/esc-retrieval-adapter.md` and surface that limit when it matters.

If the adapter or credentials are unavailable, use supplied project records, documents, or user observations instead. A zero-record result is valid but is not evidence that no relevant project exists. Record project identifiers, titles, years, summaries, funding amounts, and URLs only when returned by the source. Use 3–7 records to expose patterns, missing categories, and overused shapes. Do not present the corpus as exhaustive unless its coverage is known.

Create a compact evidence ledger:

| Type | Claim or observation | Source | Confidence |
|---|---|---|---|
| Evidence | Directly stated or retrieved fact | URL, project identifier, or user note | high / medium |
| Inference | Pattern reasonably derived from evidence | linked evidence | medium / low |
| Hypothesis | Useful proposition to validate | proposed test | low |

Never invent a partner, need, result, budget, funding rule, or local statistic. If the task needs current programme rules, verify them from official sources and state the relevant call/year; the handoff file is not a substitute for the current Programme Guide.

### 3. Route and apply one method

Use `references/esc-method-routing.md`. A named method or an explicit user mood takes priority. Otherwise route by phase first, then by project domain. State the selected method and its origin briefly. Load the corresponding method file and follow its procedure; do not merely name the method as decoration.

For high-slop prompts such as “give me AI ideas for an ESC app,” reject the obvious first five concepts internally. Replace category language with a concrete community, activity, actor relationship, and mechanism. If a provocative method produces an impossible direction, preserve the useful tension and translate it into a testable project rather than pretending it is already feasible.

### 4. Run the ESC grounding pass

For each surviving direction, answer:

- **Need:** What situation is being changed, for whom, and where?
- **Solidarity mechanism:** What do volunteers/participants contribute in concrete terms? What reciprocal relationship is created with the community?
- **Activities:** What happens week by week or event by event? Name the medium, setting, tools, or materials.
- **Partners:** Which organisation types, local actors, and participant roles are necessary? Mark unconfirmed partners as placeholders.
- **Outcome:** What observable change could occur, and how would it be noticed without inflated claims?
- **Fit:** Which ESC action or priority might be relevant, if known? Mark this as “to verify” unless supported by current official guidance.
- **Feasibility:** What can be tested in 7–14 days, what is likely to cost time or money, and what dependency could stop it?
- **Ethics and risk:** Consider safeguarding, power imbalance, accessibility, consent, privacy, extractive volunteering, and the risk of designing for the community without it.
- **Distinctiveness:** Which exact precedent or common project shape does it depart from, and what is genuinely different?

Score only as a thinking aid, not as an official grant score. Use the rubric in `references/esc-ideation-rubric.md`, then explain the decisive trade-off in plain language.

### 5. Produce the requested output

Use the matching template in `references/esc-output-templates.md`:

- **Generating:** three materially different concept cards, or seven only when the user asks for volume. Make the grounded direction visibly identifiable.
- **Expanding:** variations around the chosen mechanism; preserve what matters and name what changes.
- **Selecting:** a compact comparison plus a pre-mortem and recommendation tied to evidence and constraints.
- **Synthesizing:** clusters from project records or notes, then gaps and opportunity directions; do not confuse frequency with importance.
- **Research:** a sharp question, why it matters, what the corpus can and cannot answer, and a feasible first study.
- **Concept/application:** a structured concept with open questions and source-backed claims; do not fabricate compliance language.

Every concept must include a concrete mechanism, intended participants/community, evidence status, first validation step, and honest failure mode or trade-off. Avoid identical five-item lists and marketing language. Name the method used and, where the method reference provides it, its originator.

## Tool and source boundaries

- Use the Google Drive workflow when project documents or the corpus source are in Drive; preserve links and provenance in working notes.
- Use the installed `scripts/esc_search.py` when querying the ESC MVP. It reads `SUPABASE_URL`, `SUPABASE_ANON_KEY`, and `SUPABASE_ACCESS_TOKEN` from the environment and calls only the authenticated `esc-search` Edge Function. Never request, print, or pass service-role credentials as command arguments, and never substitute direct table access for the configured search surface. See `references/esc-retrieval-adapter.md`.
- Browse official EU/ESC sources for current rules, priorities, deadlines, or scoring. Treat third-party examples as inspiration or leads, not authority.
- If a required fact is unavailable, leave an explicit open question and propose a validation action instead of filling the gap with plausible prose.

## Final quality check

Before returning, verify:

- [ ] The route and chosen method are visible or recoverable.
- [ ] The concept is tied to a real need, community, place, or partner situation.
- [ ] The solidarity mechanism and participant work are concrete.
- [ ] Evidence, inference, and hypothesis are separated.
- [ ] Each retrieved precedent keeps its source identifier and URL; missing provenance was not treated as a valid record, and similarity was not presented as confidence.
- [ ] At least one direction is buildable/pursuable now.
- [ ] A failure mode, trade-off, ethical risk, and first validation step are present.
- [ ] No invented eligibility, score, statistic, partner, impact, or funding amount appears.
- [ ] The output is specific enough that two people could take the next real-world step.
