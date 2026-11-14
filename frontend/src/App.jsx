// App.jsx — left rail + screens. One screen = one route (spec §7).
import { Routes, Route, Navigate } from 'react-router-dom'
import Rail from './components/Rail.jsx'
import Footer from './components/Footer.jsx'
import Topbar from './components/Topbar.jsx'
import Today from './pages/Today.jsx'
import Crew from './pages/Crew.jsx'
import Placeholder from './pages/Placeholder.jsx'
import Log from './pages/Log.jsx'
import EventDetail from './pages/EventDetail.jsx'
import Settings from './pages/Settings.jsx'
import { CURRENT_CREW } from './session.js'

export default function App() {
  return (
    <div className="app">
      <Rail />
      <main className="main">
        <Topbar />
        <Routes>
          <Route path="/" element={<Navigate to="/today" replace />} />
          <Route path="/today" element={<Today />} />
          <Route path="/body" element={<Placeholder titleKey="nav.body" />} />
          <Route path="/trends" element={<Placeholder titleKey="nav.trends" />} />
          <Route path="/log" element={<Log />} />
          <Route path="/procedures" element={<Placeholder titleKey="nav.procedures" />} />
          <Route path="/crew" element={CURRENT_CREW === 'c2' ? <Crew /> : <Navigate to="/today" replace />} />
          <Route path="/settings" element={<Settings />} />
          <Route path="/events/:id" element={<EventDetail />} />
          <Route path="/warning" element={<Placeholder titleKey="page.warning" />} />
        </Routes>
      </main>
      <Footer />
    </div>
  )
}
