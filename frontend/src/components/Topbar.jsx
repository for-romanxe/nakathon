// Topbar.jsx — mission status strip: sol and time, environment, one-way delay to Earth, next comm window,
// and the autonomy dial (Earth connected / delayed / blackout) when GET /mission sends comms_state (#46, #47 §3).
// The dial only shows the server's state; it never works the state out from the clock itself.
import { useMission } from '../mission.jsx'
import { USE_FIXTURES } from '../api/client.js'
import { useT } from '../i18n/index.jsx'

const COMMS_STATES = ['connected', 'delayed', 'blackout']

function AutonomyDial({ state, daysLeft }) {
  const { t } = useT()
  return (
    <div className={`comms-dial comms-${state}`}>
      <span className="sr-only">{t('comms.label')}: {t(`comms.${state}`)}</span>
      <ol className="comms-steps" aria-hidden="true">
        {COMMS_STATES.map((s) => (
          <li key={s} className={s === state ? 'on' : ''}>{t(`comms.${s}`)}</li>
        ))}
      </ol>
      <span className="comms-note">
        {state === 'blackout' && daysLeft != null ? t('comms.blackout_left', { n: daysLeft }) : t(`comms.${state}_hint`)}
      </span>
    </div>
  )
}

export default function Topbar() {
  const { t } = useT()
  const { mission: m } = useMission()

  if (!m) return <header className="topbar" />
  const state = COMMS_STATES.includes(m.comms_state) ? m.comms_state : null
  // next_window_at counts the blackout (no send until Sol 57); the older next_window is only a time of day
  const at = m.next_window_at
  const windowValue = at?.sol != null && at?.time ? t('topbar.window_at', { sol: at.sol, time: at.time }) : m.next_window
  const items = [
    ['topbar.sol', `${m.clock.sol} · ${m.clock.time}`],
    ['topbar.env', t(`env.${m.environment}`)],
    ['topbar.delay', t('topbar.minutes', { n: m.one_way_delay_min })],
    ['topbar.window', windowValue],
  ]
  return (
    <header className="topbar">
      <div className="topbar-items">
        {items.map(([label, value]) => (
          <div key={label} className="topbar-item">
            <span className="topbar-label">{t(label)}</span>
            <span className="topbar-value">{value}</span>
          </div>
        ))}
      </div>
      {/* Fixture mode (team decision 6 in #47): always say the screen is example data, never pass it off as live */}
      {USE_FIXTURES && <span className="fixture-badge" role="note">{t('fixture.badge')}</span>}
      {state && <AutonomyDial state={state} daysLeft={m.blackout_days_remaining} />}
    </header>
  )
}
