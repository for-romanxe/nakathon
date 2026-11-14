// Placeholder.jsx — stand-in for screens not built yet.
import { useT } from '../i18n/index.jsx'

export default function Placeholder({ titleKey }) {
  const { t } = useT()
  return (
    <section className="page">
      <h1>{t(titleKey)}</h1>
      <p className="muted">{t('placeholder.todo')}</p>
    </section>
  )
}
