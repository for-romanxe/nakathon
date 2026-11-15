// DemoClock.jsx — presentation controls for the backend's virtual mission clock (spec: demo time control).
// Each button is one POST /demo/clock; the app-wide mission state is refreshed right after, so the top bar,
// Today and Crew follow. In fixture mode the same buttons move an in-memory clock (api/client.js), so the evening
// check-out and other timed scenes can be shown without the backend.
import { useState } from 'react'
import { api } from '../api/client.js'
import { useMission } from '../mission.jsx'
import { useT } from '../i18n/index.jsx'

const HHMM = /^(?:[01]\d|2[0-3]):[0-5]\d$/

// GET /mission -> { clock: { sol, time }, next_window, ... } (CONTRACT §5). Anything else is not used.
function validMission(m) {
  return Number.isInteger(m?.clock?.sol) && HHMM.test(m?.clock?.time ?? '')
}
const hasWindow = (m) => HHMM.test(m?.next_window ?? '')

// Scenes from the demo script. Each returns the body for POST /demo/clock, given a valid mission state,
// or null when the scene cannot be built from it (no comm window in the response).
const SCENES = [
  { key: 'morning', body: ({ clock }) => ({ sol: clock.sol, time: '06:10' }) }, // S1 wake-up, band synced
  { key: 'recheck', body: ({ clock }) => ({ sol: clock.sol, time: '14:00' }) }, // S4 afternoon re-check
  { key: 'evening', body: ({ clock }) => ({ sol: clock.sol, time: '19:00' }) }, // evening check-out on Today
  { // S7 / S14: next comm window (tomorrow's first one if today's have passed)
    key: 'window',
    needsWindow: true,
    body: (m) => (hasWindow(m) ? { sol: m.clock.sol + (m.next_window <= m.clock.time ? 1 : 0), time: m.next_window } : null),
  },
  { key: 'hour', body: () => ({ advance: '1h' }) },
  { key: 'next_sol', body: ({ clock }) => ({ sol: clock.sol + 1, time: '06:10' }) }, // a second day in a row
]

// Presentation scenes from issue #47 (FE-06): one press puts the clock on that act, so no one sets a date by hand
// on stage. Fixed sol and time; the backend decides what each sol looks like (comms state, data).
const ACTS = [
  { key: 'act1', sol: 16, time: '06:10' }, // C1 slept badly: the habitat adjusts
  { key: 'act1_result', sol: 17, time: '06:10' }, // next morning: before / after
  { key: 'act2', sol: 40, time: '09:00' }, // D-3 before the solar conjunction
  { key: 'act3', sol: 46, time: '09:00' }, // blackout, 11 days to go: C4 chest pain
  { key: 'act4', sol: 57, time: '08:00' }, // first window after the blackout opens
].map((a) => ({ ...a, body: () => ({ sol: a.sol, time: a.time }) }))

export default function DemoClock() {
  const { t } = useT()
  const { mission, refresh } = useMission()
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState(null)

  async function go(scene) {
    setBusy(true)
    setError(null)
    try {
      const now = await api.getMission() // the shared state can be up to 15 s old
      if (!validMission(now)) { setError('demo.clock.bad_mission'); return }
      const body = scene.body(now)
      if (!body) { setError('demo.clock.no_window'); return }
      await api.setDemoClock(body)
      refresh()
    } catch (e) {
      // with sign-in on, only the medical officer may move the clock (403)
      setError(e?.code === 'forbidden' || e?.code === 'http_403' ? 'demo.clock.forbidden' : 'common.error')
    } finally {
      setBusy(false)
    }
  }

  return (
    <section className="panel">
      <div className="panel-head">
        <h2>{t('demo.clock.title')}</h2>
        <span className="muted num small">
          {validMission(mission) ? t('demo.clock.now', { sol: mission.clock.sol, time: mission.clock.time }) : '–'}
        </span>
      </div>
      <h3 className="demo-clock-group">{t('demo.clock.acts')}</h3>
      <div className="demo-clock">
        {ACTS.map((a) => {
          const here = mission?.clock?.sol === a.sol && mission?.clock?.time === a.time
          return (
            <button key={a.key} type="button" className="btn-secondary" onClick={() => go(a)} disabled={busy}
              aria-current={here ? 'step' : undefined}>
              <span>{t(`demo.clock.${a.key}`)}</span>
              <span className="muted small num">{t('demo.clock.at', { sol: a.sol, time: a.time })}</span>
            </button>
          )
        })}
      </div>
      <h3 className="demo-clock-group">{t('demo.clock.steps')}</h3>
      <div className="demo-clock">
        {SCENES.map((s) => (
          <button key={s.key} type="button" className="btn-secondary" onClick={() => go(s)}
            disabled={busy || (s.needsWindow && mission != null && !hasWindow(mission))}>
            <span>{t(`demo.clock.${s.key}`)}</span>
            <span className="muted small">{t(`demo.clock.${s.key}_hint`)}</span>
          </button>
        ))}
      </div>
      {error && <p role="alert" className="panel-empty error">{t(error)}</p>}
    </section>
  )
}
