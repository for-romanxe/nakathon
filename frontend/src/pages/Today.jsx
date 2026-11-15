// Today.jsx — Today screen (spec §7-1): greeting -> status sentence -> today's guide -> evidence (6 metrics) -> check-in streak.
import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { api } from '../api/client.js'
import CheckinSheet from '../components/CheckinSheet.jsx'
import GuideWhy from '../components/GuideWhy.jsx'
import { useMission } from '../mission.jsx'
import { isWarningAcked, warningKey } from '../warningAck.js'
import { METRICS, metricLabel, formatMetric } from '../api/contract.js'
import { CURRENT_CREW } from '../session.js'
import Cite from '../components/Cite.jsx'
import DeviationScale from '../components/DeviationScale.jsx'
import HabitatCard from '../components/HabitatCard.jsx'
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

// Remembers "closed the check-in sheet" per crew, sol and kind, so it stays closed when you come back to Today
let sheetDismissedFor = null
const EVENING_FROM = 18 // the evening check-out is offered from 18:00 mission time, once the morning one is done

// Which check-in is due now: morning until it is done, then the evening check-out in the evening, else none
function dueCheckin(checkin, time) {
  if (!checkin?.morning_done) return 'morning'
  const hour = Number(String(time ?? '').split(':')[0])
  if (!checkin.evening_done && hour >= EVENING_FROM) return 'evening'
  return null
}

export default function Today() {
  const { t, lang } = useT()
  const [data, setData] = useState(null)
  const [error, setError] = useState(null)
  const navigate = useNavigate()
  const { mission } = useMission()
  const sol = mission?.clock.sol
  const [, setSheetClosed] = useState(false) // re-render trigger; the source of truth is sheetDismissedFor
  const due = dueCheckin(data?.checkin, mission?.clock.time)
  const sheetKey = `${CURRENT_CREW}:${sol}:${due}`
  const sheetClosed = sheetDismissedFor === sheetKey

  useEffect(() => {
    api.getToday(CURRENT_CREW, lang)
      .then(setData)
      .catch(setError)
  }, [lang, sol])

  // CONTRACT §5.4: a metric at warning opens the full-screen warning even without a symptom report
  useEffect(() => {
    if (sol == null || !data) return
    const hit = data.metrics.some((m) => m.level === 'warning')
    if (hit && !isWarningAcked(warningKey(CURRENT_CREW, sol))) navigate('/warning')
  }, [data, sol, navigate])

  function closeSheet(closed) {
    sheetDismissedFor = closed ? sheetKey : null
    setSheetClosed(closed)
  }

  if (error) return <section className="page"><p className="error">{t('common.error')}</p></section>
  if (!data) return <section className="page"><p className="muted">{t('common.loading')}</p></section>

  const today = data
  const level = today.status.level
  const statusText = today.status.text || t(`today.status.${level}`) // backend localises via ?lang
  const showSheet = due != null && !sheetClosed

  async function submitCheckin(body) {
    const updated = await api.postCheckin(CURRENT_CREW, body, lang) // backend recomputes the guide and returns /today
    setData(updated)
  }

  return (
    <section className="page">
      {showSheet && (
        <CheckinSheet
          key={sheetKey}
          kind={due}
          prefill={today.checkin?.morning_prefill}
          onSubmit={submitCheckin}
          onSymptoms={() => navigate('/log')}
          onClose={() => closeSheet(true)}
        />
      )}
      {due != null && sheetClosed && (
        <button type="button" className="btn-secondary align-start" onClick={() => closeSheet(false)}>
          {t(due === 'evening' ? 'checkin.evening.open' : 'checkin.open')}
        </button>
      )}
      <h1>
        {t(mission ? greetingKey(mission.clock.time) : 'today.greeting.day', { name: CURRENT_CREW.toUpperCase() })}
      </h1>
      {/* Annunciator: a lit lamp with the level word, then the sentence */}
      <div className={`annunciator lv-${level}`}>
        <span className="annunciator-lamp">
          <span aria-hidden="true">{LEVEL_ICONS[level]}</span> {t(`level.${level}`)}
        </span>
        <p className="annunciator-text">{statusText}</p>
      </div>
      {today.baseline_progress && today.baseline_progress.collected_days < today.baseline_progress.target_days &&
        <p className="muted">{t('today.baseline_progress', today.baseline_progress)}</p>}
      {/* Another crew member's procedure step is waiting for my consent (#47 FE-03, draft field) */}
      {(today.consent_requests ?? []).map((r) => (
        <Link key={`${r.event_id}:${r.step_id}`} className="consent-request lv-warning" to={`/events/${r.event_id}/procedure`}>
          <b>{t('today.consent_request', { patient: r.patient?.toUpperCase() ?? '–' })}</b>
          <span className="num">{t('proc.consent.count', { n: r.approvals ?? 0, of: r.required ?? 2 })} · {t('today.consent_open')}</span>
        </Link>
      ))}

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
                  {g.cites.map((c) => <Cite key={c} id={c} />)}
                </div>
              )}
              {!g.done && <GuideWhy cites={g.cites} />}
            </li>
          ))}
        </ul>
      </section>

      <HabitatCard crewId={CURRENT_CREW} sol={sol} lang={lang} />

      <section className="panel">
        <div className="panel-head">
          <h2>{t('today.evidence')}</h2>
          <span className="muted">{t('today.streak', { n: today.streak })}</span>
        </div>
        <div className="readouts">
          {today.metrics.map((m) => {
            // Each metric shows its own backend level (CONTRACT §5.3); the UI never recomputes it from z.
            // caution/warning are coloured, advisory stays uncoloured, hold shows its reason.
            const lv = m.level ?? 'normal'
            const tint = lv === 'caution' || lv === 'warning' ? lv : null
            const badgeClass = tint ? `lv-${tint}` : lv === 'advisory' ? 'neutral' : `lv-${lv}`
            return (
              <div key={m.metric} className={`readout${tint ? ` lv-${tint} off` : ''}`}>
                <span className="readout-name">
                  {metricLabel(m.metric, lang)}
                  {lv === 'hold' && m.hold_reason && <span className="readout-note">{t(`hold.${m.hold_reason}`)}</span>}
                </span>
                <DeviationScale z={lv === 'hold' ? null : m.z} level={lv} />
                <span className="readout-value">{formatMetric(m.metric, m.value)}</span>
                <span className="readout-unit">{METRICS[m.metric]?.unit}</span>
                <span className={`badge ${badgeClass}`}>
                  {lv === 'hold' ? `${LEVEL_ICONS.hold} ${t('level.hold')}` : `${LEVEL_ICONS[lv]} ${formatZ(m.z) ?? ''}`}
                </span>
              </div>
            )
          })}
        </div>
      </section>
    </section>
  )
}
