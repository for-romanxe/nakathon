// ProcedureConsent.jsx — /events/:id/procedure: where a designated crew member (C1, C3) opens another crew
// member's warning procedure and gives consent from their own session (#47 FE-03). Reached from Today's
// consent request. It shows only the procedure, not the patient's records.
import { Link, useParams } from 'react-router-dom'
import ProcedureSteps from '../components/ProcedureSteps.jsx'
import { useT } from '../i18n/index.jsx'

export default function ProcedureConsent() {
  const { t } = useT()
  const { id } = useParams()
  return (
    <section className="page">
      <Link className="back-link" to="/today">{t('proc.consent.back')}</Link>
      <h1>{t('proc.consent.title', { id })}</h1>
      <section className="panel procedure-panel">
        <ProcedureSteps eventId={id} fallback={<p className="panel-empty muted">{t('proc.consent.none')}</p>} fallbackWhenHeld={false} />
      </section>
    </section>
  )
}
