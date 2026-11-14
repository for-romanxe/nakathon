// DemoClock.jsx — presentation controls for the backend's virtual mission clock (spec: demo time control).
// Each button is one POST /demo/clock; the app-wide mission state is refreshed right after, so the top bar,
// Today and Crew follow. Needs the real backend: in fixture mode the buttons are off.
import { useState } from 'react'
import { api, USE_FIXTURES } from '../api/client.js'
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
      <div className="demo-clock">
        {SCENES.map((s) => (
          <button key={s.key} type="button" className="btn-secondary" onClick={() => go(s)}
            disabled={busy || USE_FIXTURES || (s.needsWindow && mission != null && !hasWindow(mission))}>
            <span>{t(`demo.clock.${s.key}`)}</span>
            <span className="muted small">{t(`demo.clock.${s.key}_hint`)}</span>
          </button>
        ))}
      </div>
      {USE_FIXTURES && <p className="panel-empty muted small">{t('demo.clock.fixtures')}</p>}
      {error && <p role="alert" className="panel-empty error">{t(error)}</p>}
    </section>
  )
}
