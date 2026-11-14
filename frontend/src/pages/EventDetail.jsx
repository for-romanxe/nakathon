// EventDetail.jsx — one symptom event (spec §7 event detail, scenarios S2/S3):
// report -> facts (rule table) -> risk guidance in three lines -> verification (5 checks, runs) -> response.
// Facts and the rule verdict always sit above any model sentence (PRODUCT principle 1).
import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { api } from '../api/client.js'
import { METRICS, VERIFY_CHECKS, OVERRIDE_REASONS, metricLabel, formatMetric, conditionLabel, isUrgentReport } from '../api/contract.js'
import { useT } from '../i18n/index.jsx'

const ICONS = { normal: '✔', advisory: '•', caution: '▲', warning: '✖', hold: '↻' }

function formatZ(z) {
  if (z == null) return '–'
  const r = Math.round(z * 10) / 10
  return `${r > 0 ? '+' : r < 0 ? '−' : '±'}${Math.abs(r).toFixed(1)}σ`
}

export default function EventDetail() {
  const { id } = useParams()
  const { t } = useT()
  const [event, setEvent] = useState(null)
  const [error, setError] = useState(false)

  useEffect(() => {
    api.getEvent(id).then(setEvent).catch(() => setError(true))
  }, [id])

  if (error) return <section className="page"><p className="error">{t('event.not_found')}</p></section>
  if (!event) return <section className="page"><p className="muted">{t('common.loading')}</p></section>

  return (
    <section className="page event">
      <Link to="/log" className="back-link">← {t('nav.log')}</Link>
      <div className="event-head">
        <span className={`badge lv-${event.level}`}>{ICONS[event.level]} {t(`level.${event.level}`)}</span>
        <h1>{event.title}</h1>
        <span className="num muted">{event.ts.slice(0, 16).replace('T', ' ')}</span>
      </div>
      <blockquote className="report">“{event.symptom_text}”</blockquote>

      <Facts event={event} />
      <Guidance event={event} />
      <Verification event={event} />
      <Response event={event} />
    </section>
  )
}

