// EarthReports.jsx — crew reports saved for Earth after two-person consent (#46 Act 3, #47 FE-04).
// Shows what was saved, who consented, and where its warning packet is: held by the blackout, waiting for the next
// window, sent, or acknowledged. Re-reads every few seconds, so a report saved from another crew member's session
// appears without a reload. With `eventId` it shows that event's report only; with no reports it shows nothing.
import { useEffect, useState } from 'react'
import { api } from '../api/client.js'
import { formatTs, metricLabel, formatMetric, METRICS } from '../api/contract.js'
import { useMission } from '../mission.jsx'
import { nextWindowLabel } from '../nextWindow.js'
import { useT } from '../i18n/index.jsx'

const POLL_MS = 5000
const HELD_REASONS = ['blackout'] // CONTRACT #47: held_reason values with their own wording
const PACKET_CLASS ={ held: 'lv-warning', queued: 'lv-caution', sent: 'neutral', missing: 'lv-caution', acked: 'lv-normal' }

function Report({ r }) {
  const { t, lang } = useT()
  const { mission } = useMission()
  const status = r.packet?.status
  const who = (r.approvals ?? []).map((a) => String(a?.crew_id ?? '').toUpperCase()).filter(Boolean)
  return (
    <li className="earth-report">
      <div className="earth-report-top">
        <b>{t('earth.report', { id: r.report_id, event: r.event_id })}</b>
        {r.created_at && <span className="muted small num">{formatTs(r.created_at)}</span>}
      </div>
      <p className="small">{who.length ? t('earth.consented', { who: who.join(' · ') }) : t('earth.no_consent')}</p>
      {r.metrics?.some((m) => m?.metric) ? (
        <ul className="earth-metrics num small">
          {r.metrics.filter((m) => m?.metric).map((m) => (
            <li key={m.metric}>{metricLabel(m.metric, lang)} {formatMetric(m.metric, m.value)} {METRICS[m.metric]?.unit ?? ''}</li>
          ))}
        </ul>
      ) : <p className="muted small">{t('earth.no_metrics')}</p>}
      {status && (
        <p className="earth-packet">
          <span className={`badge ${PACKET_CLASS[status] ?? 'neutral'}`}>{t(`earth.packet.${status}`, { seq: r.packet.seq })}</span>{' '}
          <span className="small">
            {status === 'queued' && t('earth.packet.queued_when', { window: nextWindowLabel(mission) })}
            {/* a reason is shown only when the backend gives one this screen knows; it is never guessed */}
            {status === 'held' && (HELD_REASONS.includes(r.packet.held_reason)
              ? t('earth.packet.held_when', { reason: t(`earth.held.${r.packet.held_reason}`), window: nextWindowLabel(mission) })
              : t('earth.packet.held_plain', { window: nextWindowLabel(mission) }))}
          </span>
        </p>
      )}
    </li>
  )
}

export default function EarthReports({ eventId = null, className = '' }) {
  const { t } = useT()
  const [reports, setReports] = useState([])

  useEffect(() => {
    let alive = true
    const load = () => api.getEarthReports().then((list) => alive && setReports(list)).catch(() => {}) // keep the last good list
    load()
    const id = setInterval(load, POLL_MS) // the consent that saves a report happens in another session
    return () => { alive = false; clearInterval(id) }
  }, [])

  const shown = eventId == null ? reports : reports.filter((r) => String(r.event_id) === String(eventId))
  if (!shown.length) return null
  return (
    <section className={`earth-reports ${className}`}>
      <h2>{t('earth.title')}</h2>
      <ul className="earth-list">
        {shown.map((r) => <Report key={r.report_id} r={r} />)}
      </ul>
      <p className="muted small">{t('earth.note')}</p>
    </section>
  )
}
