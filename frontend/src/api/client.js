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

export const USE_FIXTURES = import.meta.env.VITE_USE_FIXTURES !== 'false'
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
// Same phrases as backend/events.py WARNING_PHRASES + CONSCIOUSNESS_CHANGE, so rehearsed demo lines behave the same
const FIXTURE_URGENT = /\bchest pain\b|흉통|가슴 통증|가슴이 아파|\bshortness of breath\b|\b(can't|cannot) breathe\b|호흡곤란|숨을 못 쉬|\bkill myself\b|\bwant to die\b|죽고 싶|\bloss of consciousness\b|\bunresponsive\b|의식 소실|의식이 없/i

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
const STREAM_LIMIT_MS = 60000 // longest a pipeline may take before the UI stops waiting

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
  getToday: (crewId, lang) =>
    request(`/crew/${crewId}/today?lang=${lang}`, () => ({
      ...todayFixture,
      events: [...todayFixture.events, ...Object.values(fixtureEvents)], // fixture-only reports from this session
    })),
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
  // POST /events/{id}/answer {answer:"yes"|"no"} -> 202. Resolves { saved }: false when the backend has no
  // answer endpoint yet (404), so the UI can say the answer was not saved instead of pretending it was
  postAnswer: (eventId, answer) =>
    request(`/events/${eventId}/answer`, null, { method: 'POST', body: JSON.stringify({ answer }) })
      .then(() => ({ saved: true }))
      .catch((e) => {
        if (e.code === 'http_404' || e.code === 'not_found') return { saved: false }
        throw e
      }),
  // GET /events/{id} -> event (spec §9: findings, codes, risk, explanation, runs, verified, ...)
  getEvent: (eventId) =>
    request(`/events/${eventId}`, () => fixtureEvents[eventId] ?? { ...eventCautionFixture, id: Number(eventId) }),
  // GET /tx -> transmission packets to Earth, warning first (seq, event_id, priority, status, attempts, ...)
  getTx: () => request('/tx', txFixture),
  // POST /tx {event_id} -> queues an event summary for Earth (warning events are queued by the backend already)
  queueTx: (eventId) => request('/tx', txFixture, { method: 'POST', body: JSON.stringify({ event_id: eventId }) }),
  // POST /tx {daily:true} -> queues today's summary for every crew member (used for a metrics-only warning)
  queueDaily: () => request('/tx', txFixture, { method: 'POST', body: JSON.stringify({ daily: true }) }),
  // POST /tx/send -> sends queued packets if a comm window is open now; returns the queue
  sendTx: () => request('/tx/send', txFixture, { method: 'POST' }),
  // First steps of the emergency procedure per warning code. No /docs endpoint yet: placeholder fixture only
  getFirstSteps: () => Promise.resolve(firstStepsFixture),
  // GET /crew -> [{ id: "c1", name: "C1", ... }] — display names come from here
  getCrew: () => request('/crew', crewFixture),
  // GET /mission -> { clock:{sol,time}, environment, one_way_delay_min, next_window }
  getMission: () => request('/mission', missionFixture),
  getTransmissions: () => request('/tx', []),
  queueDailySummaries: () => request('/tx', [], { method: 'POST', body: JSON.stringify({ daily: true }) }),
  sendTransmissions: () => request('/tx/send', [], { method: 'POST' }),
  recordReceipt: (seq, status, attempt) =>
    request(`/tx/${seq}/receipt`, [], { method: 'POST', body: JSON.stringify({ status, attempt }) }),
  simulateTransmission: (seq, amplitude) =>
    request(`/tx/${seq}/simulate`, null, { method: 'POST', body: JSON.stringify({ wide_amplitude: amplitude }) }),
  setDemoClock: (clock) =>
    request('/demo/clock', missionFixture, { method: 'POST', body: JSON.stringify(clock) }),
}

// Pipeline progress for one event (CONTRACT §4 stage names). Calls onStage(stage) as stages arrive and
// resolves with how it ended — only what actually happened:
//   "done" | "hold"  the stream said so
//   "unavailable"    the stream could not be opened at all (no endpoint yet): progress unknown, not "done"
//   "interrupted"    the stream broke after some stages: shown as stopped, never as "done"
// Live: SSE GET /events/{id}/stream.
export function runPipeline(eventId, { urgent, onStage }) {
  if (USE_FIXTURES) {
    // urgent reports skip the model: rules -> done (spec S9)
    const stages = urgent ? ['collect', 'rules', 'done'] : PIPELINE_STAGES.filter((s) => s !== 'hold' && s !== 'question')
    return stages.reduce((p, stage) => p.then(() => wait(450)).then(() => onStage(stage)), Promise.resolve()).then(() => 'done')
  }
  return new Promise((resolve) => {
    let source
    try {
      source = new EventSource(`${API_BASE}/events/${eventId}/stream`)
    } catch {
      resolve('unavailable')
      return
    }
    let seen = 0
    const finish = (result) => {
      clearTimeout(timer)
      source.close()
      resolve(result)
    }
    // a stream that never sends done/hold must not keep the chat waiting forever
    const timer = setTimeout(() => finish(seen === 0 ? 'unavailable' : 'interrupted'), STREAM_LIMIT_MS)
    source.onmessage = (msg) => {
      seen += 1
      try {
        const { stage } = JSON.parse(msg.data)
        onStage(stage)
        if (stage === 'done' || stage === 'hold') finish(stage)
      } catch {
        finish('interrupted')
      }
    }
    // A passing network error leaves the source CONNECTING and the browser reconnects by itself, so keep
    // waiting (the 60 s limit still applies). Stop only when it gave up for good (CLOSED, e.g. 404).
    source.onerror = () => {
      if (source.readyState === EventSource.CLOSED) finish(seen === 0 ? 'unavailable' : 'interrupted')
    }
  })
}
