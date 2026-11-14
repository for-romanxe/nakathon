// Today.jsx — Today screen (spec §7-1): greeting -> status sentence -> today's guide -> evidence (6 metrics) -> check-in streak.
import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../api/client.js'
import CheckinSheet from '../components/CheckinSheet.jsx'
import { METRICS, SENSITIVITY, metricLabel, formatMetric } from '../api/contract.js'
import { CURRENT_CREW } from '../session.js'
import { useT } from '../i18n/index.jsx'

// Status is never shown by color alone: icon + word + color
const LEVEL_ICONS = { normal: '✔', advisory: '•', caution: '▲', warning: '✖', hold: '↻' }

function greetingKey(time) {
  const hour = Number(time.split(':')[0])
  if (hour < 11) return 'today.greeting.morning'
  if (hour < 18) return 'today.greeting.day'
  return 'today.greeting.evening'
}

function formatZ(z) {
  if (z == null) return null
  const r = Math.round(z * 10) / 10
  return `${r > 0 ? '+' : r < 0 ? '−' : '±'}${Math.abs(r).toFixed(1)}σ`
}

export default function Today() {
  const { t, lang } = useT()
  const [data, setData] = useState(null)
  const [error, setError] = useState(null)
  const [sheetClosed, setSheetClosed] = useState(false)
  const navigate = useNavigate()

  useEffect(() => {
    // /crew and /mission are not on the backend yet, so their failure must not break Today
    Promise.all([
      api.getToday(CURRENT_CREW, lang),
      api.getCrew().catch(() => []),
      api.getMission().catch(() => null),
    ])
      .then(([today, crew, mission]) => setData({ today, crew: crew.find((c) => c.id === CURRENT_CREW), mission }))
      .catch(setError)
  }, [lang])

  if (error) return <section className="page"><p className="error">{t('common.error')}</p></section>
  if (!data) return <section className="page"><p className="muted">{t('common.loading')}</p></section>

  const { today, crew, mission } = data
  const level = today.status.level
  // The backend writes status.text in English; Korean uses the dictionary until /today supports ?lang
  const statusText = lang === 'en' && today.status.text ? today.status.text : t(`today.status.${level}`)
  const [advisoryLimit] = SENSITIVITY.standard
  const showSheet = !today.checkin.morning_done && !sheetClosed

  async function submitCheckin(body) {
    const updated = await api.postCheckin(CURRENT_CREW, body) // backend recomputes the guide and returns /today
    setData((d) => ({ ...d, today: updated }))
  }

  return (
    <section className="page">
      {showSheet && (
        <CheckinSheet
          onSubmit={submitCheckin}
          onSymptoms={() => navigate('/log')}
          onClose={() => setSheetClosed(true)}
        />
      )}
      {!today.checkin.morning_done && sheetClosed && (
        <button type="button" className="btn-secondary align-start" onClick={() => setSheetClosed(false)}>
          {t('checkin.open')}
        </button>
      )}
      <h1>
        {crew
          ? t(mission ? greetingKey(mission.clock.time) : 'today.greeting.day', { name: crew.name })
          : t('today.greeting.generic')}
      </h1>
      <p className={`status lv-${level}`}>
        <span aria-hidden="true">{LEVEL_ICONS[level]}</span>
        {statusText}
      </p>

      <section className="panel">
        <div className="panel-head"><h2>{t('today.guide')}</h2></div>
        {today.guide.length === 0 && <p className="panel-empty muted">{t('today.guide_empty')}</p>}
        <ul className="guide">
          {today.guide.map((g) => (
            <li key={g.key} className={g.done ? 'done' : ''}>
              <div>
                <span className="guide-target">{g.target}</span>
                {g.adjustment && <> → <span className="guide-adjust">{g.adjustment}</span></>}
              </div>
              <span className="guide-state">{g.done ? `✔ ${t('today.done')}` : ''}</span>
              {g.why && (
                <div className="guide-why">
                  <span>{t('today.why')}: <span className="num">{g.why}</span></span>
                  {g.cites.map((c) => <span key={c} className="cite">{c}</span>)}
                </div>
              )}
            </li>
          ))}
        </ul>
      </section>

      <section className="panel">
        <div className="panel-head">
          <h2>{t('today.evidence')}</h2>
          <span className="muted">{t('today.streak', { n: today.streak })}</span>
        </div>
        <div className="readouts">
          {today.metrics.map((m) => {
            // Which metric drove the verdict: the backend's per-metric level when it sends one (requested),
            // otherwise |z| at or above the contract's advisory limit. The overall verdict stays the backend's.
            const flagged = m.level ? m.level !== 'normal' : m.z != null && Math.abs(m.z) >= advisoryLimit
            const tint = flagged && (level === 'caution' || level === 'warning') ? level : null // advisory stays uncoloured
            const z = formatZ(m.z)
            return (
              <div key={m.metric} className={`readout${tint ? ` lv-${tint} off` : ''}`}>
                <span>{metricLabel(m.metric, lang)}</span>
                <span className="readout-value">{formatMetric(m.metric, m.value)}</span>
                <span className="readout-unit">{METRICS[m.metric]?.unit}</span>
                <span className={`badge ${tint ? `lv-${tint}` : flagged ? 'neutral' : z ? 'lv-normal' : 'lv-hold'}`}>
                  {z ?? `${LEVEL_ICONS.hold} ${t('level.hold')}`}
                </span>
              </div>
            )
          })}
        </div>
      </section>
    </section>
  )
}
