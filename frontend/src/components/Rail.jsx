// Rail.jsx — left rail: 6 screens + settings (spec §7), language toggle.
import { NavLink } from 'react-router-dom'
import { useT } from '../i18n/index.jsx'

const ITEMS = ['today', 'body', 'trends', 'log', 'procedures', 'crew']

export default function Rail() {
  const { t, lang, setLang } = useT()
  return (
    <nav className="rail">
      <div className="rail-brand">
        <span className="rail-mark" aria-hidden="true">
          <svg viewBox="0 0 24 24"><path d="M22 12h-4l-3 9L9 3l-3 9H2" /></svg>
        </span>
        {t('app.name')}
      </div>
      <ul className="rail-list">
        {ITEMS.map((key) => (
          <li key={key}>
            <NavLink to={`/${key}`} className="rail-link">{t(`nav.${key}`)}</NavLink>
          </li>
        ))}
      </ul>
      <div className="rail-bottom">
        <NavLink to="/settings" className="rail-link">{t('nav.settings')}</NavLink>
        <button type="button" className="rail-lang" onClick={() => setLang(lang === 'ko' ? 'en' : 'ko')}>
          {lang === 'ko' ? 'English' : '한국어'}
        </button>
      </div>
    </nav>
  )
}
