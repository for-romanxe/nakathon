// client.js — the only place the UI gets data from.
// VITE_USE_FIXTURES=true (default) reads fixtures/*.json; false calls the FastAPI backend (CONTRACT §5).
// API fields are snake_case and are used as-is (CONTRACT §0-4).
import trendsFixture from './fixtures/trends.json'
import todayFixture from './fixtures/today.json'
import todayOthersFixture from './fixtures/today_others.json'
import crewFixture from './fixtures/crew.json'
import firstStepsFixture from './fixtures/first_steps.json'
import docsFixture from './fixtures/docs.json'
import txFixture from './fixtures/tx.json'
import missionFixture from './fixtures/mission.json'
import eventCautionFixture from './fixtures/event_caution.json'
import eventWarningFixture from './fixtures/event_warning.json'
import { PIPELINE_STAGES } from './contract.js'
import { CURRENT_CREW } from '../session.js'

export const USE_FIXTURES = import.meta.env.VITE_USE_FIXTURES !== 'false'
const API_BASE = import.meta.env.VITE_API_BASE ?? 'http://localhost:8000' // CONTRACT §1

// Korean status.text for c1–c4 in fixture mode (what the backend sends with ?lang=ko). A top-level map of its own,
// separate from the per-crew /today objects, so every crew id including c1 has an entry
const STATUS_TEXT_KO = todayOthersFixture.status_text_ko

// ---- Fixture-only mission clock: the demo clock moves it in memory, as POST /demo/clock does on the backend ----
const WINDOW_MINUTES = [8 * 60, 20 * 60] // comm windows 08:00 and 20:00 (backend/mission.py)
const hhmm = (m) => `${String(Math.floor(m / 60)).padStart(2, '0')}:${String(m % 60).padStart(2, '0')}`
const { _note: _missionNote, ...missionStart } = missionFixture
let fixtureMission = structuredClone(missionStart)
function moveFixtureClock(update) {
  const [h, m] = fixtureMission.clock.time.split(':').map(Number)
  let total = (fixtureMission.clock.sol - 1) * 1440 + h * 60 + m
  if (update.advance) {
    const n = Number.parseInt(update.advance, 10)
    total += update.advance.endsWith('h') ? n * 60 : n
  } else {
    const [uh, um] = update.time.split(':').map(Number)
    total = (update.sol - 1) * 1440 + uh * 60 + um
  }
  const minute = total % 1440
  const next = WINDOW_MINUTES.find((w) => w > minute) ?? WINDOW_MINUTES[0]
  fixtureMission = { ...fixtureMission, clock: { sol: Math.floor(total / 1440) + 1, time: hhmm(minute) }, next_window: hhmm(next) }
  return structuredClone(fixtureMission)
}

// ---- Fixture-only check-ins: kept per crew member and sol, so a check-in stays done for the person who made it ----
const fixtureCheckins = {} // "c3:16" -> { morning: true, evening: true }
function fixtureToday(crewId, lang) {
  const base = todayOthersFixture[crewId] ?? todayFixture
  // this session's fixture reports go only to the crew member who sent them
  const mine = Object.values(fixtureEvents).filter((e) => e.crew === crewId)
  const done = fixtureCheckins[`${crewId}:${fixtureMission.clock.sol}`] ?? {}
  const today = {
    ...base,
    events: [...base.events, ...mine].sort((a, b) => b.id - a.id),
    checkin: { ...base.checkin, ...(done.morning && { morning_done: true }), ...(done.evening && { evening_done: true }) },
    streak: (base.streak ?? 0) + (done.morning && !base.checkin?.morning_done ? 1 : 0),
  }
  // the backend localises status.text via ?lang; the fixtures are English, so swap in its Korean sentence
  const ko = lang === 'ko' && STATUS_TEXT_KO[crewId]
  return ko ? { ...today, status: { ...today.status, text: ko } } : today
}
// Fixture for POST /checkin: that crew member's /today with the check-in marked done
function checkinFixture(crewId, body, lang) {
  const key = `${crewId}:${fixtureMission.clock.sol}`
  fixtureCheckins[key] = { ...fixtureCheckins[key], [body.kind]: true }
  return fixtureToday(crewId, lang)
}