// Rule facts: symptom codes + every metric with baseline and z at the time of the report
function Facts({ event }) {
  const { t, lang } = useT()
  return (
    <section className="panel">
      <div className="panel-head">
        <h2>{t('event.facts')}</h2>
        <span className="muted small">{t('event.facts_by')}</span>
      </div>
      {event.codes.length > 0 && (
        <div className="codes">
          {event.codes.map((c) => <span key={c} className="code-chip">{t(`symptom.${c}`)}</span>)}
        </div>
      )}
      <table className="facts-table">
        <thead>
          <tr>
            <th>{t('event.col.metric')}</th>
            <th className="right">{t('event.col.value')}</th>
            <th className="right">{t('event.col.baseline')}</th>
            <th className="right">z</th>
            <th>{t('event.col.level')}</th>
          </tr>
        </thead>
        <tbody>
          {event.findings.map((f) => (
            <tr key={f.metric} className={f.level === 'caution' || f.level === 'warning' ? `lv-${f.level} off` : ''}>
              <td>{metricLabel(f.metric, lang)}</td>
              <td className="num right">{formatMetric(f.metric, f.value)} <span className="muted">{METRICS[f.metric]?.unit}</span></td>
              <td className="num right">{formatMetric(f.metric, f.baseline)}</td>
              <td className="num right">{formatZ(f.z)}</td>
              <td><span className={`badge ${f.level === 'advisory' ? 'neutral' : `lv-${f.level}`}`}>{t(`level.${f.level}`)}</span></td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  )
}

// Risk guidance in three lines: HRP category · possible condition (fixed list, always "possibility") · today's actions
function Guidance({ event }) {
  const { t, lang } = useT()
  const runs = event.runs ?? []
  const passed = runs.some((r) => r.ok)
  const withheld = runs.length >= 2 && !passed // verification failed twice -> judgement withheld
  const ex = event.explanation

  let body
  if (event.level === 'warning' && !ex) {
    body = (
      <div className="notice lv-warning">
        <p>{t(isUrgentReport(event) ? 'event.urgent_skip' : 'event.measured_skip')}</p>
        <Link className="btn-primary" to={`/warning?event=${event.id}`}>{t('log.open_warning')}</Link>
      </div>
    )
  } else if (withheld) {
    body = <p className="notice lv-hold">{t('event.withheld')}</p>
  } else if (!ex) {
    body = <p className="panel-empty muted">{t('event.pending')}</p>
  } else {
    body = (
      <ol className="guidance">
        <li>
          <span className="guidance-label">{t('event.line.category')}</span>
          <span>{t(`hrp.${ex.category}`)}</span>
        </li>
        <li>
          <span className="guidance-label">{t('event.line.condition')}</span>
          <div>
            <b>
              {conditionLabel(ex.condition_id, lang)
                ? t('event.possibility', { name: conditionLabel(ex.condition_id, lang) })
                : t('event.condition_unlisted')}
            </b>
            {ex.lines.map((line, i) => <p key={i}>{line}</p>)}
            <div className="cites">{ex.cites.map((c) => <span key={c} className="cite">{c}</span>)}</div>
          </div>
        </li>
        <li>
          <span className="guidance-label">{t('event.line.today')}</span>
          <ul className="actions">
            {(event.risk?.actions ?? []).map((a, i) => (
              <li key={i}>
                <label>
                  <input type="checkbox" /> {/* TODO: POST /events/{id}/action/{i}/done when the backend has it */}
                  <span>{a.text}</span>
                </label>
                <span className="cite">{a.doc}</span>
              </li>
            ))}
          </ul>
        </li>
      </ol>
    )
  }

  return (
    <section className="panel">
      <div className="panel-head">
        <h2>{t('event.guidance')}</h2>
        <span className="muted small">{t('event.guidance_by')}</span>
      </div>
      {body}
    </section>
  )
}

// Five code checks on the model sentence, and every run (a discarded run stays visible)
function Verification({ event }) {
  const { t } = useT()
  const runs = event.runs ?? []
  if (runs.length === 0) {
    return (
      <section className="panel">
        <div className="panel-head"><h2>{t('event.verify')}</h2></div>
        <p className="panel-empty muted">{event.level === 'warning' ? t('event.verify_skipped') : t('event.verify_none')}</p>
      </section>
    )
  }
  const last = runs[runs.length - 1]
  return (
    <section className="panel">
      <div className="panel-head">
        <h2>{t('event.verify')}</h2>
        <span className={`badge ${last.ok ? 'lv-normal' : 'lv-hold'}`}>{t('event.verified', { n: event.verified })}</span>
      </div>
      <ul className="checks">
        {VERIFY_CHECKS.map((c) => {
          const ok = !last.fails.includes(c)
          return (
            <li key={c} className={ok ? 'lv-normal' : 'lv-warning'}>
              <span aria-hidden="true">{ok ? '✔' : '✖'}</span> {t(`check.${c}`)}
            </li>
          )
        })}
      </ul>
      <ol className="runs">
        {runs.map((r) => (
          <li key={r.n} className={r.ok ? 'ok' : 'discarded'}>
            <b>{t('event.run', { n: r.n })}</b>{' '}
            {r.ok ? t('event.run_passed') : t('event.run_discarded', { checks: r.fails.map((f) => t(`check.${f}`)).join(', ') })}
            {r.note && <span className="muted"> — {r.note}</span>}
          </li>
        ))}
      </ol>
    </section>
  )
}

// Share with the medical officer, or dismiss with a required reason (logged and visible to the CMO)
function Response({ event }) {
  const { t } = useT()
  const [shared, setShared] = useState(event.shared)
  const [overriding, setOverriding] = useState(false)
  const [reason, setReason] = useState('')
  const [overridden, setOverridden] = useState(null)

  return (
    <section className="panel">
      <div className="panel-head"><h2>{t('event.response')}</h2></div>
      <div className="response">
        {/* TODO: POST /events/{id}/share and /override when the backend has them; local only for now */}
        <button type="button" className="btn-secondary" disabled={shared} onClick={() => setShared(true)}>
          {shared ? `✔ ${t('event.shared')}` : t('event.share')}
        </button>
        {!overridden && !overriding && (
          <button type="button" className="btn-ghost" onClick={() => setOverriding(true)}>{t('event.override')}</button>
        )}
        {overriding && (
          <form className="override" onSubmit={(e) => { e.preventDefault(); if (reason) { setOverridden(reason); setOverriding(false) } }}>
            <label htmlFor="override-reason">{t('event.override_reason')}</label>
            <select id="override-reason" value={reason} onChange={(e) => setReason(e.target.value)} required>
              <option value="">{t('event.override_pick')}</option>
              {OVERRIDE_REASONS.map((r) => <option key={r} value={r}>{t(`override.${r}`)}</option>)}
            </select>
            <button type="submit" className="btn-secondary" disabled={!reason}>{t('event.override_confirm')}</button>
            <button type="button" className="btn-ghost" onClick={() => setOverriding(false)}>{t('common.cancel')}</button>
          </form>
        )}
        {overridden && <p className="muted">{t('event.overridden', { reason: t(`override.${overridden}`) })}</p>}
        {(shared || overridden) && <p className="muted small">{t('event.local_only')}</p>}
      </div>
    </section>
  )
}
