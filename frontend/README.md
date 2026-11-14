# Crew Health — frontend

React + Vite. Port 5173 (CONTRACT §1). English is the primary UI language, Korean is the second (`src/i18n/en.js`, `src/i18n/ko.js`).

## Run

```sh
cd frontend
npm install
npm run dev
```

Open http://localhost:5173.

## Data source

- Default: fixtures in `src/api/fixtures/` (shaped like `backend/today.py`).
- Real backend: create `frontend/.env.development.local` with `VITE_USE_FIXTURES=false`, run the backend on port 8000, restart `npm run dev`.
- All requests go through `src/api/client.js`. Shared enums are loaded from `../contracts/enums.json` via `src/api/contract.js`.

## Screens

Routes follow CONTRACT §5. The Today screen (`/today`) shows the daily guide
and supports morning check-in. The Crew screen (`/crew`) shows the demo roster
and the Earth transmission queue.

With the demo backend connected, open Crew and queue daily summaries. Advance
the demo clock to the next transmission window and send the queued packets.
Mark a packet missing, advance to the next window, and send it again before
confirming receipt. The sequence number and hash stay the same across attempts.
Use **Compare signals** on a packet to see how amplitude affects bit errors,
successful packets, and relative energy. The queue controls simulate delivery.
