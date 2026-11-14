// client.js — the only place the UI gets data from.
// VITE_USE_FIXTURES=true (default) reads fixtures/*.json; false calls the FastAPI backend (CONTRACT §5).
// API fields are snake_case and are used as-is (CONTRACT §0-4).
import todayFixture from './fixtures/today.json'
import crewFixture from './fixtures/crew.json'
import missionFixture from './fixtures/mission.json'
import eventCautionFixture from './fixtures/event_caution.json'
import eventWarningFixture from './fixtures/event_warning.json'
import txFixture from './fixtures/tx.json'
import firstStepsFixture from './fixtures/first_steps.json'
import { PIPELINE_STAGES } from './contract.js'

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

// ---- Fixture-only symptom flow (fake data; the real rules live in backend/events.py) ----
const fixtureEvents = {}
let fixtureNextId = 101
const FIXTURE_URGENT = /chest pain|can't breathe|want to die|흉통|가슴|숨을 못|숨이 안|죽고\s*싶/i

function fixtureSymptom({ text }) {
  const urgent = FIXTURE_URGENT.test(text)
  const base = urgent ? eventWarningFixture : eventCautionFixture
  const id = fixtureNextId++
  fixtureEvents[id] = { ...structuredClone(base), id, symptom_text: text }
  return urgent
    ? { event_id: id, needs_question: false }
    : { event_id: id, needs_question: true, question: 'Is it worse when you stand up?' }
}

export class ApiError extends Error {
  constructor(code, message) {
    super(message)
    this.code = code
  }
}

const wait = (ms) => new Promise((r) => setTimeout(r, ms))

async function request(path, fixture, options = {}) {
  if (USE_FIXTURES) {
    await wait(300) // small delay so the loading state is visible
    return structuredClone(typeof fixture === 'function' ? fixture() : fixture)
  }
  // Content-Type only when there is a body, so plain GETs skip the CORS preflight
  const headers = options.body ? { 'Content-Type': 'application/json', ...options.headers } : options.headers
  const res = await fetch(`${API_BASE}${path}`, { ...options, headers })
  const body = res.status === 204 ? null : await res.json().catch(() => null)
  if (!res.ok) {
    // CONTRACT §5 error shape: { "error": { "code", "message" } }
    throw new ApiError(body?.error?.code ?? `http_${res.status}`, body?.error?.message ?? res.statusText)
  }
  return body
}

export const api = {
  // GET /crew/{id}/today -> { status:{level,text}, guide, metrics:[{metric,value,baseline,sd,z}], events, checkin, streak }
  // ?lang=ko localises status.text (guide lines are English for now)
  getToday: (crewId, lang) => request(`/crew/${crewId}/today?lang=${lang}`, todayFixture),
  // POST /crew/{id}/checkin {kind, answers, free_text?} -> updated /today (CONTRACT §5)
  // answers (agreed with backend): { sleep_quality, mood, fatigue: 1-5 ints, symptoms?: "none"|"yes" }
  postCheckin: (crewId, body, lang) =>
    request(`/crew/${crewId}/checkin?lang=${lang}`, checkinFixture(body), { method: 'POST', body: JSON.stringify(body) }),
  // POST /crew/{id}/symptom {text, lang} -> { event_id, needs_question, question? } (CONTRACT §5)
  postSymptom: (crewId, text, lang) =>
    request(`/crew/${crewId}/symptom`, () => fixtureSymptom({ text }), {
      method: 'POST',
      body: JSON.stringify({ text, lang }),
    }),
  // POST /events/{id}/answer {answer:"yes"|"no"} -> 202. Not on the backend yet: a 404 is ignored
  postAnswer: (eventId, answer) =>
    request(`/events/${eventId}/answer`, null, { method: 'POST', body: JSON.stringify({ answer }) }).catch((e) => {
      if (e.code !== 'http_404' && e.code !== 'not_found') throw e
    }),
  // GET /events/{id} -> event (spec §9: findings, codes, risk, explanation, runs, verified, ...)
  getEvent: (eventId) =>
    request(`/events/${eventId}`, () => fixtureEvents[eventId] ?? { ...eventCautionFixture, id: Number(eventId) }),
  // GET /tx -> transmission packets to Earth, warning first (seq, event_id, priority, status, attempts, ...)
  getTx: () => request('/tx', txFixture),
  // POST /tx {event_id} -> queues an event summary for Earth (warning events are queued by the backend already)
  queueTx: (eventId) => request('/tx', txFixture, { method: 'POST', body: JSON.stringify({ event_id: eventId }) }),
  // POST /tx/send -> sends queued packets if a comm window is open now; returns the queue
  sendTx: () => request('/tx/send', txFixture, { method: 'POST' }),
  // First steps of the emergency procedure per warning code. No /docs endpoint yet: placeholder fixture only
  getFirstSteps: () => Promise.resolve(firstStepsFixture),
  // GET /crew -> [{ id: "c1", name: "C1", ... }] — display names come from here
  getCrew: () => request('/crew', crewFixture),
  // GET /mission -> { clock:{sol,time}, environment, one_way_delay_min, next_window }
  getMission: () => request('/mission', missionFixture),
}

// Pipeline progress for one event (CONTRACT §4 stage names). Calls onStage(stage) as stages arrive and
// resolves with the final stage ("done" or "hold").
// Live: SSE GET /events/{id}/stream. The backend has no stream yet, so a failed stream resolves "done".
export function runPipeline(eventId, { urgent, onStage }) {
  if (USE_FIXTURES) {
    // urgent reports skip the model: rules -> done (spec S9)
    const stages = urgent ? ['collect', 'rules', 'done'] : PIPELINE_STAGES.filter((s) => s !== 'hold' && s !== 'question')
    return stages.reduce((p, stage) => p.then(() => wait(450)).then(() => onStage(stage)), Promise.resolve()).then(() => 'done')
  }
  return new Promise((resolve) => {
    const source = new EventSource(`${API_BASE}/events/${eventId}/stream`)
    source.onmessage = (msg) => {
      const { stage } = JSON.parse(msg.data)
      onStage(stage)
      if (stage === 'done' || stage === 'hold') {
        source.close()
        resolve(stage)
      }
    }
    source.onerror = () => {
      source.close()
      resolve('done')
    }
  })
}
