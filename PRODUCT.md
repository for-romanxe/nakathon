# Product

<!-- impeccable:product-schema 1 -->

## Register

product

## Platform

web

## Stack

Static HTML/CSS/vanilla JS, no build step. One file per screen under `mockup/`. Fonts from Google Fonts (Inter, JetBrains Mono, Noto Sans KR). Canvas for the pixel body. Opened directly from disk or via a local static server.

## Users

Astronauts on a long-duration mission (Moon, Mars transit), checking their own health status a few times a day on a shared tablet or laptop, offline, often alone, sometimes tired or unwell. Secondary: the crew medical officer, who may also be the patient. Earth medical teams receive summaries with 3–22 minutes of one-way delay, so they are not in the loop for same-day decisions.

## Product Purpose

Gather health indicators from a wrist wearable (heart rate, HRV, electrodermal activity, skin temperature), sleep and activity records, plus symptoms the astronaut types in plain language; evaluate them against the person's own baseline; and help the astronaut act. Success is an astronaut who, in under ten seconds, knows whether something is off, why the system thinks so, what to do today, and whom to tell. Built for the NASA Space Apps Challenge 2026, "Create Health Monitoring Software for Astronauts on Space Missions". Mockups in this repo are discussion material for the team meeting; the submission is rebuilt during the event (Nov 14–15, 2026).

## Positioning

A health management platform that runs the routine crews already follow (daily sleep and mood, about 2.5 hours of exercise, weekly diet and PMC, monthly body mass, quarterly vitals) in one light place, and greets the crew member every morning with what to do today. The body changes the routine through rules: a personal-baseline verdict adjusts the guide, a small on-device model only writes the reason and picks a possible condition from a fixed on-device list, and five code checks discard any sentence that disagrees with the numbers or overstates the verdict ("judgement withheld"). Alerts are tiered so a normal day is not made into a problem: advisory (one quiet line), caution, warning. Most teams will show a vitals dashboard with an AI alert. Ours tells you what to do today and shows why, with the verification beside it.

## Operating Context

- Offline, local 4B-class model, no cloud. Long inference (one to two seconds) is normal and shown.
- Pipeline fixed in code: collect → anomaly detection (z-score vs 14-day personal baseline) → symptom interpretation (model, enum-constrained JSON) → evidence retrieval (local BM25) → explanation (model, must cite) → verification (code).
- Status levels follow NASA crew-interface convention: Warning (immediate action), Caution (attention today), Advisory/normal. Colour marks every tier including normal (green); a single-metric advisory (참고) line stays uncoloured; threshold crossings get a yellow/red arrow next to the value; stale data is flagged.
- Data on hand is proxy data: PhysioNet Empatica E4 wrist recordings of healthy adults under stress and exercise, and Sleep-EDF. Presented as proxy, never as astronaut data.
- Team of four. This repo is Tyler's AI-part mockups; a teammate builds the front end.

## Capabilities and Constraints

- Screens (`mockup/app/`): today (greeting, status sentence, 오늘의 가이드, evidence tiles and small body), morning check-in sheet and optional evening check-out, records (symptom chat, weekly diet questionnaire, auto-generated weekly PMC summary, monthly body mass, quarterly vitals), region detail on a pixel body, trends, event detail with verification, full-screen warning, procedures, crew view for the medical officer, settings.
- Working in the mockup: 30-second pre-filled check-in that finalises the guide; rule-driven guide adjustments with cited reasons; advisory / caution / warning tiers; symptom result as three lines (risk category, possible condition from a fixed list, today's actions); scripted pipeline runs with pass, discard and withhold outcomes; check-in streak as the only game element. Earlier single-file explorations: `mockup/dashboard.html`, `mockup/app.html`.
- Not real: all numbers, document ids, crew names. No model runs in the mockup.
- Undecided: whether a single readiness score is shown (currently no score, status banner only); exact metric set beyond the six E4-based tiles; how much of the checklist and explanation is interactive.
- Terminology: baseline (기준선), σ / z-score, Caution/Warning, "judgement withheld" (판단 보류), source id (출처).

## Brand Commitments

- Name: Crew Health (working title).
- Personality: a manager who greets you every morning; warm, concrete and non-assertive. The product never overstates; when evidence is thin it says so.
- Binding references: card style and colour of a dark trading terminal (near-black navy surfaces, 1px hairline borders, tabular mono numbers, teal/red deltas); a pixel-grid body in lime with occasional light cells, anomalous regions fragmenting outward (from the nohandslabs film); the dark launch-film register of the CodePilot film for the separate concept page only.
- Copy is Korean first with English labels where they are standard (HRV, EDA, Sol, Caution).

## Evidence on Hand

- Challenge statement summary and Seoul organiser rules: `notes/health-monitoring-decisions.md`.
- Team idea context: `notes/health-monitoring-idea-context.md`.
- Dashboard research brief (Few, NASA HSI workshop, Oura/Whoop, Carbon/Atlassian colour): `notes/dashboard-design-brief.md`.
- Reference videos: `mockup/refs/` (not committed).
- No real astronaut data, no evaluation numbers yet (to be measured during the event). Do not fabricate either.

## Product Principles

1. Facts first, then words. Numbers and the rule verdict are always visible before and beside any model text.
2. Colour states the tier, never colour alone. Green means within baseline, yellow Caution, red Warning; a single-metric advisory gets one plain line and no colour.
3. Withholding is a feature. When checks fail or data is thin, the honest state is "judgement withheld" with the raw numbers, not a confident sentence.
4. Ten seconds to the plan. Greeting, status sentence and today's guide come before any number; the numbers are evidence below.
5. Everything cites. Every action and explanation carries a source id the astronaut can open.

## Accessibility & Inclusion

Assumed, not yet confirmed by the user: WCAG AA contrast (body 4.5:1, large 3:1) on the dark theme; status conveyed by colour plus arrow plus text; `prefers-reduced-motion` stops the scatter animation and ticking transitions; keyboard-reachable tiles and body regions.
