// App.jsx — left rail + screens. One screen = one route (spec §7).
import { Routes, Route, Navigate } from 'react-router-dom'
import { lazy, Suspense, useEffect, useState } from 'react'
import Rail from './components/Rail.jsx'
import Footer from './components/Footer.jsx'
import Topbar from './components/Topbar.jsx'
import Today from './pages/Today.jsx'
import Crew from './pages/Crew.jsx'
import Placeholder from './pages/Placeholder.jsx'
import Log from './pages/Log.jsx'
import EventDetail from './pages/EventDetail.jsx'
import Warning from './pages/Warning.jsx'
import Procedures from './pages/Procedures.jsx'
import Settings from './pages/Settings.jsx'
import { CURRENT_CREW, setSignedInCrew, CREW_IDS } from './session.js'
import { api } from './api/client.js'
import { useT } from './i18n/index.jsx'

const Trends = lazy(() => import('./pages/Trends.jsx'))

export default function App() {
  const { t } = useT()
  const [session, setSession] = useState(null)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  useEffect(() => {
    let active = true
    api.getSession().then(result => {
      if (!active) return
      if (result.crew_id) setSignedInCrew(result.crew_id)
      setSession(result)
    }).catch(() => { if (active) setError('common.error') })
    return () => { active = false }
  }, [])

  async function signIn(event) {
    event.preventDefault()
    const form = new FormData(event.currentTarget)
    setBusy(true)
    setError('')
    try {
      await api.login(form.get('crew'), form.get('code'))
      window.location.reload()
    } catch (failure) {
      setError(failure.code === 'unauthorized' ? 'login.invalid' : 'common.error')
    } finally {
      setBusy(false)
    }
  }

  if (!session) return <main className="page">{t(error || 'common.loading')}</main>
  if (session.login_required && !session.crew_id) {
    return (
      <main className="page">
        <h1>{t('login.title')}</h1>
        <form className="panel checkin-form" onSubmit={signIn}>
          <label>{t('login.crew')} <select name="crew">
            {CREW_IDS.map(id => <option key={id} value={id}>{id.toUpperCase()}</option>)}
          </select></label>
          <label>{t('login.code')} <input name="code" type="password" autoComplete="current-password" required maxLength={256} /></label>
          <button className="btn-primary" disabled={busy}>{t('login.title')}</button>
          {error && <p role="alert">{t(error)}</p>}
        </form>
      </main>
    )
  }
  return (
    <div className="app">
      <Rail />
      <main className="main">
        <Topbar />
        <Routes>
          <Route path="/" element={<Navigate to="/today" replace />} />
          <Route path="/today" element={<Today />} />
          <Route path="/body" element={<Placeholder titleKey="nav.body" />} />
          <Route path="/trends" element={<Suspense fallback={<p role="status">{t('common.loading')}</p>}><Trends /></Suspense>} />
          <Route path="/log" element={<Log />} />
          <Route path="/procedures" element={<Procedures />} />
          <Route path="/crew" element={CURRENT_CREW === 'c2' ? <Crew /> : <Navigate to="/today" replace />} />
          <Route path="/settings" element={<Settings loginRequired={session.login_required} />} />
          <Route path="/events/:id" element={<EventDetail />} />
          <Route path="/warning" element={<Warning />} />
        </Routes>
      </main>
      <Footer />
    </div>
  )
}
