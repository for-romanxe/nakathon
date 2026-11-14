# Crew Health demo API

Run from the repository root:

```sh
python -m pip install -r backend/requirements.txt
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

The server creates and seeds `data/crew-health.sqlite3` on startup. It keeps
existing rows across restarts. The API uses a fixed demo day (Sol 16) and exposes
synthetic crew data on localhost. Use only synthetic data with this demo endpoint.

| Request | Expected status level |
| --- | --- |
| `GET /crew/c1/today` | `caution` |
| `GET /crew/c2/today` | `normal` |
| `GET /crew/c3/today` | `hold` |
| `GET /crew/c4/today` | `advisory` |

The baseline uses population standard deviation over daily averages for the
previous 14 sols. A missing day or zero variance makes the corresponding
z-score unavailable. The seeded readings are scenario fixtures and the
thresholds reproduce the team's demo rules.

Display names are C1 through C4. Crew IDs remain `c1` through `c4` in storage
and both spellings work in these URLs.

`POST /crew/c1/checkin` saves a check-in and returns the updated Today response.
Example morning request:

```json
{"kind":"morning","answers":{"sleep_quality":4,"mood":3,"fatigue":2}}
```

Morning submissions mark the sleep and mood review items complete and update
the activity review based on the existing rule status. Submitting the same
kind for the same sol updates the existing entry. `free_text` is optional
and stored as entered.

Event-day exclusions, crew access controls, and symptom handling are subsequent
integration work. The frontend check-in form still needs to call the endpoint.
