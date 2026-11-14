// App.jsx — left rail + screens. One screen = one route (spec §7).
import { Routes, Route, Navigate } from 'react-router-dom'
import Rail from './components/Rail.jsx'
import Footer from './components/Footer.jsx'
import Topbar from './components/Topbar.jsx'
import Today from './pages/Today.jsx'
import Placeholder from './pages/Placeholder.jsx'

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
          <Route path="/log" element={<Placeholder titleKey="nav.log" />} />
          <Route path="/procedures" element={<Placeholder titleKey="nav.procedures" />} />
          <Route path="/crew" element={<Placeholder titleKey="nav.crew" />} />
          <Route path="/settings" element={<Placeholder titleKey="nav.settings" />} />
          <Route path="/events/:id" element={<Placeholder titleKey="page.event" />} />
          <Route path="/warning" element={<Placeholder titleKey="page.warning" />} />
        </Routes>
      </main>
      <Footer />
    </div>
  )
}
