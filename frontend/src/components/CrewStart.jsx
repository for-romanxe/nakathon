// CrewStart.jsx — first screen in demo mode (no access codes on the backend): pick which crew member is using the app.
// The choice is kept for this browser tab (session.js); Settings can switch it later. In sign-in mode the login
// screen is used instead and this screen never shows.
import { useState } from 'react'
import { api } from '../api/client.js'
import { CREW_IDS, switchViewer } from '../session.js'
import { useT } from '../i18n/index.jsx'

const MEDICAL_OFFICER = 'c2' // CONTRACT §2

export default function CrewStart() {
  const { t, lang, setLang } = useT()
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState(false)

  async function choose(id) {
    setBusy(true)
    setError(false)
    try {
      await api.selectViewer(id) // the backend checks the id, as Settings does
      switchViewer(id)
    } catch {
      setError(true)
      setBusy(false)
    }
  }

  return (
    <main className="page crew-start">
      <div className="crew-start-head">
        <h1>{t('start.title')}</h1>
        <button type="button" className="rail-lang" onClick={() => setLang(lang === 'ko' ? 'en' : 'ko')}>
          {lang === 'ko' ? 'English' : '한국어'}
        </button>
      </div>
      <p className="muted">{t('start.hint')}</p>
      <div className="crew-start-grid">
        {CREW_IDS.map((id) => (
          <button key={id} type="button" className="btn-secondary crew-start-btn" disabled={busy} onClick={() => choose(id)}>
            <span className="crew-start-id">{id.toUpperCase()}</span>
            {id === MEDICAL_OFFICER && <span className="crew-tag">{t('crew.cmo')}</span>}
          </button>
        ))}
      </div>
      {error && <p role="alert" className="error">{t('common.error')}</p>}
    </main>
  )
}
