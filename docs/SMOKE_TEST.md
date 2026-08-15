# ESC Project Ideation — smoke test

Date: 2026-08-13

## Purpose

Exercise the installed `esc-project-ideation` skill on the current ESC semantic-search direction, using the supplied MVP handoff as the only factual project source. The test checks routing, Hermes-method use, evidence labels, meaningful project mechanisms, feasibility, and non-fabrication.

## Test prompt

> Using the ESC project-finding MVP direction in `ESC_SUPABASE_MVP_SUMMARY.md`, generate three meaningful project directions for a small German nonprofit that wants to turn project-corpus knowledge into real local solidarity work. Do not propose a software product. Use the current handoff facts, mark hypotheses clearly, and give a 7–14 day validation step for each direction.

## Route selected

- Phase: generating.
- Domain: community/institutional system.
- Specificity: named project direction plus a concrete use case.
- Stage: discovery and partner/community validation.
- Output: three concept cards with a grounded recommendation.
- Method: `references/methods/leverage-points.md` — Donella Meadows.
- Grounding references: `esc-context.md`, `esc-ideation-rubric.md`, and `esc-output-templates.md`.

The method was selected because the request is about changing the flow from project data to local solidarity work, not about building another search feature.

## Evidence ledger

| Type | Claim | Source | Confidence |
|---|---|---|---|
| Evidence | The MVP contains 1,000 Germany-coordinated records with summaries, actions, years, countries, organisations, funding amounts, and project-card URLs. | Supplied handoff, “Current corpus” | high |
| Evidence | All 1,000 records had embeddings at handoff; three semantic smoke searches returned relevant results. | Supplied handoff, “Embeddings and search” / “Verification” | high |
| Evidence | The current slice is Germany-only; `gte-small` is English-focused and truncates long inputs after 512 tokens. | Supplied handoff, “Limitations and next steps” | high |
| Inference | The corpus is useful for finding precedents and recurring descriptions, but cannot establish a local need or project impact by itself. | Derived from scope and limits | medium |
| Hypothesis | A short process that connects corpus precedents to local listening and a small pilot will produce stronger concepts than similarity search alone. | Proposed test | low |

## Smoke-test output

### Method: Leverage Points — Donella Meadows

System map: the MVP holds a growing stock of project descriptions and searchable precedents. Information flows from the corpus into an organisation’s concept work, while local observations, partner feedback, and delivery failures are not yet represented in the handoff. A likely positive loop is “well-described precedent → easy reuse → more similar concept language.” The most actionable leverage is therefore the information flow (level 6), the project goal (level 3), and the design rules for validating an idea (level 5).

### Grounded direction — Precedent-to-Listening Sprint

**Mechanism:** Over 14 days, two volunteers and one local partner organisation select three relevant ESC precedents, translate each into a plain-language activity, hold two listening sessions with the intended community, and run one small activity that can be observed. The output is a one-page concept card with an evidence ledger and a decision to continue, change, or stop.

**Need/community:** The actual local need is still an open question. The partner must choose the community and setting; the corpus supplies comparison material, not the need statement.

**Activities:** One corpus review; two facilitated listening sessions; one low-cost micro-pilot; one reflection with participants and the partner. Use printed project cards and a shared paper ledger so the method works without building a new application.

**Partners/roles:** A German nonprofit as coordinator; one local organisation with an existing relationship to the community; volunteers as listeners, organisers, and documenters. Names are placeholders until the partner confirms them.

**Expected change:** The organisation has a tested activity mechanism and a community-checked problem statement rather than a concept copied from a similar project.

**Why it is not generic:** It treats semantic search as a source of contrasts and questions, then makes local listening a required gate before application writing.

**First validation step:** Ask one plausible partner to bring five observations from the target setting. In a 60-minute session, compare those observations with three retrieved precedents and decide whether a two-hour micro-pilot is safe and useful.

**Failure mode/trade-off:** Volunteers may import a polished but inappropriate precedent; the English-focused model may miss relevant German wording; a two-week sprint may privilege needs that are easiest to observe. Mitigate by letting the partner choose the community, recording rejected precedents, and treating the model as retrieval assistance only.

**Evidence status:** Evidence for the corpus and search capability; inference about the information-flow gap; hypothesis about improved concept quality.

**Fit note:** The relevant ESC action, priority, and eligibility would need to be verified against the current official guidance after the activity and partner roles are known.

### Direction 2 — The Missing-Mechanisms Wall

