// Topbar.jsx — mission status strip: sol and time, environment, one-way delay to Earth, next comm window
import { useEffect, useState } from 'react'
import { api } from '../api/client.js'
import { useT } from '../i18n/index.jsx'

export default function Topbar() {
  const { t } = useT()
  const [m, setM] = useState(null)

  useEffect(() => {
    api.getMission().then(setM).catch(() => setM(null))
  }, [])

  if (!m) return <header className="topbar" />
  const items = [
    ['topbar.sol', `${m.clock.sol} · ${m.clock.time}`],
    ['topbar.env', t(`env.${m.environment}`)],
    ['topbar.delay', t('topbar.minutes', { n: m.one_way_delay_min })],
    ['topbar.window', m.next_window],
  ]
  return (
    <header className="topbar">
      <div className="topbar-items">
        {items.map(([label, value]) => (
          <div key={label} className="topbar-item">
            <span className="topbar-label">{t(label)}</span>
            <span className="topbar-value">{value}</span>
          </div>
        ))}
      </div>
    </header>
  )
}
