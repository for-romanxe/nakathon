# Crew Health demo API

Run from the repository root:

```sh
python -m pip install -r backend/requirements.txt
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

The server creates and seeds `data/crew-health.sqlite3` on startup. It keeps
existing rows across restarts. The demo clock starts at Sol 16, 06:12 and exposes
synthetic crew data on localhost. Use only synthetic data with this demo endpoint.

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

The event endpoint uses demo keyword rules for urgent symptoms. Model
interpretation, follow-up questions, and explanation verification are pending.
Crew access controls are pending. Use these localhost endpoints with synthetic
data only.

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
