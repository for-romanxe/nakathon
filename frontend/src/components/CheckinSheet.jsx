// CheckinSheet.jsx — morning check-in (spec §8, target 30 s). The system pre-fills every answer;
// the crew member only taps to correct. Symptoms default to "none"; "yes" leads to the Log chat.
import { useEffect, useRef, useState } from 'react'
import { useT } from '../i18n/index.jsx'

const SCALES = ['sleep_quality', 'mood', 'fatigue']

// TODO: pre-fill should come from the backend (band data + yesterday); fixed defaults until then
const DEFAULTS = { sleep_quality: 3, mood: 3, fatigue: 3, symptoms: 'none' }

export default function CheckinSheet({ onSubmit, onSymptoms, onClose }) {
  const { t } = useT()
  const [answers, setAnswers] = useState(DEFAULTS)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState(false)
  const firstButton = useRef(null)

  useEffect(() => { firstButton.current?.focus() }, [])

  const set = (key, value) => setAnswers((a) => ({ ...a, [key]: value }))

  async function submit() {
    setSaving(true)
    setError(false)
    try {
      await onSubmit({ kind: 'morning', answers })
      if (answers.symptoms === 'yes') onSymptoms()
    } catch {
      setError(true)
      setSaving(false)
    }
  }

  return (
    <div className="sheet-backdrop">
      <div className="sheet" role="dialog" aria-modal="true" aria-labelledby="checkin-title">
        <div className="sheet-head">
          <h2 id="checkin-title">{t('checkin.title')}</h2>
          <button type="button" className="btn-ghost" onClick={onClose} aria-label={t('common.close')}>✕</button>
        </div>
        <p className="muted">{t('checkin.hint')}</p>

        {SCALES.map((key, i) => (
          <fieldset key={key} className="scale">
            <legend>{t(`checkin.${key}`)}</legend>
            <div className="scale-buttons">
              {[1, 2, 3, 4, 5].map((n) => (
                <button
                  key={n}
                  ref={i === 0 && n === 1 ? firstButton : null}
                  type="button"
                  className={answers[key] === n ? 'selected' : ''}
                  aria-pressed={answers[key] === n}
                  onClick={() => set(key, n)}
                >
                  {n}
                </button>
              ))}
            </div>
            <div className="scale-ends muted">
              <span>{t(`checkin.${key}.low`)}</span>
              <span>{t(`checkin.${key}.high`)}</span>
            </div>
          </fieldset>
        ))}

        <fieldset className="scale">
          <legend>{t('checkin.symptoms')}</legend>
          <div className="choice-buttons">
            {['none', 'yes'].map((v) => (
              <button
                key={v}
                type="button"
                className={answers.symptoms === v ? 'selected' : ''}
                aria-pressed={answers.symptoms === v}
                onClick={() => set('symptoms', v)}
              >
                {t(`checkin.symptoms.${v}`)}
              </button>
            ))}
          </div>
        </fieldset>

        {error && <p className="error">{t('checkin.error')}</p>}
        <button type="button" className="btn-primary" onClick={submit} disabled={saving}>
          {saving ? t('common.saving') : t('checkin.submit')}
        </button>
      </div>
    </div>
  )
}
