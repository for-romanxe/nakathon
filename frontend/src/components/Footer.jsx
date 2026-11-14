// Footer.jsx — on every screen: not a medical device, synthetic data, fictional crew and docs (spec §5).
import { useT } from '../i18n/index.jsx'

export default function Footer() {
  const { t } = useT()
  return <footer className="footer">{t('footer.notice')}</footer>
}
