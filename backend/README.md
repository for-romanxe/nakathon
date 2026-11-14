# Crew Health demo API

Run from the repository root:

```sh
python -m pip install -r backend/requirements.txt
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

The server creates and seeds `data/crew-health.sqlite3` on startup. It keeps
existing rows across restarts. The demo clock starts at Sol 16, 06:12 and exposes
synthetic crew data on localhost. Use only synthetic data with this demo endpoint.

Use the corresponding crew ID in the `X-Demo-Viewer` header for each request.

| Request | Expected status level |
| --- | --- |
| `GET /crew/c1/today` | `caution` |
| `GET /crew/c2/today` | `normal` |
| `GET /crew/c3/today` | `hold` |
| `GET /crew/c4/today` | `advisory` |

The baseline uses population standard deviation over daily averages for the
previous 14 sols. An event day inside that window is excluded. A missing day
or zero variance makes the corresponding z-score unavailable. Overall warning,
caution, and advisory take precedence over hold, while each missing metric
retains its own hold status. The seeded readings are scenario fixtures and the
thresholds reproduce the team's demo rules.

Display names are C1 through C4. Crew IDs remain `c1` through `c4` in storage
and both spellings work in these URLs.

`GET /crew/{id}/trends?metric=hr&days=7` returns daily mean readings,
the current 14-sol baseline as `baseline.mean` and `baseline.sd`, and
events within the requested window. The window ends at the current
mission sol and defaults to 14 sols (range: 1–90). Days without measurements
have no point. The read permissions are the same as Today.

`GET /crew/{id}/preflight` returns the crew member's preflight values and
their sources. The owner can use `PUT /crew/{id}/preflight` with a body such
as `{"values":{"hr":68}}`. Unspecified metrics are preserved. Use the units
from `contracts/enums.json`. Values entered this way have source `manual`.
Trends returns the selected metric's comparison value in `preflight` as
`{value,source}` or `null`. This value is separate from the rolling baseline
used by the alert rules.

`POST /crew/c1/checkin` saves a check-in and returns the updated Today response.
Example morning request:

```json
{"kind":"morning","answers":{"sleep_quality":4,"mood":3,"fatigue":2,"symptoms":"none"}}
```

Morning submissions mark the sleep and mood review items complete and update
the activity review based on the existing rule status. Submitting the same
kind for the same sol updates the existing entry. `free_text` is optional
and stored as entered.

The three morning scores are integers from 1 to 5. Optional `symptoms`
accepts `none` or `yes`. Symptom details are submitted to the symptom endpoint.

- `GET /crew` returns the synthetic roster with `id`, `name`, `role`, and `cmo`.
- Today metrics include `level` and `hold_reason` (`insufficient_baseline`,
  `zero_variance`, `missing_reading`, or null). Status messages support `?lang=ko`
  or `?lang=en` on Today and check-in. Guide text is currently English.
- `GET /mission` returns `clock`, `environment`, `one_way_delay_min`, and
  `next_window`. The demo uses a 12-minute one-way delay and windows at
  08:00 and 20:00 mission time.
- `POST /demo/clock` accepts `{"sol":16,"time":"14:00"}` or
  `{"advance":"2h"}`. The clock is process-local and resets on restart.

`POST /crew/c1/symptom` accepts `{"text":"I feel dizzy","lang":"en"}` and
returns an event ID. Read the saved symptom report and its original readings
with `GET /events/{id}`. Today's events appear in the Today response. Previous
event days are excluded from the baseline window.

The event endpoint returns `event_id`, `urgent`, and `needs_question`, with
`question` when an answer is needed. A warning bypasses the model. `urgent`
identifies a warning raised by the report's wording, independently of warnings
raised by the report's measurement snapshot.

1. If a question was returned, send `{"answer":"yes"}` or `{"answer":"no"}` to
   `POST /events/{id}/answer` (202).
2. Open `GET /events/{id}/stream` with EventSource. It emits `{"stage":"…"}` and
   ends with `done` or `hold`. The first stream runs the explanation step;
   later streams replay the saved stages.
3. Read `GET /events/{id}` for the persisted answer, explanation, verification
   runs, and hold reason. An explanation hold leaves the rule level intact.

The default model mode is `mock`. Set `MODEL=live` to use the local model
server described in [Model client](model/README.md). Without a matching local
evidence paragraph, the backend returns `hold` without generating an
explanation.

Set `CREW_HEALTH_EVIDENCE` to the path of a UTF-8 JSON array to load the team's
reviewed local paragraphs at startup. Each object has `id` (a unique paragraph
ID in the form `org:slug#pN`), `text`, `codes` (a nonempty list of symptom
codes), and `condition_id` from `contracts/enums.json`. The demo matches
paragraphs by symptom code. Code matches and citation checks do not validate
medical advice or guarantee that the text supports each sentence. The repo
does not bundle a reviewed evidence corpus.

`GET /docs` and `GET /docs/{id}` expose the same loaded evidence for the
Procedures screen. The document ID is the portion before `#pN`, and the
response keeps the original paragraph number. Evidence rows may include
`title`, `org`, and `kind`. Set each value consistently within a document.
An unconfigured corpus returns an empty document list. Swagger is at
`/api/docs`.

### Demo crew access

