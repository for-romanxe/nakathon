import { useEffect, useRef, useState } from 'react'
import { api } from '../api/client.js'
import { formatTs } from '../api/contract.js'
import { useT } from '../i18n/index.jsx'

export default function MedicationIntakes({ crew }) {
  const { t } = useT()
  const [entries, setEntries] = useState(null)
  const [name, setName] = useState('')
  const [amount, setAmount] = useState('')
  const [saving, setSaving] = useState(false)
  const [loadFailed, setLoadFailed] = useState(false)
  const [saveFailed, setSaveFailed] = useState(false)
  const [saved, setSaved] = useState(false)
  const pending = useRef(null)

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
    const cleanAmount = amount.trim()
    if (saving || !cleanName || !cleanAmount) return
    setSaving(true)
    setSaveFailed(false)
    setSaved(false)
    try {
      if (pending.current?.name !== cleanName || pending.current?.amount !== cleanAmount) {
        pending.current = { request_id: crypto.randomUUID(), name: cleanName, amount: cleanAmount }
      }
      const entry = await api.recordMedicationIntake(crew, pending.current)
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
      <div className="panel-empty">
        <form className="intake-form" onSubmit={submit}>
          <label>{t('intake.name')}
            <input required maxLength={120} value={name} onChange={(e) => setName(e.target.value)} disabled={saving} />
          </label>
          <label>{t('intake.amount')}
            <input required maxLength={80} value={amount} onChange={(e) => setAmount(e.target.value)} disabled={saving} />
          </label>
          <button type="submit" className="btn-secondary"
            disabled={saving || entries == null || !name.trim() || !amount.trim()}>{t('intake.save')}</button>
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
