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

Routes follow CONTRACT §5: `/today /body /trends /log /procedures /crew /settings /events/:id /warning`. Only `/today` is built so far.
