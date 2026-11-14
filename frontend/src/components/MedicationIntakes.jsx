import { useEffect, useRef, useState } from 'react'
import { api } from '../api/client.js'
import { formatTs } from '../api/contract.js'
import { useT } from '../i18n/index.jsx'
import { useMission } from '../mission.jsx'

export default function MedicationIntakes({ crew }) {
  const { t } = useT()
  const [entries, setEntries] = useState(null)
  const [name, setName] = useState('')
  const [amount, setAmount] = useState('')
  const [reference, setReference] = useState(null)
  const [saving, setSaving] = useState(false)
  const [loadFailed, setLoadFailed] = useState(false)
  const [saveFailed, setSaveFailed] = useState(false)
  const [retryPending, setRetryPending] = useState(false)
  const [saved, setSaved] = useState(false)
  const pending = useRef(null)
  const editingLocked = saving || retryPending
  const countUnit = reference?.count_unit
  const count = Number(amount)
  const validAmount = countUnit ? Number.isInteger(count) && count > 0 && count <= 1000000 : Boolean(amount.trim())

  useEffect(() => {
    let active = true
    api.getMedicationIntakes(crew).then((result) => {
      if (active) setEntries(result.entries)
    }).catch(() => {
      if (active) setLoadFailed(true)
    })
    return () => { active = false }
  }, [crew])

  async function submit(event) {
    event.preventDefault()
    const cleanName = name.trim()
    if (saving || !validAmount || (!countUnit && !cleanName)) return
    setSaving(true)
    setSaveFailed(false)
    setSaved(false)
    try {
      pending.current ??= {
        request_id: crypto.randomUUID(),
        ...(countUnit ? { product_id: reference.id, unit_count: count } : { name: cleanName, amount: amount.trim() }),
      }
      const entry = await api.recordMedicationIntake(crew, pending.current)
      setEntries((current) => [entry, ...(current ?? []).filter((row) => row.id !== entry.id)]
        .sort((a, b) => b.ts.localeCompare(a.ts) || b.id - a.id).slice(0, 50))
      pending.current = null
      setRetryPending(false)
      setName('')
      setAmount('')
      setSaved(true)
    } catch (error) {
      if (['invalid_request', 'intake_product_unavailable', 'intake_conflict'].includes(error.code)) {
        pending.current = null
      }
      setRetryPending(pending.current !== null)
      setSaveFailed(true)
    } finally {
      setSaving(false)
    }
  }

  return (
    <section className="panel">
      <div className="panel-head"><h2>{t('intake.title')}</h2></div>
      <MedicationReferences reference={reference} disabled={editingLocked}
        onSelect={(row) => {
          if (editingLocked || pending.current !== null) return
          setReference(row)
          setAmount('')
        }} />
      {countUnit && <IntakeSummary key={reference.id} crew={crew} reference={reference} entries={entries} />}
      <div className="panel-empty">
        {countUnit && !reference.intake_limits && <p className="muted">{t('intake.record_only')}</p>}
        <form className="intake-form" onSubmit={submit}>
          {!countUnit && <label>{t('intake.name')}
            <input required maxLength={120} value={name} onChange={(e) => setName(e.target.value)} disabled={editingLocked} />
          </label>}
          <label>{t('intake.amount')}{countUnit && ` (${countUnit})`}
            <input required type={countUnit ? 'number' : 'text'} min={1} max={1000000} step={1}
              maxLength={80} value={amount} onChange={(e) => setAmount(e.target.value)} disabled={editingLocked} />
          </label>
          <button type="submit" className="btn-secondary"
            disabled={saving || entries == null || (!countUnit && !name.trim()) || !validAmount}>
            {editingLocked && !saving ? t('intake.retry_save') : t('intake.save')}
          </button>
        </form>
        {loadFailed && <p role="alert" className="error">{t('intake.load_failed')}</p>}
        {saveFailed && <p role="alert" className="error">{t('event.save_failed')}</p>}
        {saved && <p role="status">{t('intake.saved')}</p>}
        {entries?.length === 0 && <p className="muted">{t('intake.empty')}</p>}
        {entries?.length > 0 && (
          <ul>
            {entries.map((entry) => (
              <li key={entry.id}>{entry.name} · {entry.amount} · <time dateTime={entry.ts}>{formatTs(entry.ts)}</time></li>
            ))}
          </ul>
        )}
      </div>
    </section>
  )
}

