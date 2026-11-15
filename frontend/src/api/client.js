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
import habitatFixture from './fixtures/habitat_actions.json'
import procedureFixture from './fixtures/procedure.json'
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
// Comms state as planned in issue #47 §3: blackout from Sol 43 00:00 up to (not including) Sol 57 00:00, otherwise
// connected while a 30-minute window is open and delayed in between. TODO: the backend will own these values;
// until GET /mission sends them, only fixture mode shows the autonomy dial.
const BLACKOUT = { start: 43, end: 57 }
const WINDOW_OPEN_MINUTES = 30
const inBlackout = (sol) => sol >= BLACKOUT.start && sol < BLACKOUT.end
function withComms(m) {
  const [h, min] = m.clock.time.split(':').map(Number)
  const minute = h * 60 + min
  const { sol } = m.clock
  const blackout = inBlackout(sol)
  const open = WINDOW_MINUTES.some((w) => minute >= w && minute < w + WINDOW_OPEN_MINUTES)
  // next_window_at = the next window that starts after now (like next_window) in which a packet can really go out,
  // so a window inside the blackout is skipped: Sol 42 21:00 -> Sol 57 08:00, not Sol 43 08:00
  const next = WINDOW_MINUTES.find((w) => w > minute)
  const nextSol = next != null ? sol : sol + 1
  const at = inBlackout(nextSol)
    ? { sol: BLACKOUT.end, time: hhmm(WINDOW_MINUTES[0]) }
    : { sol: nextSol, time: hhmm(next ?? WINDOW_MINUTES[0]) }
  return {
    ...m,
    next_window: at.time, // equals next_window_at.time (CONTRACT §5.1, #51)
    comms_state: blackout ? 'blackout' : open ? 'connected' : 'delayed',
    blackout_start_sol: BLACKOUT.start,
    blackout_end_sol: BLACKOUT.end,
    blackout_days_remaining: blackout ? BLACKOUT.end - sol : 0, // 0 outside the blackout, as the backend sends
    next_window_at: at,
    simulation: true,
  }
}
const { _note: _missionNote, ...missionStart } = missionFixture
let fixtureMission = withComms(structuredClone(missionStart))
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
  fixtureMission = withComms({ ...fixtureMission, clock: { sol: Math.floor(total / 1440) + 1, time: hhmm(minute) } })
  return structuredClone(fixtureMission)
}

// ---- Fixture-only habitat adjustments (#47 §3): approve / undo change them in memory. On the sol they were made
// they show as they are now; the next sol an applied one is released with its before / after outcome, an undone
// one stays undone and an unanswered proposal is gone. Other sols and crew members have none ----
const fixtureHabitat = {} // id -> { status, approved_by }
const pickLang = (v, lang) => (v && typeof v === 'object' ? (v[lang] ?? v.en) : v)
function fixtureHabitatAction(a, lang) {
  const now = { ...a, ...fixtureHabitat[a.id] }
  const sol = fixtureMission.clock.sol
  if (sol === a.sol + 1) {
    if (now.status === 'proposed') return null
    if (now.status === 'applied') now.status = 'released'
  } else if (sol !== a.sol) return null
  return {
    ...now,
    before: pickLang(now.before, lang),
    after: pickLang(now.after, lang),
    reason_text: pickLang(now.reason_text, lang),
    outcome: now.status === 'released' ? now.outcome : null,
  }
}
function fixtureHabitatList(crewId, lang) {
  return habitatFixture.actions.filter((a) => a.crew === crewId).map((a) => fixtureHabitatAction(a, lang)).filter(Boolean)
}
function fixtureHabitatSet(id, from, change, lang) {
  const a = habitatFixture.actions.find((x) => x.id === id)
  const cur = a && fixtureHabitatAction(a, lang)
  if (!cur) throw new ApiError('action_not_found', 'No such adjustment') // same codes as the backend (#59)
  if (!from.includes(cur.status)) throw new ApiError('action_stale', `Adjustment is ${cur.status}`)
  fixtureHabitat[id] = { ...fixtureHabitat[id], ...change }
  return fixtureHabitatAction(a, lang)
}

