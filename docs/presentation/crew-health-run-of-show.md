# Crew Health Presentation Run-of-Show

Baseline: `main` at `e83cf6b`. The flow below was rehearsed in the browser against that commit. The 4-minute timing is a rehearsal guide. Adjust it to the event's actual time limit.

## Run mode: what was tested and what is pending

| Item | Status |
| --- | --- |
| Browser rehearsal on `e83cf6b` | Done with the **mock model**. All screens below come from this run. |
| Gemma + adapter final recheck | **Pending.** Do not present mock output as real-model output. If the real-model recheck is not complete, say "designed to run on board" and label mock screens as mock. |
| Evidence corpus | Passages and their language come from the **configured export**. If no evidence file is configured, the rehearsal backend still loads the bundled habitat passages. |
| Setup | Backend and run modes: [backend/README.md](../../backend/README.md). Model and adapter: [model/README.md](../../backend/model/README.md). |

All measurements are synthetic demo data. Medical guidance stays on hold in the rehearsal, and the crew contacts the medical officer outside the app.

## Script (~4 minutes)

Rows marked **Essential** must be shown. Rows marked **Optional** can be dropped when time is short. Acts 1 and 3 are essential; Acts 2 and 4 are optional per #47.

| # | Time | Priority | Screen and talking points |
| --- | ---: | --- | --- |
| Intro | 20 s | Essential | **Mars base intro.** "When ground answers are delayed, what can the crew check on board right now?" The demo setting is 12 minutes one way, which means 24 minutes of round-trip signal time alone. |
| Act 1 | 50 s | Essential | **Sol 16, 06:12 · C1.** Lighting adjusts automatically. The owner approves the EVA schedule adjustment. **Sol 17:** compare readings against C1's personal baseline, then release. |
| Act 2 | 20 s | Optional | **Sol 40, 09:00 · delayed.** Optionally add a short spoken bridge about the delay. There is no preparation feature, so do not show or describe one. |
| Act 3 | 70 s | Essential | **Sol 46, 08:00 · C4.** Enter a symptom live. The entry triggers a rule warning (see details below). |
| Act 4 | 50 s | Optional | **Sol 57, 08:00 · C2.** Send, then confirm simulated receipt. For a retry demo, mark the packet missing, advance to a later comm window, send it again, then confirm receipt. Then show the signal comparison (see details below). |
| Close | 20 s | Essential | "While waiting for ground, the crew can still see what changed and which records support it." |

### Act 3 details

1. C4 enters a symptom live. The rule engine shows a warning.
2. On their own **Today** screens, C1 and C3 each consent to saving a **NONMEDICAL** report.
3. The saved report contains all six recorded readings and links to the existing warning packet.
4. This consent does not produce clinical guidance. State this explicitly during the demo.

### Act 4 details

- **Send flow.** Show sequence numbers, the hash, and the simulated receipt state. The whole flow is a local simulation. The transmission control updates the simulated warning packet. The detailed report stays in the local database.
- **Signal comparison.** Hold the noise the same and compare ±1 against ±3 levels. At equal symbol duration, the ±3 case uses 9× energy. Present this result as conditional on the simulation settings, not as measured link performance.

## Optional standalone: RAG example (separate rehearsal, if time)

This example is not part of the four acts. Show it only if it has been rehearsed separately.

1. Enter "I feel dizzy."
2. The app asks a follow-up question about standing.
3. The app shows a cited passage from the configured export. Open the source and point to the passage ID.

If no passage matches, the app withholds an explanation instead of answering freely.

## Data and verification labels

- **Data:** Synthetic scenario from [seed.py](../../backend/seed.py). Personal baselines come from [today.py](../../backend/today.py) and use the most recent 14 valid measurement days.
- **Verification:** The app checks numbers, source IDs, warning level, JSON format, and assertive wording. If a check fails, the app regenerates once, then withholds. A valid source ID does not prove that the passage supports the meaning of the text. Do not present validator pass rates as clinical accuracy.
- **Medication:** The model does not recommend drugs or doses.

## Sources

| Topic | Source | Use |
| --- | --- | --- |
| Mars delay | [NASA: Communication Delays, Disruptions, and Blackouts for Crewed Mars Missions](https://ntrs.nasa.gov/citations/20220013418) | One-way delay can reach about 22 minutes, and disruptions also occur. The app's 12 minutes is a demo setting. |
| Store and forward | [NASA: Delay/Disruption Tolerant Networking](https://www.nasa.gov/communicating-with-missions/delay-disruption-tolerant-networking/) | Design reference only. Do not claim NASA DTN is implemented. |
| Withholding and checks | [event_flow.py](../../backend/event_flow.py), [pipeline.py](../../backend/model/pipeline.py), [verify.py](../../backend/verify.py) | Retrieval, regeneration, and withholding. |

## Before presenting

- Re-run Acts 1–4 once.
- Confirm the event's time limit.
- Disclose AI use in submitted materials.
