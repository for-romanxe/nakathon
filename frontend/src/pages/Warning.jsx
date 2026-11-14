// Warning.jsx — full-screen warning (spec §7 경보 화면, scenarios S9 and S12).
// Raised by rules only (symptom phrases or |z| >= 3); the model is skipped and can never lower it.
// Order: what happened -> first procedure steps -> call the medical officer -> current numbers ->
// urgent transmission to Earth -> acknowledge, or close as a false alarm with a required reason.
import { useEffect, useState } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { api } from '../api/client.js'
import { METRICS, OVERRIDE_REASONS, metricLabel, formatMetric } from '../api/contract.js'
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
  const [event, setEvent] = useState(undefined) // undefined = loading, null = no active warning
  const [steps, setSteps] = useState(null)
  const [packet, setPacket] = useState(null)
  const [cmoCalledAt, setCmoCalledAt] = useState(null)
  const [closing, setClosing] = useState(false)
  const [reason, setReason] = useState('')
  const [sendNote, setSendNote] = useState(null)

  useEffect(() => {
    async function load() {
      // ?event=<id> from Log/Event; otherwise the latest warning event of today
      let id = params.get('event')
      if (!id) {
        const today = await api.getToday(CURRENT_CREW, lang)
        id = [...today.events].reverse().find((e) => e.level === 'warning')?.id
      }
      if (!id) return setEvent(null)
      const [ev, firstSteps, tx] = await Promise.all([
        api.getEvent(id),
        api.getFirstSteps(),
        api.getTx().catch(() => []),
      ])
      setEvent(ev)
      const code = ev.codes.find((c) => firstSteps[c]) ?? 'default'
      setSteps(firstSteps[code])
      setPacket(tx.find((p) => p.event_id === ev.id) ?? null)
    }
    load().catch(() => setEvent(null))
  }, [params, lang])

  if (event === undefined) return <div className="warning-screen"><p className="muted">{t('common.loading')}</p></div>
  if (event === null) {
    return (
      <section className="page">
        <h1>{t('page.warning')}</h1>
        <p className="muted">{t('warning.none')}</p>
        <Link className="btn-secondary align-start" to="/log">{t('nav.log')}</Link>
      </section>
    )
  }

  const flagged = event.findings.filter((f) => f.level === 'caution' || f.level === 'warning')

  async function sendNow() {
    const queue = packet ? await api.sendTx() : await api.queueTx(event.id).then(() => api.sendTx())
    const p = queue.find((x) => x.event_id === event.id) ?? null
    setPacket(p)
    setSendNote(p?.status === 'queued' ? t('warning.tx.no_window', { time: mission?.next_window ?? '–' }) : null)
    refreshMission()
  }

  // Earliest reply: a packet still waiting leaves at the next window; one already out left about now
  const leavesAt = packet && packet.status !== 'queued' && packet.status !== 'missing' ? mission?.clock.time : mission?.next_window

  return (
    <div className="warning-screen" role="alertdialog" aria-labelledby="warning-title" aria-describedby="warning-report">
      <div className="warning-inner">
        <p className="warning-level">{t('warning.level_line')}</p>
        <h1 id="warning-title">{event.codes.length ? event.codes.map((c) => t(`symptom.${c}`)).join(', ') : event.title}</h1>
        <p id="warning-report" className="warning-report">“{event.symptom_text}”</p>
        <p className="muted">{t('warning.by_rules')}</p>

        <section className="warning-block">
          <h2>{t('warning.first_steps')}</h2>
          <ol className="warning-steps">
            {steps?.steps[lang].map((s, i) => <li key={i}>{s}</li>)}
          </ol>
          {steps && <span className="cite">{steps.doc}</span>}
        </section>

        <div className="warning-actions">
          {/* TODO: no crew-call API yet; local state only */}
          <button type="button" className="btn-warning" disabled={!!cmoCalledAt} onClick={() => setCmoCalledAt(mission?.clock.time ?? '')}>
            {cmoCalledAt ? `✔ ${t('warning.cmo_called', { time: cmoCalledAt })}` : t('warning.call_cmo')}
          </button>
        </div>

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
          {mission && (
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
          <button type="button" className="btn-primary" onClick={() => navigate(`/events/${event.id}`)}>
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
                if (reason) navigate(`/events/${event.id}`)
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
