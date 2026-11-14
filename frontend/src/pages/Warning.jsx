// Warning.jsx — full-screen warning (spec §7 경보 화면, scenarios S9 and S12).
// Raised by rules only (symptom phrases or |z| >= 3); the model is skipped and can never lower it.
// CONTRACT §5.4: a warning is any event or metric with level "warning"; event.urgent only says whether
// the report text caused it. A metric at warning opens this screen even with no symptom report.
// Order: what happened -> first procedure steps -> call the medical officer -> current numbers ->
// urgent transmission to Earth -> acknowledge, or close as a false alarm with a required reason.
import { useEffect, useState } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { api } from '../api/client.js'
import { METRICS, OVERRIDE_REASONS, metricLabel, formatMetric, isUrgentReport } from '../api/contract.js'
import { ackWarning, warningKey } from '../warningAck.js'
import { CURRENT_CREW } from '../session.js'
import { useMission } from '../mission.jsx'
import { useT } from '../i18n/index.jsx'

function addMinutes(hhmm, minutes) {
  const [h, m] = hhmm.split(':').map(Number)
  const total = (h * 60 + m + minutes) % (24 * 60)
  return `${String(Math.floor(total / 60)).padStart(2, '0')}:${String(total % 60).padStart(2, '0')}`
}

