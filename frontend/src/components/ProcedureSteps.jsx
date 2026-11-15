// ProcedureSteps.jsx — the local procedure for a warning, with two-person consent (#46 Act 3, #47 FE-03).
// Every step opens its source paragraph. A step marked needs_consent goes ahead only after the designated crew
// members (e.g. C1 and C3 for C4's chest pain) each agree from their own session; the screen shows 0/2, 1/2, 2/2
// and re-reads every few seconds so a consent given in another tab shows up. The backend decides who may consent
// and when a step is done; this only shows it. No procedure (404 / not available) -> `fallback` is shown instead.
import { useCallback, useEffect, useState } from 'react'
import { api } from '../api/client.js'
import { CURRENT_CREW } from '../session.js'
import { useMission } from '../mission.jsx'
import { agreed, usableProcedure } from '../procedureCheck.js'
import Cite from './Cite.jsx'
import { useT } from '../i18n/index.jsx'

const POLL_MS = 5000
const crewList = (ids) => ids.map((c) => c.toUpperCase()).join(' · ')

function ConsentLine({ proc, step, onApprove, busy, error }) {
  const { t } = useT()
  const mine = step.approvals.some((a) => a.crew === CURRENT_CREW)
  const canConsent = proc.consenters.includes(CURRENT_CREW)
  // shown count: designated consenters who agreed, each once. Whether the step is done stays the backend's call
  const n = agreed(proc, step).length
  return (
    <div className={`consent ${step.done ? 'consent-done' : ''}`}>
      <span className="consent-count num">{t('proc.consent.count', { n, of: proc.required })}</span>
      <ul className="consent-people">
        {proc.consenters.map((c) => {
          const got = step.approvals.some((a) => a.crew === c)
          return <li key={c} className={got ? 'got' : ''}>{got ? '✔' : '○'} {c.toUpperCase()}</li>
        })}
      </ul>
      {step.done ? (
        <p className="small">{t(step.kind === 'report' ? 'proc.consent.report_saved' : 'proc.consent.done')}</p>
      ) : step.step_id !== proc.current_step ? (
        <p className="muted small">{t('proc.consent.later')}</p>
      ) : mine ? (
        <p className="small">{t('proc.consent.waiting', { who: crewList(proc.consenters.filter((c) => !step.approvals.some((a) => a.crew === c))) })}</p>
      ) : canConsent ? (
        <button type="button" className="btn-warning align-start" disabled={busy} onClick={() => onApprove(step.step_id)}>
          {t('proc.consent.approve', { me: CURRENT_CREW.toUpperCase() })}
        </button>
      ) : (
        <p className="muted small">{t('proc.consent.who', { who: crewList(proc.consenters) })}</p>
      )}
      {error && <p role="alert" className="error small">{t(error)}</p>}
    </div>
  )
}

export default function ProcedureSteps({ eventId, fallback = null }) {
  const { t, lang } = useT()
  const { mission } = useMission()
  const [proc, setProc] = useState(undefined) // undefined loading, null none
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState(null)

  const load = useCallback(() => api.getProcedure(eventId, lang).then((p) => setProc(usableProcedure(p)))
    .catch(() => setProc((p) => p ?? null)), [eventId, lang])

  useEffect(() => {
    if (eventId == null) return undefined // a metrics-only warning has no event, so no procedure
    load()
    const id = setInterval(load, POLL_MS) // the other consenter works in another session
    return () => clearInterval(id)
  }, [eventId, load])

  async function approve(stepId) {
    setBusy(true)
    setError(null)
    try {
      setProc(usableProcedure(await api.approveProcedureStep(eventId, stepId, lang)))
    } catch (e) {
      setError(e?.code === 'forbidden' || e?.code === 'http_403' ? 'proc.consent.forbidden'
        : e?.code === 'state_conflict' || e?.code === 'http_409' ? 'proc.consent.conflict' : 'proc.consent.failed')
      load()
    } finally {
      setBusy(false)
    }
  }

  if (eventId == null) return fallback
  if (proc === undefined) return <p className="muted">{t('common.loading')}</p>
  if (!proc?.available) return fallback

  const blackout = mission?.comms_state === 'blackout'
  return (
    <div className="procedure">
      <p className="muted small">
        {t(proc.medical_available === false ? 'proc.steps.report_only' : 'proc.steps.source')} · {t('proc.steps.viewer', { me: CURRENT_CREW.toUpperCase(), patient: proc.patient?.toUpperCase() ?? '–' })}
      </p>
      <ol className="procedure-steps">
        {proc.steps.map((s) => (
          <li key={s.step_id} className={s.step_id === proc.current_step ? 'current' : ''}>
            <p>{s.text}</p>
            {s.cite_id && <p className="small"><Cite id={s.cite_id} /></p>}
            {s.kind === 'contact' && blackout && <p className="small proc-blackout">{t('proc.steps.contact_blackout')}</p>}
            {s.needs_consent && <ConsentLine proc={proc} step={s} onApprove={approve} busy={busy} error={error} />}
          </li>
        ))}
      </ol>
      <button type="button" className="btn-ghost align-start small" onClick={load}>{t('proc.consent.refresh')}</button>
      {proc.medical_available === false && fallback}
    </div>
  )
}
