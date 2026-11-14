// DemoClock.jsx — presentation controls for the backend's virtual mission clock (spec: demo time control).
// Each button is one POST /demo/clock; the app-wide mission state is refreshed right after, so the top bar,
// Today and Crew follow. Needs the real backend: in fixture mode the buttons are off.
import { useState } from 'react'
import { api, USE_FIXTURES } from '../api/client.js'
import { useMission } from '../mission.jsx'
import { useT } from '../i18n/index.jsx'

// Scenes from the demo script. Each returns the body for POST /demo/clock, given the current mission state.
const SCENES = [
  { key: 'morning', body: ({ clock }) => ({ sol: clock.sol, time: '06:10' }) }, // S1 wake-up, band synced
  { key: 'recheck', body: ({ clock }) => ({ sol: clock.sol, time: '14:00' }) }, // S4 afternoon re-check
  { // S7 / S14: next comm window (tomorrow's first one if today's have passed)
    key: 'window',
    body: ({ clock, next_window }) => ({ sol: clock.sol + (next_window <= clock.time ? 1 : 0), time: next_window }),
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
      await api.setDemoClock(scene.body(now))
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
          {mission ? t('demo.clock.now', { sol: mission.clock.sol, time: mission.clock.time }) : '–'}
        </span>
      </div>
      <div className="demo-clock">
        {SCENES.map((s) => (
          <button key={s.key} type="button" className="btn-secondary" disabled={busy || USE_FIXTURES} onClick={() => go(s)}>
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