// ---- Fixture-only symptom flow (fake data; the real rules live in backend/events.py) ----
const fixtureEvents = {}
let fixtureNextId = 101
// Same phrases as backend/events.py WARNING_PHRASES + CONSCIOUSNESS_CHANGE, so rehearsed demo lines behave the same
const FIXTURE_URGENT = /\bchest pain\b|흉통|가슴\s*통증|가슴이\s*아파|\bshortness of breath\b|\b(can't|cannot) breathe\b|호흡곤란|숨을\s*못\s*쉬|숨이\s*안\s*쉬어|\bkill myself\b|\bwant to die\b|\bend it all\b|죽고\s*싶|다\s*끝내고\s*싶|\bloss of consciousness\b|\bunresponsive\b|의식 소실|의식이 없/i

function fixtureSymptom({ crewId, text }) {
  const urgent = FIXTURE_URGENT.test(text)
  const base = urgent ? eventWarningFixture : eventCautionFixture
  const id = fixtureNextId++
  fixtureEvents[id] = { ...structuredClone(base), id, crew: crewId, symptom_text: text } // the reporter owns it
  return urgent
    ? { event_id: id, needs_question: false }
    : { event_id: id, needs_question: true, question: 'Is it worse when you stand up?' }
}

function fixtureEvent(id) {
  return fixtureEvents[id] ?? { ...eventCautionFixture, id: Number(id) }
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
  const headers = { 'X-Demo-Viewer': CURRENT_CREW, ...options.headers }
  if (options.body) headers['Content-Type'] = 'application/json'
  const res = await fetch(`${API_BASE}${path}`, { ...options, headers, credentials: 'include' })
  const body = res.status === 204 ? null : await res.json().catch(() => null)
  if (!res.ok) {
    // CONTRACT §5 error shape: { "error": { "code", "message" } }
    throw new ApiError(body?.error?.code ?? `http_${res.status}`, body?.error?.message ?? res.statusText)
  }
  return body
}

export const api = {
  getMedicationReferences: () => request('/medication-references'),
  getMedicationIntakes: (crewId) => request(`/crew/${crewId}/medication-intakes`),
  getMedicationIntakeSummary: (crewId, productId, signal) =>
    request(`/crew/${crewId}/medication-intake-summary?${new URLSearchParams({ product_id: productId })}`, null, { signal }),
  recordMedicationIntake: (crewId, entry) => request(`/crew/${crewId}/medication-intakes`, null, {
    method: 'POST', body: JSON.stringify(entry),
  }),
  getTrends: (crewId, metric, days) => request(
    `/crew/${crewId}/trends?${new URLSearchParams({ metric, days })}`,
    () => {
      // c1's real readings copied from the backend; keep the last `days` of them
      const series = trendsFixture[metric] ?? { points: [], baseline: { mean: null, sd: null }, events: [] }
      return { ...series, points: series.points.slice(-days) }
    },
  ),
  // GET/PUT /crew/{id}/preflight -> { values: { metric: { value, source } } }; PUT body { values: { metric: number } }
  // No fixture: the form shows a connect-the-backend message instead of faking storage
  getPreflight: (crewId) => request(`/crew/${crewId}/preflight`, () => {
    throw new ApiError('fixture_unsupported', 'Preflight values need the backend')
  }),
  putPreflight: (crewId, body) => request(`/crew/${crewId}/preflight`, () => {
    throw new ApiError('fixture_unsupported', 'Preflight values need the backend')
  }, { method: 'PUT', body: JSON.stringify(body) }),
  getSession: () => request('/session', { login_required: false, crew_id: null }),
  login: (crew_id, access_code) => request('/session/login', null, {
    method: 'POST', body: JSON.stringify({ crew_id, access_code }),
  }),
  logout: () => request('/session/logout', null, { method: 'POST' }),
  selectViewer: (id) => request(`/demo/viewer/${id}`, () => ({ id }), { method: 'POST' }),
  getSettings: () => request('/settings', () => ({
    cmo_access: localStorage.getItem(`crew-health-cmo-${CURRENT_CREW}`) !== 'false',
  })),
  setSettings: (settings) => request('/settings', () => {
    localStorage.setItem(`crew-health-cmo-${CURRENT_CREW}`, String(settings.cmo_access))
    return settings
  }, { method: 'PUT', body: JSON.stringify(settings) }),
  // GET /crew/{id}/today -> { status:{level,text}, guide, metrics:[{metric,value,baseline,sd,z}], events, checkin, streak }
  // ?lang=ko localises status.text (guide lines are English for now)
  getToday: (crewId, lang) =>
    request(`/crew/${crewId}/today?lang=${lang}`, () => fixtureToday(crewId, lang)),
  // POST /crew/{id}/checkin {kind, answers, free_text?} -> updated /today (CONTRACT §5)
  // answers (agreed with backend): { sleep_quality, mood, fatigue: 1-5 ints, symptoms?: "none"|"yes" }
  postCheckin: (crewId, body, lang) =>
    request(`/crew/${crewId}/checkin?lang=${lang}`, () => checkinFixture(crewId, body, lang), { method: 'POST', body: JSON.stringify(body) }),
  // POST /crew/{id}/symptom {text, lang} -> { event_id, needs_question, question? } (CONTRACT §5)
  postSymptom: (crewId, text, lang) =>
    request(`/crew/${crewId}/symptom`, () => fixtureSymptom({ crewId, text }), {
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
    request(`/events/${eventId}`, () => fixtureEvent(eventId)),
  shareEvent: (id) =>
    request(`/events/${id}/share`, () => (fixtureEvents[id] = { ...fixtureEvent(id), shared: true }), { method: 'POST' }),
  completeAction: (id, index) => request(`/events/${id}/action/${index}/done`, () => {
    const event = structuredClone(fixtureEvent(id))
    event.risk.actions[index].done = true
    fixtureEvents[id] = event
    return event
  }, { method: 'POST' }),
  closeEvent: (id) =>
    request(`/events/${id}/close`, () => (fixtureEvents[id] = {
      ...fixtureEvent(id), status: 'closed', closed_reason: 'resolved',
    }), { method: 'POST' }),
  overrideEvent: (id, reason) =>
    request(`/events/${id}/override`, () => (fixtureEvents[id] = {
      ...fixtureEvent(id), status: 'closed', closed_reason: reason, override: { reason },
    }), { method: 'POST', body: JSON.stringify({ reason }) }),
  // GET /tx -> transmission packets to Earth, warning first (seq, event_id, priority, status, attempts, ...)
  getTx: () => request('/tx', txFixture),
  // POST /tx {event_id} -> queues an event summary for Earth (warning events are queued by the backend already)
  queueTx: (eventId) => request('/tx', txFixture, { method: 'POST', body: JSON.stringify({ event_id: eventId }) }),
  // POST /tx {daily:true} -> queues today's summary for every crew member (used for a metrics-only warning)
  queueDaily: () => request('/tx', txFixture, { method: 'POST', body: JSON.stringify({ daily: true }) }),
  // POST /tx/send -> sends queued packets if a comm window is open now; returns the queue
  sendTx: () => request('/tx/send', txFixture, { method: 'POST' }),
  getDocs: () => request('/docs', docsFixture.docs).then((docs) => {
    if (!Array.isArray(docs)) throw new ApiError('invalid_docs', 'Invalid document list.')
    return { docs, sample: USE_FIXTURES }
  }),
  // GET /docs/{id} -> {id,title,org,kind,paragraphs:[{n,text}]}; fixture only in fixture mode. Unknown id -> ApiError doc_not_found
  getDoc: (id) => {
    const fromFixture = () => {
      const doc = docsFixture.docs.find((d) => d.id === id)
      if (!doc) throw new ApiError('doc_not_found', 'Document not on device.')
      return structuredClone(doc)
    }
    if (USE_FIXTURES) return wait(150).then(fromFixture)
    return request(`/docs/${encodeURIComponent(id)}`, null)
  },
  // A sample citation is only clickable when its exact paragraph exists.
  getFirstSteps: () => {
    if (!USE_FIXTURES) return Promise.resolve({})
    return Promise.resolve(Object.fromEntries(
      Object.entries(firstStepsFixture).filter(([key]) => key !== '_note').map(([key, item]) => {
        const [id, paragraph] = item.doc.split('#p')
        const exists = docsFixture.docs.find(doc => doc.id === id)?.paragraphs.some(p => p.n === Number(paragraph))
        return [key, { ...item, doc: exists ? item.doc : null }]
      }),
    ))
  },
  // GET /crew -> [{ id: "c1", name: "C1", ... }] — display names come from here
  getCrew: () => request('/crew', crewFixture),
  // GET /mission -> { clock:{sol,time}, environment, one_way_delay_min, next_window }
  getMission: () => request('/mission', () => structuredClone(fixtureMission)),
  recordReceipt: (seq, status, attempt) =>
    request(`/tx/${seq}/receipt`, [], { method: 'POST', body: JSON.stringify({ status, attempt }) }),
  simulateTransmission: (seq, amplitude) =>
    request(`/tx/${seq}/simulate`, null, { method: 'POST', body: JSON.stringify({ wide_amplitude: amplitude }) }),
  setDemoClock: (clock) =>
    request('/demo/clock', () => moveFixtureClock(clock), { method: 'POST', body: JSON.stringify(clock) }),
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
      source = new EventSource(`${API_BASE}/events/${eventId}/stream?demo_viewer=${CURRENT_CREW}`, { withCredentials: true })
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
