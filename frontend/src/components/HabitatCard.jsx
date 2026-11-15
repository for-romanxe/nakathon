// HabitatCard.jsx — "the habitat changed, not you" (#46, #47 FE-02). One row per adjustment the backend made or
// proposes for this crew member: what changed (before -> after), why (sentence, numbers, sources), and the one
// thing the crew can do about it (approve a proposal, undo an applied change). The next sol shows what was
// observed after the change. The backend's rules decide every adjustment and state; this card only shows them.
import { useEffect, useState } from 'react'
import { api } from '../api/client.js'
import { METRICS, metricLabel, formatMetric } from '../api/contract.js'
import Cite from './Cite.jsx'
import { useT } from '../i18n/index.jsx'

const formatZ = (z) => (z == null ? '' : ` (${z > 0 ? '+' : z < 0 ? '−' : '±'}${Math.abs(z).toFixed(1)}σ)`)
const reading = (metric, value, z) => `${formatMetric(metric, value)} ${METRICS[metric]?.unit ?? ''}${formatZ(z)}`.trim()

// A schedule change applied without approval only happens in the blackout (#47 comment: the crew can veto it)
const noApproval = (a) => a.target === 'schedule' && a.tier === 'auto'

function stateKey(a) {
  if (a.status === 'applied') return noApproval(a) ? 'habitat.state.applied_no_approval' : a.approved_by ? 'habitat.state.approved' : 'habitat.state.auto'
  return `habitat.state.${a.status}`
}

// CONTRACT (#59): 403 owner only, 404 action_not_found, 409 action_stale
function failureKey(e) {
  if (e?.code === 'action_stale' || e?.code === 'http_409' || e?.code === 'action_not_found' || e?.code === 'http_404') return 'habitat.stale'
  if (e?.code === 'forbidden' || e?.code === 'http_403') return 'habitat.forbidden'
  return 'habitat.failed'
}

function Row({ action: a, lang, onChange, onStale }) {
  const { t } = useT()
  const [busy, setBusy] = useState(false)
  const [failed, setFailed] = useState(null)

  async function run(call) {
    setBusy(true)
    setFailed(null)
    try {
      onChange(await call(a.id, lang))
    } catch (e) {
      const key = failureKey(e)
      setFailed(key)
      if (key === 'habitat.stale') onStale() // the action changed elsewhere: show what it is now
    } finally {
      setBusy(false)
    }
  }

  const changed = a.status === 'applied' || a.status === 'released'
  return (
    <li className={`habitat-row habitat-${a.status}`}>
      <div className="habitat-top">
        <span className="habitat-target">{t(`habitat.target.${a.target}`)}</span>
        <span className="habitat-state">{t(stateKey(a), { who: a.approved_by?.toUpperCase() })}</span>
      </div>
      <p className="habitat-change">
        <span className={changed ? 'habitat-before' : ''}>{a.before}</span>
        <span aria-hidden="true"> → </span>
        <span className="sr-only">{t('habitat.to')}</span>
        <span className={a.status === 'undone' ? 'habitat-before' : 'habitat-after'}>{a.after}</span>
      </p>
      <div className="habitat-why">
        <p>{a.reason_text ?? <span className="muted">{t('habitat.reason_hold')}</span>}</p>
        <p className="muted small">
          {t('habitat.because', { metric: metricLabel(a.reason.metric, lang), value: reading(a.reason.metric, a.reason.value, a.reason.z) })}
          {' '}{a.cite_ids.map((c) => <Cite key={c} id={c} />)}
        </p>
      </div>
      {a.outcome && (
        <div className="habitat-outcome">
          <p className="small">{t('habitat.outcome')}</p>
          <ul>
            {a.outcome.metrics.map((m) => (
              <li key={m.metric} className="num small">
                {metricLabel(m.metric, lang)}: {reading(m.metric, m.before, m.before_z)} → {reading(m.metric, m.after, m.after_z)}
              </li>
            ))}
          </ul>
          <p className="muted small">{t(a.outcome.released ? 'habitat.released' : 'habitat.kept')} {t('habitat.outcome_note')}</p>
        </div>
      )}
      {(a.status === 'proposed' || a.status === 'applied') && (
        <div className="habitat-actions">
          {a.status === 'proposed' && (
            <button type="button" className="btn-primary" disabled={busy} onClick={() => run(api.approveHabitatAction)}>
              {t('habitat.approve')}
            </button>
          )}
          {a.status === 'applied' && (
            <button type="button" className="btn-secondary" disabled={busy} onClick={() => run(api.undoHabitatAction)}>
              {t(noApproval(a) ? 'habitat.veto' : 'habitat.undo')}
            </button>
          )}
        </div>
      )}
      {/* outside the buttons: after a 409 the reloaded action may have none, and the note must stay */}
      {failed && <p role="alert" className="error small">{t(failed)}</p>}
    </li>
  )
}

export default function HabitatCard({ crewId, sol, lang }) {
  const { t } = useT()
  const [actions, setActions] = useState(null)
  const [reload, setReload] = useState(0) // bump to read the list again (after a 409)

  useEffect(() => {
    let alive = true
    api.getHabitatActions(crewId, lang)
      .then((list) => alive && setActions(list))
      .catch(() => alive && setActions((prev) => prev ?? [])) // the card is extra: a failed fetch leaves Today as it was
    return () => { alive = false }
  }, [crewId, sol, lang, reload])

  if (!actions?.length) return null
  const replace = (next) => setActions((list) => list.map((a) => (a.id === next.id ? next : a)))
  const stale = () => setReload((n) => n + 1)
  return (
    <section className="panel habitat">
      <div className="panel-head">
        <h2>{t('habitat.title')}</h2>
        <span className="muted small">{t('habitat.simulated')}</span>
      </div>
      <ul className="habitat-list">
        {actions.map((a) => <Row key={a.id} action={a} lang={lang} onChange={replace} onStale={stale} />)}
      </ul>
    </section>
  )
}
