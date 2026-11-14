import { useEffect, useRef, useState } from 'react'
import { api } from '../api/client.js'
import { formatTs } from '../api/contract.js'
import { useT } from '../i18n/index.jsx'

export default function MedicationIntakes({ crew }) {
  const { t } = useT()
  const [entries, setEntries] = useState(null)
  const [name, setName] = useState('')
  const [amount, setAmount] = useState('')
  const [reference, setReference] = useState(null)
  const [saving, setSaving] = useState(false)
  const [loadFailed, setLoadFailed] = useState(false)
  const [saveFailed, setSaveFailed] = useState(false)
  const [saved, setSaved] = useState(false)
  const pending = useRef(null)
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
    const payload = countUnit
      ? { product_id: reference.id, unit_count: count }
      : { name: cleanName, amount: amount.trim() }
    setSaving(true)
    setSaveFailed(false)
    setSaved(false)
    try {
      const key = JSON.stringify(payload)
      if (pending.current?.key !== key) {
        pending.current = { key, entry: { request_id: crypto.randomUUID(), ...payload } }
      }
      const entry = await api.recordMedicationIntake(crew, pending.current.entry)
      setEntries((current) => [entry, ...(current ?? []).filter((row) => row.id !== entry.id)].slice(0, 50))
      pending.current = null
      setName('')
      setAmount('')
      setSaved(true)
    } catch {
      setSaveFailed(true)
    } finally {
      setSaving(false)
    }
  }

  return (
    <section className="panel">
      <div className="panel-head"><h2>{t('intake.title')}</h2></div>
      <MedicationReferences reference={reference} disabled={saving} onSelect={(row) => { setReference(row); setAmount('') }} />
      <div className="panel-empty">
        <form className="intake-form" onSubmit={submit}>
          {!countUnit && <label>{t('intake.name')}
            <input required maxLength={120} value={name} onChange={(e) => setName(e.target.value)} disabled={saving} />
          </label>}
          <label>{t('intake.amount')}{countUnit && ` (${countUnit})`}
            <input required type={countUnit ? 'number' : 'text'} min={1} max={1000000} step={1}
              maxLength={80} value={amount} onChange={(e) => setAmount(e.target.value)} disabled={saving} />
          </label>
          <button type="submit" className="btn-secondary"
            disabled={saving || entries == null || (!countUnit && !name.trim()) || !validAmount}>{t('intake.save')}</button>
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
