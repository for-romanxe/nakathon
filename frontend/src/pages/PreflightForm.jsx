// PreflightForm.jsx: the current crew member's preflight reference values (GET/PUT /crew/{id}/preflight).
// Fixture mode has no backend to store them, so it explains that instead of pretending to save.
import { useEffect, useState } from 'react'
import { api, USE_FIXTURES } from '../api/client.js'
import { METRIC_KEYS, METRICS, metricLabel } from '../api/contract.js'
import { useT } from '../i18n/index.jsx'
import { CURRENT_CREW } from '../session.js'

// {metric:{value,source}} -> {metric:number}, dropping anything that is not a finite number
function savedNumbers(values) {
  const out = {}
  for (const [key, entry] of Object.entries(values ?? {})) {
    if (typeof entry?.value === 'number' && Number.isFinite(entry.value)) out[key] = entry.value
  }
  return out
}

const asInput = (saved, metric) => (saved?.[metric] != null ? String(saved[metric]) : '')

export default function PreflightForm() {
  const { t, lang } = useT()
  const [saved, setSaved] = useState(null)
  const [metric, setMetric] = useState(METRIC_KEYS[0])
  const [input, setInput] = useState('')
  const [status, setStatus] = useState(null) // 'saved' | 'invalid' | 'error'
  const [busy, setBusy] = useState(false)

  useEffect(() => {
    if (USE_FIXTURES) return undefined
    let active = true
    api.getPreflight(CURRENT_CREW)
      .then((res) => {
        if (!active) return
        const values = savedNumbers(res?.values)
        setSaved(values)
        setInput(asInput(values, METRIC_KEYS[0])) // the form stays disabled until this load, so the metric is still the first
      })
      .catch(() => { if (active) setStatus('error') })
    return () => { active = false }
  }, [])

  if (USE_FIXTURES) {
    return (
      <section className="panel" aria-labelledby="preflight-title">
        <h2 id="preflight-title">{t('preflight.title')}</h2>
        <p className="muted" role="note">{t('preflight.fixture')}</p>
      </section>
    )
  }

  async function submit(event) {
    event.preventDefault()
    const value = input.trim() === '' ? NaN : Number(input)
    if (!Number.isFinite(value) || value < 0) {
      setStatus('invalid')
      return
    }
    setBusy(true)
    setStatus(null)
    try {
      const res = await api.putPreflight(CURRENT_CREW, { values: { [metric]: value } })
      const values = savedNumbers(res.values)
      setSaved(values)
      setInput(asInput(values, metric))
      setStatus('saved')
    } catch {
      setStatus('error')
    } finally {
      setBusy(false)
    }
  }

  const unit = METRICS[metric]?.unit
  return (
    <section className="panel" aria-labelledby="preflight-title">
      <h2 id="preflight-title">{t('preflight.title')}</h2>
      <form onSubmit={submit} noValidate>
        <fieldset disabled={saved === null || busy}>
          <legend className="sr-only">{t('preflight.title')}</legend>
          <label>
            {t('preflight.metric')}{' '}
            <select value={metric} onChange={(event) => {
              const id = event.target.value
              setMetric(id)
              setInput(asInput(saved, id))
              setStatus(null)
            }}>
              {METRIC_KEYS.map((id) => <option key={id} value={id}>{metricLabel(id, lang)}</option>)}
            </select>
          </label>
          <label>
            {t('preflight.value')}{' '}
            <input type="number" min="0" step="any" inputMode="decimal" value={input}
              aria-invalid={status === 'invalid'} aria-describedby={status === 'invalid' ? 'preflight-invalid' : undefined}
              onChange={(event) => { setInput(event.target.value); setStatus(null) }} />
            {unit && <span className="muted small"> {unit}</span>}
          </label>
          <button type="submit" className="btn-secondary">{t('preflight.save')}</button>
        </fieldset>
      </form>
      {status === 'invalid' && <p id="preflight-invalid" role="alert" className="error">{t('preflight.invalid')}</p>}
      {status === 'error' && <p role="alert" className="error">{t('common.error')}</p>}
      {status === 'saved' && <p role="status" className="muted">{t('preflight.saved')}</p>}
    </section>
  )
}
