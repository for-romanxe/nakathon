import { useEffect, useState } from 'react'
import { api } from '../api/client.js'
import { useT } from '../i18n/index.jsx'
import { CREW_IDS, CURRENT_CREW, switchViewer } from '../session.js'
import PreflightForm from './PreflightForm.jsx'
import DemoClock from '../components/DemoClock.jsx'

export default function Settings({ loginRequired }) {
  const { t } = useT()
  const [access, setAccess] = useState(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState(false)

  useEffect(() => {
    api.getSettings().then(settings => setAccess(settings.cmo_access)).catch(() => setError(true))
  }, [])

  async function update(action) {
    setBusy(true)
    setError(false)
    try {
      await action()
    } catch {
      setError(true)
    } finally {
      setBusy(false)
    }
  }

  return (
    <section className="page">
      <h1>{t('nav.settings')}</h1>
      {loginRequired ? (
        <button type="button" className="btn-secondary" disabled={busy} onClick={() => update(async () => {
          await api.logout()
          window.location.reload()
        })}>{t('login.logout')}</button>
      ) : <label>
        {t('settings.viewer')}{' '}
        <select value={CURRENT_CREW} disabled={busy} onChange={event => {
          const id = event.target.value
          update(async () => switchViewer((await api.selectViewer(id)).id))
        }}>
          {CREW_IDS.map(id => <option key={id} value={id}>{id.toUpperCase()}</option>)}
        </select>
      </label>}
      <label>
        <input type="checkbox" checked={access === true} disabled={busy || access === null} onChange={event => {
          const cmo_access = event.target.checked
          update(async () => setAccess((await api.setSettings({ cmo_access })).cmo_access))
        }} /> {t('settings.cmo_access')}
      </label>
      {error && <p role="alert" className="error">{t('common.error')}</p>}
      <PreflightForm />
      <DemoClock />
    </section>
  )
}