**Mechanism:** Volunteers print a small, deliberately varied sample of project cards and sort them by actual participant activity—repair, accompaniment, teaching, mapping, hosting, advocacy, care—rather than by topic. With a local partner, they mark who is missing, which community role is assumed, and which outcomes are merely claimed. The group then designs one activity around a gap that the partner confirms locally.

**Need/community:** The local target group is an open question. The first session is a diagnostic with the partner and must not claim that a corpus “absence” equals a community need.

**Activities:** Extract activity/mechanism cards; make a wall map; annotate participant and community roles; choose one gap; test a small activity or conversation.

**Partners/roles:** A nonprofit facilitator, one community-based partner, and volunteers with language/accessibility support as needed. The partner owns the interpretation of what is missing locally.

**Expected change:** The organisation can distinguish “few records describe this” from “this community needs this,” and can avoid repeatedly proposing the same visible project shape.

**Why it is not generic:** The unusual unit of analysis is the work people do, not the topic label or grant amount.

**First validation step:** Print 12 records from different actions and ask a partner plus three volunteers to classify the mechanisms independently. Compare disagreements before designing anything.

**Failure mode/trade-off:** The sample may reflect search bias, Germany-only coverage, or language limitations; the wall can turn into an abstract taxonomy with no community action. Stop if the group cannot identify a safe local test within the session.

**Evidence status:** Evidence for the fields and corpus limits; inference that mechanism-level comparison may expose repetition; hypothesis about useful gaps.

**Fit note:** Any claim about an underserved group or programme priority remains `to verify` with local evidence and current official guidance.

### Direction 3 — Failure-First Solidarity Lab

**Mechanism:** Before drafting a project concept, volunteers and a community partner run a structured pre-mortem: assume the proposed activity failed six months later, then identify the smallest design change that would have prevented each failure. Use corpus precedents only to find concrete activities and failure questions, not to justify the plan.

**Need/community:** This addresses an organisational design need—projects being shaped before delivery realities and community power are visible. The beneficiary-facing need must still be named with the partner.

**Activities:** Select three contrasting precedents; write failure cards for recruitment, access, language, safeguarding, partner capacity, and continuation; choose one prevention test; revise the concept; record what remains unknown.

**Partners/roles:** Nonprofit coordinator, community partner, and volunteers who will actually deliver the activity. Former coordinators could be invited, but their experience is a perspective, not proof.

**Expected change:** The project plan contains explicit dependencies and stop conditions before resources are committed.

**Why it is not generic:** The main deliverable is a set of rejected or revised assumptions, not a polished application narrative.

**First validation step:** Run a 90-minute pre-mortem on an existing concept with one partner representative and one person expected to participate in delivery. Count how many assumptions change.

**Failure mode/trade-off:** The exercise can become defensive paperwork or exclude the community if only coordinators attend. Require a participant/community voice and end with one observable test, not a longer risk register.

**Evidence status:** Method-backed proposal grounded in the project context; no evidence yet that it improves delivery.

**Fit note:** This is a design practice, not an eligibility claim or a substitute for safeguarding review.

### Decision aid

| Direction | Need/locality | Solidarity mechanism | Evidence | Delivery | Ethical risk | Decisive trade-off |
|---|---:|---:|---:|---:|---:|---|
| Precedent-to-Listening Sprint | 1/3 | 3/3 | 2/3 | 3/3 | 2/3 | Best first test, but depends on a real partner and may overvalue easy-to-observe needs. |
| Missing-Mechanisms Wall | 1/3 | 2/3 | 2/3 | 3/3 | 2/3 | Strong anti-repetition device, but “missing from the corpus” is easy to misread as “needed locally.” |
| Failure-First Solidarity Lab | 1/3 | 2/3 | 1/3 | 2/3 | 2/3 | Useful governance practice, but weaker direct community benefit until attached to a real activity. |

Recommendation: start with the Precedent-to-Listening Sprint. It puts the corpus in a supporting role, creates a concrete community-validation gate, and can be stopped after 14 days. Reverse this choice if no partner can safely host listening and a micro-pilot; in that case, run the Missing-Mechanisms Wall only as an internal diagnostic and do not present its gaps as needs.

## Result

Pass. The run selected a method before generating, used the handoff facts without inventing project records or eligibility, produced three different mechanisms, identified a grounded direction, and gave each direction a validation step and failure mode. The main residual risk is that a live corpus query would be needed before attaching specific project precedents to a future concept.

