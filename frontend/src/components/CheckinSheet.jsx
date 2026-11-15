// CheckinSheet.jsx — the two daily check-ins (spec §8, target 30 s each). The system pre-fills every answer;
// the crew member only taps to correct. Symptoms default to "none"; "yes" leads to the Log chat.
//   morning: sleep quality, mood, fatigue (1–5) + symptoms
//   evening (check-out, optional): how today went, stress (1–5), enough water + symptoms
// Answer names follow CONTRACT §5.
import { useEffect, useRef, useState } from 'react'
import { formatMetric } from '../api/contract.js'
import { useT } from '../i18n/index.jsx'

const FORMS = {
  morning: {
    scales: ['sleep_quality', 'mood', 'fatigue'],
    defaults: { sleep_quality: 3, mood: 3, fatigue: 3, symptoms: 'none' },
    title: 'checkin.title',
    hint: 'checkin.hint',
    submit: 'checkin.submit',
  },
  evening: {
    scales: ['day_rating', 'stress'],
    yesNo: ['hydration_ok'],
    defaults: { day_rating: 3, stress: 3, hydration_ok: true, symptoms: 'none' },
    title: 'checkin.evening.title',
    hint: 'checkin.evening.hint',
    submit: 'checkin.evening.submit',
  },
}

export default function CheckinSheet({ kind = 'morning', prefill, onSubmit, onSymptoms, onClose }) {
  const { t } = useT()
  const form = FORMS[kind] ?? FORMS.morning
  // answers belong to the kind they were given for: if kind changes on the same sheet, the old answers are dropped
  // and the new kind starts from its own defaults (never submitting morning answers as an evening check-out)
  const defaults = kind === 'morning' ? { ...form.defaults, ...prefill?.answers } : form.defaults
  const [state, setState] = useState({ kind, answers: defaults })
  const answers = state.kind === kind ? state.answers : defaults
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState(false)
  const firstButton = useRef(null)

  useEffect(() => { firstButton.current?.focus() }, [])

  const set = (key, value) => setState((s) => ({
    kind,
    answers: { ...(s.kind === kind ? s.answers : defaults), [key]: value },
  }))

  async function submit() {
    setSaving(true)
    setError(false)
    try {
      await onSubmit({ kind, answers })
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
          <h2 id="checkin-title">{t(form.title)}</h2>
          <button type="button" className="btn-ghost" onClick={onClose} aria-label={t('common.close')}>✕</button>
        </div>
        <p className="muted">{t(form.hint)}</p>
        {kind === 'morning' && Object.keys(prefill?.answers ?? {}).length > 0 &&
          <p className="muted">{t('checkin.previous_answers')}</p>}
        {kind === 'morning' && prefill?.sleep_hours != null &&
          <p className="muted">{t('checkin.band_sleep', { hours: formatMetric('sleep', prefill.sleep_hours) })}</p>}

        {form.scales.map((key, i) => (
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

        {(form.yesNo ?? []).map((key) => (
          <fieldset key={key} className="scale">
            <legend>{t(`checkin.${key}`)}</legend>
            <div className="choice-buttons">
              {[true, false].map((v) => (
                <button
                  key={String(v)}
                  type="button"
                  className={answers[key] === v ? 'selected' : ''}
                  aria-pressed={answers[key] === v}
                  onClick={() => set(key, v)}
                >
                  {t(v ? 'common.yes' : 'common.no')}
                </button>
              ))}
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
          {saving ? t('common.saving') : t(form.submit)}
        </button>
      </div>
    </div>
  )
}
