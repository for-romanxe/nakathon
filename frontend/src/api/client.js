// client.js — the only place the UI gets data from.
// VITE_USE_FIXTURES=true (default) reads fixtures/*.json; false calls the FastAPI backend (CONTRACT §5).
// API fields are snake_case and are used as-is (CONTRACT §0-4).
import todayFixture from './fixtures/today.json'
import crewFixture from './fixtures/crew.json'
import missionFixture from './fixtures/mission.json'

const USE_FIXTURES = import.meta.env.VITE_USE_FIXTURES !== 'false'
const API_BASE = import.meta.env.VITE_API_BASE ?? 'http://localhost:8000' // CONTRACT §1

// Fixture for POST /checkin: the updated /today with the check-in marked done
function checkinFixture(body) {
  return {
    ...todayFixture,
    checkin: { ...todayFixture.checkin, [`${body.kind}_done`]: true },
    streak: todayFixture.streak + (body.kind === 'morning' ? 1 : 0),
  }
}

export class ApiError extends Error {
  constructor(code, message) {
    super(message)
    this.code = code
  }
}

async function request(path, fixture, options = {}) {
  if (USE_FIXTURES) {
    await new Promise((r) => setTimeout(r, 300)) // small delay so the loading state is visible
    return structuredClone(fixture)
  }
  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: { 'Content-Type': 'application/json', ...options.headers },
  })
  const body = res.status === 204 ? null : await res.json().catch(() => null)
  if (!res.ok) {
    // CONTRACT §5 error shape: { "error": { "code", "message" } }
    throw new ApiError(body?.error?.code ?? `http_${res.status}`, body?.error?.message ?? res.statusText)
  }
  return body
}

export const api = {
  // GET /crew/{id}/today -> { status:{level,text}, guide, metrics:[{metric,value,baseline,sd,z}], events, checkin, streak }
  // lang is sent so the backend can localise status.text and guide lines (requested; ignored until supported)
  getToday: (crewId, lang) => request(`/crew/${crewId}/today?lang=${lang}`, todayFixture),
  // POST /crew/{id}/checkin {kind, answers, free_text?} -> updated /today (CONTRACT §5)
  // answers shape is our proposal (spec §8): { sleep_quality, mood, fatigue: 1-5, symptoms: "none"|"yes" }
  postCheckin: (crewId, body) =>
    request(`/crew/${crewId}/checkin`, checkinFixture(body), { method: 'POST', body: JSON.stringify(body) }),
  // GET /crew -> crew list (CONTRACT: CMO view). Used for names until /today carries the crew profile
  getCrew: () => request('/crew', crewFixture),
  // Mission clock, environment, comm delay, next window. Not in CONTRACT §5 yet — fixture only
  getMission: () => request('/mission', missionFixture),
}