// ---- Fixture-only procedure with two-person consent (#47 §3). Consents live in localStorage so two tabs (C1, C3)
// share them, as they would through the backend. A procedure exists only for an urgent report made in fixture
// mode: the reporter is recorded as the patient when the report is made (fixtureSymptom). An event no tab has
// recorded has no procedure; the patient is never guessed ----
const PROC_KEY = 'fixture-procedure' // { [eventId]: { patient, approvals: { [stepId]: [{ crew, at }] } } }
function procStore() {
  try { return JSON.parse(localStorage.getItem(PROC_KEY)) ?? {} } catch { return {} }
}
function procSave(store) {
  try { localStorage.setItem(PROC_KEY, JSON.stringify(store)) } catch { /* private window: this tab only */ }
}
// A number counter shared by every tab (localStorage); without storage this tab keeps its own
const localCounters = {}
function nextSharedNumber(key, first) {
  let n = Math.max(first, localCounters[key] ?? first)
  try {
    n = Math.max(n, Number.parseInt(localStorage.getItem(key), 10) || 0)
    localStorage.setItem(key, String(n + 1))
  } catch { /* this tab only */ }
  localCounters[key] = n + 1
  return n
}
function procRegister(eventId, patient) {
  const store = procStore()
  store[String(eventId)] = { patient, approvals: {} }
  procSave(store)
}
const CONSENT_ORDER = ['c1', 'c3', 'c2', 'c4']
function fixtureProcedure(eventId, lang) {
  const rec = procStore()[String(eventId)]
  if (!rec?.patient) throw new ApiError('not_found', 'No procedure for this event')
  const { patient, approvals = {} } = rec
  const consenters = CONSENT_ORDER.filter((c) => c !== patient).slice(0, 2)
  const { _note: _procNote, ...base } = procedureFixture
  const steps = base.steps.map((s) => {
    // only designated consenters count, each once, however the stored list looks
    const got = (approvals[s.step_id] ?? []).filter((a, i, all) =>
      consenters.includes(a?.crew) && all.findIndex((b) => b?.crew === a.crew) === i)
    return { ...s, text: pickLang(s.text, lang), approvals: got, done: s.needs_consent ? got.length >= base.required : false }
  })
  return {
    ...base,
    event_id: Number(eventId),
    patient,
    consenters,
    steps,
    current_step: steps.find((s) => s.needs_consent && !s.done)?.step_id ?? null,
  }
}
function fixtureApprove(eventId, stepId, lang) {
  const p = fixtureProcedure(eventId, lang)
  if (!p.consenters.includes(CURRENT_CREW)) throw new ApiError('forbidden', 'Not a designated consenter')
  const step = p.steps.find((s) => s.step_id === stepId)
  if (step?.approvals.some((a) => a.crew === CURRENT_CREW)) return p // the same consent again: same result
  if (stepId !== p.current_step) throw new ApiError('state_conflict', 'Not the current step')
  const store = procStore()
  const rec = store[String(eventId)]
  rec.approvals = { ...rec.approvals, [stepId]: [...(rec.approvals?.[stepId] ?? []), { crew: CURRENT_CREW, at: fixtureMission.clock }] }
  procSave(store)
  const after = fixtureProcedure(eventId, lang)
  // the consent that completes the procedure saves its report: its own report id and packet seq, kept with it
  if (after.current_step === null && !rec.report) {
    rec.report = { report_id: nextSharedNumber('fixture-next-report-id', 1), seq: nextSharedNumber('fixture-next-seq', 101) }
    procSave(store)
  }
  return after
}
// What /today would list for a consenter: steps still waiting for this crew member's consent
function fixtureConsentRequests(crewId) {
  return Object.keys(procStore()).flatMap((id) => {
    let p
    try { p = fixtureProcedure(id, 'en') } catch { return [] }
    const step = p.steps.find((s) => s.step_id === p.current_step)
    if (!step || !p.consenters.includes(crewId) || step.approvals.some((a) => a.crew === crewId)) return []
    return [{ event_id: p.event_id, patient: p.patient, step_id: step.step_id, approvals: step.approvals.length, required: p.required }]
  })
}
// What GET /earth-reports would hold: one report per procedure whose consent is complete, readable by the patient
// and the medical officer. The warning packet is held during the blackout and waits in the queue otherwise.
function fixtureEarthReports(crewId) {
  const blackout = fixtureMission.comms_state === 'blackout'
  const store = procStore()
  return Object.keys(store).flatMap((id) => {
    const report = store[id]?.report // ids handed out when the consent completed; none -> no report
    if (!report) return []
    let p
    try { p = fixtureProcedure(id, 'en') } catch { return [] }
    if (!(crewId === 'c2' || crewId === p.patient)) return []
    const approvals = p.steps.flatMap((s) => s.approvals).map((a) => ({ crew_id: a.crew, at: a.at }))
    return [{
      report_id: report.report_id, event_id: p.event_id, created_at: null, level: 'warning',
      metrics: [], actions: [], cite_ids: p.steps.map((s) => s.cite_id).filter(Boolean), approvals,
      packet: { seq: report.seq, status: blackout ? 'held' : 'queued', held_reason: blackout ? 'blackout' : null },
    }]
  }).sort((a, b) => a.report_id - b.report_id)
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
    consent_requests: fixtureConsentRequests(crewId), // draft field (#47 FE-03): another crew member's step needs me
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
// Event ids come from one counter in localStorage, so two tabs (C4 reporting, C1 consenting) never hand out the
// same id for different reports. Without storage (private window) the tab keeps its own counter.
const EVENT_ID_KEY = 'fixture-next-event-id'
function nextFixtureEventId() {
  let id = fixtureNextId
  try {
    id = Math.max(id, Number.parseInt(localStorage.getItem(EVENT_ID_KEY), 10) || 0)
    localStorage.setItem(EVENT_ID_KEY, String(id + 1))
  } catch { /* this tab only */ }
  fixtureNextId = id + 1
  return id
}
// Same phrases as backend/events.py WARNING_PHRASES + CONSCIOUSNESS_CHANGE, so rehearsed demo lines behave the same
const FIXTURE_URGENT = /\bchest pain\b|흉통|가슴\s*통증|가슴이\s*아파|\bshortness of breath\b|\b(can't|cannot) breathe\b|호흡곤란|숨을\s*못\s*쉬|숨이\s*안\s*쉬어|\bkill myself\b|\bwant to die\b|\bend it all\b|죽고\s*싶|다\s*끝내고\s*싶|\bloss of consciousness\b|\bunresponsive\b|의식 소실|의식이 없/i
const FIXTURE_CHEST_PAIN = /\bchest pain\b|흉통|가슴\s*통증|가슴이\s*아파/i

function fixtureSymptom({ crewId, text }) {
  const urgent = FIXTURE_URGENT.test(text)
  const base = urgent ? eventWarningFixture : eventCautionFixture
  const id = nextFixtureEventId()
  fixtureEvents[id] ={ ...structuredClone(base), id, crew: crewId, symptom_text: text } // the reporter owns it
  if (FIXTURE_CHEST_PAIN.test(text)) procRegister(id, crewId) // the #49 steps are for chest pain only
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
    // Fixture paragraphs are Korean only; runtime docs carry their own optional lang
    return { docs: USE_FIXTURES ? docs.map((d) => ({ lang: 'ko', ...d })) : docs, sample: USE_FIXTURES }
  }),
  // GET /docs/{id} -> {id,title,org,kind,paragraphs:[{n,text}]}; fixture only in fixture mode. Unknown id -> ApiError doc_not_found
  getDoc: (id) => {
    const fromFixture = () => {
      const doc = docsFixture.docs.find((d) => d.id === id)
      if (!doc) throw new ApiError('doc_not_found', 'Document not on device.')
      return { lang: 'ko', ...structuredClone(doc) }
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
  //   + planned (#47 §3, fixture only for now): comms_state, blackout_start_sol, blackout_end_sol,
  //     blackout_days_remaining, next_window_at:{sol,time}, simulation
  getMission: () => request('/mission', () => structuredClone(fixtureMission)),
  recordReceipt: (seq, status, attempt) =>
    request(`/tx/${seq}/receipt`, [], { method: 'POST', body: JSON.stringify({ status, attempt }) }),
  simulateTransmission: (seq, amplitude) =>
    request(`/tx/${seq}/simulate`, null, { method: 'POST', body: JSON.stringify({ wide_amplitude: amplitude }) }),
  setDemoClock: (clock) =>
    request('/demo/clock', () => moveFixtureClock(clock), { method: 'POST', body: JSON.stringify(clock) }),

  // Habitat adjustments (#47 §3, draft until the backend sample): GET /habitat/actions?crew=&lang= ->
  //   [{ id, crew, sol, target: lighting|schedule, tier: auto|approve, status: proposed|applied|undone|released,
  //      reason:{metric,value,z}, before, after, reason_text|null, cite_ids, approved_by, outcome|null }]
  // The backend has no such route yet (404) -> [] so Today simply shows no card.
  getHabitatActions: (crewId, lang = 'en') =>
    request(`/habitat/actions?crew=${crewId}&lang=${lang}`, () => fixtureHabitatList(crewId, lang))
      .catch((e) => {
        if (e.code === 'http_404' || e.code === 'not_found') return []
        throw e
      }),
  // POST /habitat/actions/{id}/approve -> the action, now applied (CONTRACT #59: 403 owner only,
  // 404 action_not_found, 409 action_stale when it is not proposed)
  approveHabitatAction: (id, lang = 'en') =>
    request(`/habitat/actions/${id}/approve?lang=${lang}`,
      () => fixtureHabitatSet(id, ['proposed'], { status: 'applied', approved_by: CURRENT_CREW }, lang), { method: 'POST' }),
  // Procedure with two-person consent (#47 §3, draft until the backend sample): GET /events/{id}/procedure?lang= ->
  //   { event_id, patient, available, required, consenters:[crew], current_step|null,
  //     steps:[{ step_id, kind, text, cite_id, needs_consent, approvals:[{crew, at}], done }] }
  // No such route yet (404) -> null, and the warning screen keeps its first steps.
  getProcedure: (eventId, lang = 'en') =>
    request(`/events/${eventId}/procedure?lang=${lang}`, () => fixtureProcedure(eventId, lang))
      .catch((e) => {
        if (e.code === 'http_404' || e.code === 'not_found') return null
        throw e
      }),
  // GET /earth-reports -> { reports:[{ report_id, event_id, created_at, level, metrics, approvals:[{crew_id, at}],
  //   actions, cite_ids, packet:{ seq, status, held_reason } }] } (CONTRACT #47). The patient and a medical officer
  // with access can read a report. No such route -> [].
  getEarthReports: () =>
    request('/earth-reports', () => ({ reports: fixtureEarthReports(CURRENT_CREW) }))
      .then((r) => (Array.isArray(r?.reports) ? r.reports : []))
      .catch((e) => {
        if (e.code === 'http_404' || e.code === 'not_found') return []
        throw e
      }),
  // POST /events/{id}/procedure/steps/{step_id}/approve -> the procedure. 403 not a consenter, 409 not the current
  // step; the same person again gets the same result
  approveProcedureStep: (eventId, stepId, lang = 'en') =>
    request(`/events/${eventId}/procedure/steps/${stepId}/approve?lang=${lang}`,
      () => fixtureApprove(eventId, stepId, lang), { method: 'POST' }),
  // POST /habitat/actions/{id}/undo -> the action, now undone; the cabin goes back to `before`
  undoHabitatAction: (id, lang = 'en') =>
    request(`/habitat/actions/${id}/undo?lang=${lang}`,
      () => fixtureHabitatSet(id, ['applied'], { status: 'undone' }, lang), { method: 'POST' }),
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