export default function Warning() {
  const { t, lang } = useT()
  const navigate = useNavigate()
  const [params] = useSearchParams()
  const { mission, refresh: refreshMission } = useMission()
  // undefined = loading, null = no active warning,
  // otherwise { event (or null for a metrics-only warning), findings, urgent, codes }
  const [warning, setWarning] = useState(undefined)
  const [steps, setSteps] = useState(null)
  const [packet, setPacket] = useState(null)
  const [cmoCalledAt, setCmoCalledAt] = useState(null)
  const [closing, setClosing] = useState(false)
  const [reason, setReason] = useState('')
  const [sendNote, setSendNote] = useState(null)
  const [loadError, setLoadError] = useState(false)
  const [attempt, setAttempt] = useState(0) // bump to retry the load

  useEffect(() => {
    async function load() {
      // ?event=<id> from Log/Event; otherwise today's latest warning event; otherwise a metric at warning
      const [firstSteps, tx] = await Promise.all([api.getFirstSteps(), api.getTx().catch(() => [])])
      const showEvent = (ev) => {
        const codes = ev.codes ?? [] // missing fields must not break the warning screen
        setWarning({ event: ev, findings: ev.findings ?? [], urgent: isUrgentReport(ev), codes })
        setSteps(firstSteps[codes.find((c) => firstSteps[c]) ?? 'default'])
        setPacket(tx.find((p) => p.event_id === ev.id) ?? null)
      }
      const asked = params.get('event')
      if (asked) {
        const ev = await api.getEvent(asked).catch(() => null) // gone or unreadable: fall back to today below
        if (ev?.level === 'warning') return showEvent(ev)
      }
      const today = await api.getToday(CURRENT_CREW, lang)
      const id = [...(today.events ?? [])].reverse().find((e) => e.level === 'warning')?.id
      if (id) return showEvent(await api.getEvent(id))
      if ((today.metrics ?? []).some((m) => m.level === 'warning')) {
        setWarning({ event: null, findings: today.metrics, urgent: false, codes: [] })
        setSteps(firstSteps.default)
        setPacket(tx.find((p) => p.kind === 'daily' && p.crew === CURRENT_CREW) ?? null)
        return
      }
      setWarning(null)
    }
    load().catch(() => setLoadError(true)) // unknown is not the same as "no warning"
  }, [params, lang, attempt])

  if (loadError) {
    return (
      <div className="warning-screen warning-unknown" role="alert">
        <div className="warning-inner">
          <h1>{t('warning.unknown_title')}</h1>
          <p>{t('warning.unknown_body')}</p>
          <button type="button" className="btn-primary align-start" onClick={() => { setLoadError(false); setWarning(undefined); setAttempt((n) => n + 1) }}>
            {t('warning.retry')}
          </button>
        </div>
      </div>
    )
  }

  if (warning === undefined) return <div className="warning-screen"><p className="muted">{t('common.loading')}</p></div>
  if (warning === null) {
    return (
      <section className="page">
        <h1>{t('page.warning')}</h1>
        <p className="muted">{t('warning.none')}</p>
        <Link className="btn-secondary align-start" to="/log">{t('nav.log')}</Link>
      </section>
    )
  }

  const { event, findings, urgent, codes } = warning
  const flagged = findings.filter((f) => f.level === 'caution' || f.level === 'warning')
  const done = () => {
    ackWarning(warningKey(CURRENT_CREW, mission?.clock.sol))
    navigate(event ? `/events/${event.id}` : '/today')
  }

  async function sendNow() {
    try {
      // an event warning sends its event summary; a metrics-only warning goes with today's summary
      const queue = packet ? await api.sendTx() : await (event ? api.queueTx(event.id) : api.queueDaily()).then(() => api.sendTx())
      const p = queue.find((x) => (event ? x.event_id === event.id : x.kind === 'daily' && x.crew === CURRENT_CREW)) ?? null
      setPacket(p)
      setSendNote(p?.status === 'queued' ? t('warning.tx.no_window', { time: mission?.next_window ?? '–' }) : null)
      refreshMission()
    } catch {
      setSendNote(t('warning.tx.failed')) // the send button stays, so it can be retried
    }
  }

  // Earliest reply: a packet still waiting leaves at the next window; one already out left about now
  const leavesAt = packet && packet.status !== 'queued' && packet.status !== 'missing' ? mission?.clock?.time : mission?.next_window
  const hasTime = typeof leavesAt === 'string' && /^\d{2}:\d{2}$/.test(leavesAt)
  // 3) step list for the current language, falling back to English, never undefined
  const stepList = steps?.steps?.[lang] ?? steps?.steps?.en ?? []

  return (
    <div className="warning-screen" role="alertdialog" aria-labelledby="warning-title" aria-describedby="warning-report">
      <div className="warning-inner">
        <p className="warning-level">{t('warning.level_line')}</p>
        <h1 id="warning-title">
          {urgent && codes.length ? codes.map((c) => t(`symptom.${c}`)).join(', ') : urgent ? event.title : t('warning.measured_title')}
        </h1>
        {event && <p id="warning-report" className="warning-report">“{event.symptom_text}”</p>}
        <p className="muted">{t(urgent ? 'warning.by_rules' : 'warning.by_readings')}</p>

        <section className="warning-block">
          <h2>{t('warning.first_steps')}</h2>
          <ol className="warning-steps">
            {stepList.map((s, i) => <li key={i}>{s}</li>)}
          </ol>
          {steps && <span className="cite">{steps.doc}</span>}
        </section>

        {/* The app cannot call anyone yet (no crew-call API), so it must not say it did */}
        <section className="warning-block warning-contact">
          <h2>{t('warning.contact_title')}</h2>
          <p>{t('warning.contact_body')}</p>
          <button type="button" className="btn-warning align-start" disabled={!!cmoCalledAt} onClick={() => setCmoCalledAt(mission?.clock.time ?? '')}>
            {cmoCalledAt ? `✔ ${t('warning.contact_noted', { time: cmoCalledAt })}` : t('warning.contact_done')}
          </button>
        </section>

        <section className="warning-block">
          <h2>{t('warning.numbers')}</h2>
          {flagged.length === 0 && <p className="muted">{t('warning.numbers_normal')}</p>}
          <ul className="warning-numbers">
            {flagged.map((f) => (
              <li key={f.metric} className={`lv-${f.level}`}>
                <span>{metricLabel(f.metric, lang)}</span>
                <b className="num">{formatMetric(f.metric, f.value)} <span className="muted">{METRICS[f.metric]?.unit}</span></b>
                <span className="muted num">{t('warning.baseline', { v: formatMetric(f.metric, f.baseline) })}</span>
              </li>
            ))}
          </ul>
        </section>

        <section className="warning-block">
          <h2>{t('warning.tx')}</h2>
          <p>
            {packet
              ? t(`warning.tx.${packet.status}`, { time: mission?.next_window ?? '–' })
              : t('warning.tx.none')}
          </p>
          {mission && hasTime && (
            <p className="muted num">
              {t('warning.tx.delay', {
                n: mission.one_way_delay_min,
                reply: addMinutes(leavesAt, mission.one_way_delay_min * 2),
              })}
            </p>
          )}
          {(!packet || packet.status === 'queued' || packet.status === 'missing') && (
            <button type="button" className="btn-secondary align-start" onClick={sendNow}>{t('warning.tx.send')}</button>
          )}
          {sendNote && <p className="muted">{sendNote}</p>}
        </section>

        <div className="warning-footer">
          <button type="button" className="btn-primary" onClick={done}>
            {t('warning.ack')}
          </button>
          {!closing && (
            <button type="button" className="btn-ghost" onClick={() => setClosing(true)}>{t('event.override')}</button>
          )}
          {closing && (
            <form
              className="override"
              onSubmit={(e) => {
                e.preventDefault()
                // TODO: POST /events/{id}/override {reason} when the backend has it
                if (reason) done()
              }}
            >
              <label htmlFor="warning-close-reason">{t('event.override_reason')}</label>
              <select id="warning-close-reason" value={reason} onChange={(e) => setReason(e.target.value)} required>
                <option value="">{t('event.override_pick')}</option>
                {OVERRIDE_REASONS.map((r) => <option key={r} value={r}>{t(`override.${r}`)}</option>)}
              </select>
              <button type="submit" className="btn-secondary" disabled={!reason}>{t('event.override_confirm')}</button>
            </form>
          )}
        </div>
      </div>
    </div>
  )
}