function IntakeSummary({ crew, reference, entries }) {
  const { t } = useT()
  const { mission } = useMission()
  const sol = mission?.clock?.sol
  const time = mission?.clock?.time
  const [result, setResult] = useState(null)

  useEffect(() => {
    const request = new AbortController()
    api.getMedicationIntakeSummary(crew, reference.id, request.signal).then((summary) => {
      if (!request.signal.aborted) setResult({ summary, sol, time, entries })
    }).catch(() => {
      if (!request.signal.aborted) setResult({ summary: null, sol, time, entries })
    })
    return () => request.abort()
  }, [crew, reference.id, sol, time, entries])

  const current = result?.sol === sol && result?.time === time && result?.entries === entries ? result : null
  const summary = current?.summary
  return (
    <section className="panel-empty">
      <h3>{t('intake.summary')}</h3>
      {!current && <p role="status">{t('common.loading')}</p>}
      {current && !summary && <p role="alert" className="error">{t('intake.summary_failed')}</p>}
      {summary && (
        <>
          <p>{t('intake.recorded_24h', { n: summary.recorded_units_24h, unit: reference.count_unit })}</p>
          <p>{summary.minutes_since_last == null ? t('intake.no_product_record')
            : t('intake.elapsed', { n: summary.minutes_since_last })}</p>
          {summary.text_entries_24h > 0 && <p className="muted">{t('intake.text_excluded', { n: summary.text_entries_24h })}</p>}
          <IntakeLimitComparison comparison={summary.limit_comparison} unit={reference.count_unit} />
          {summary.recorded_limit_exceeded && <p>{t('intake.limit_exceeded')}</p>}
          {summary.shortest_violating_gap_minutes != null &&
            <p>{t('intake.violating_gap', { n: summary.shortest_violating_gap_minutes })}</p>}
          <IntakeProductReview review={summary.product_review} reason={summary.limit_comparison.reason} />
        </>
      )}
    </section>
  )
}

function IntakeLimitComparison({ comparison, unit }) {
  const { t } = useT()
  return (
    <>
      {comparison.status === 'hold' ? <p>{t(`intake.limits.${comparison.reason}`)}</p> : (
        <>
          {comparison.minutes_below_minimum_interval > 0 &&
            <p>{t('intake.interval_short', { n: comparison.minutes_below_minimum_interval })}</p>}
          {!comparison.exceeds_24h_limit &&
            <p>{t('intake.below_limit', { n: comparison.units_below_24h_limit, unit })}</p>}
        </>
      )}
      <p className="muted">{t('medref.confirm')}</p>
    </>
  )
}

function IntakeProductReview({ review, reason }) {
  const { t } = useT()
  return (
    <>
      <p className="muted">{t('intake.interactions_scope')}</p>
      {review.unknown_product_history && reason !== 'unknown_products' &&
        <p>{t('intake.limits.unknown_products')}</p>}
      {review.shared_ingredients.map((row) => (
        <p key={row.product_id}>
          {t('intake.shared_ingredients', { product: row.product, ingredients: row.ingredients.join(', ') })}
        </p>
      ))}
      {review.cautions.map((row) => (
        <p key={`${row.product_id}-${row.source_product_id}`}>
          {row.product} · {row.text}{' '}
          <a href={row.label_url} target="_blank" rel="noreferrer">{t('medref.source')} · {row.label_revision}</a>
        </p>
      ))}
    </>
  )
}

function MedicationReferences({ reference, disabled, onSelect }) {
  const { t } = useT()
  const [references, setReferences] = useState(null)
  const [failed, setFailed] = useState(false)

  useEffect(() => {
    let active = true
    api.getMedicationReferences().then((result) => {
      if (active) setReferences(result.references)
    }).catch(() => {
      if (active) setFailed(true)
    })
    return () => { active = false }
  }, [])

  return (
    <section className="panel-empty">
      <h3>{t('medref.title')}</h3>
      {failed && <p role="alert" className="error">{t('medref.failed')}</p>}
      {!failed && references == null && <p role="status">{t('common.loading')}</p>}
      {references?.length === 0 && <p className="muted">{t('medref.hold')}</p>}
      {references?.length > 0 && (
        <label>{t('medref.select')}{' '}
          <select value={reference?.id ?? ''} disabled={disabled}
            onChange={(e) => onSelect(references.find((row) => row.id === e.target.value) ?? null)}>
            <option value="">{t('medref.placeholder')}</option>
            {references.map((row) => <option key={row.id} value={row.id}>{row.product} · {row.strength}</option>)}
          </select>
        </label>
      )}
      {reference && (
        <div>
          <h4>{t('medref.directions')}</h4>
          <p>{reference.directions}</p>
          <h4>{t('medref.warnings')}</h4>
          <p>{reference.warnings}</p>
          <p className="muted">{t('medref.confirm')}</p>
          <a href={reference.label_url} target="_blank" rel="noreferrer">
            {t('medref.source')} · {reference.label_revision}
          </a>
        </div>
      )}
    </section>
  )
}