Use Settings to switch between C1–C4 and change whether the crew medical officer
can read the selected crew member's records. This preference is stored per crew
member and defaults to on. Owners can read and modify their own records. The
medical officer (C2) can read another member's records when allowed and can open
marked reports from the Crew page. The roster and transmission controls are
restricted to the medical officer. Turning access off hides that member's
packets and pauses their dispatch until access is restored.

For direct requests, pass `X-Demo-Viewer: c1` through `c4` (default `c1`).
EventSource passes the same ID in `demo_viewer`. `GET /settings` reads the
selected viewer's preference and `PUT /settings` accepts
`{"cmo_access":false}`. `POST /demo/viewer/{id}` validates a demo selection.
The caller supplies the role for rehearsal. This is not authentication and is
intended only for synthetic localhost data.

### Sign-in mode

Set `CREW_HEALTH_ACCESS_CODES` before starting the backend to enable sign-in.
Its value is a JSON object with keys `c1`, `c2`, `c3`, and `c4`. Give each
crew member a different randomly generated code of at least 16 characters.
Keep the codes out of source control. For local testing, use the same host name
in the frontend and API URLs, such as `127.0.0.1` for both.

The server derives the viewer from an HttpOnly cookie. Demo viewer selection
is disabled in this mode. Sessions expire after eight hours or on backend
restart. This setup is for one local backend process; it is not a production
identity system.

### Event follow-up

- `POST /events/{id}/share` persists the event's share flag for the crew medical
  officer. The demo does not send a notification or enforce viewer permissions.
- `POST /events/{id}/close` closes an event that is not a warning.
- `POST /events/{id}/override` closes an event with a reason from
  `contracts/enums.json` and an optional note, for example
  `{"reason":"action_done","note":"Scenario completed."}`.
- `POST /events/{id}/action/{index}/done` marks a response action complete.
  Only the event owner can write. The index is zero-based in
  `event.risk.actions`. Repeating a completion returns the stored result.

A verified explanation can expose response actions from the optional
`action_text` field on cited evidence paragraphs for the verified condition.
Use team-reviewed text for this field. The event stores that text and its
paragraph ID with the completion state.

These endpoints return the updated event. Repeating the same resolution is safe.
A conflicting resolution returns 409. Closed events remain in history with
their original readings and level. They stop contributing to the active Today
status, which still reflects any current reading warnings. Existing transmission
packets are retained.

## Transmission queue simulation

A warning symptom event creates a summary packet with a sequence number and a
SHA-256 hash of its canonical JSON. The packet contains the event ID, crew ID,
timestamp, level, codes, and flagged readings. The same payload and sequence
number are kept for retries.

- `GET /tx` lists packets in priority order.
- `POST /tx` queues an existing event with `{"event_id":1}`, or one daily
  summary per crew member with `{"daily":true}`. Repeating a request reuses
  the existing packet.
- `POST /tx/send` marks eligible packets as sent during the first 30 minutes
  of the 08:00 and 20:00 mission-time windows. An optional body uses the same
  format as `POST /tx`.
- `POST /tx/{seq}/receipt` accepts `{"status":"acked","attempt":1}` or
  `{"status":"missing","attempt":1}`. A missing packet can be sent again in
  a later window. A duplicate missing receipt returns HTTP 409. An ACK can
  still confirm the current attempt before a retry. Use the packet's current
  `attempts` value when sending a receipt.

The send and receipt routes simulate delivery; data stays in the local SQLite
database.

`POST /tx/{seq}/simulate` compares the saved packet with two signal amplitudes.
Send `{}` for defaults, or specify `narrow_amplitude`, `wide_amplitude`,
`noise_sd`, `trials`, and `seed`. The default test uses amplitudes ±1 and ±3,
unit Gaussian noise, and 100 trials. Both amplitudes receive the same noise
sample for each bit. The response reports bit error rates, exact packet
success rates, expected success under independent bit errors, and energy
relative to the narrow signal at equal symbol duration.

This experiment models additive noise while a link is available. It has no
error correction or framing overhead and does not change packet delivery
status. It runs independently of the mission clock and transmission window.

### Frontend integration

Use `X-Demo-Viewer: c2` for all transmission API calls in this walkthrough.

Render the queue from `GET /tx`. Each row has `seq`, `crew`, `event_id`,
`kind`, `priority`, `status`, `attempts`, `window_id`, `hash`, and `payload`.
Use the sequence number as the row key so a retry updates the same row.

1. Submit a synthetic warning report to `POST /crew/c1/symptom` with
   `{"text":"I have chest pain","lang":"en"}`. Find its packet by matching the
   returned `event_id` against the queue.
2. Set the demo clock to Sol 16 at 08:00, then call `POST /tx/send` with no
   body. The returned queue shows the first attempt as `sent`.
3. Post `missing` with the packet's current attempt number. Move the clock to
   20:00 and send again. Post `acked` with the new attempt number.
4. Compare either before or after sending by posting
   `{"wide_amplitude":5}` to `/tx/{seq}/simulate`. Display each of `narrow`
   and `wide` using `bit_error_rate` as a percentage, `successful_packets`
   out of `trials`, and `relative_energy_per_bit` as a multiplier. The
   response's `packet_bits` gives the payload size.
