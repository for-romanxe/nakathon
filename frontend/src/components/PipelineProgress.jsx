// PipelineProgress.jsx — shows the fixed pipeline stages as they arrive (CONTRACT §4).
// Stages the event did not pass through (e.g. the model is skipped on a warning) are simply not listed.
import { useT } from '../i18n/index.jsx'

export default function PipelineProgress({ stages, final }) {
  const { t } = useT()
  return (
    <div className="pipeline" aria-live="polite">
      <ol>
        {stages.map((s, i) => {
          const last = i === stages.length - 1 && !final
          return (
            <li key={`${s}-${i}`} className={last ? 'running' : 'done'}>
              <span aria-hidden="true">{last ? '◌' : '✔'}</span> {t(`stage.${s}`)}
            </li>
          )
        })}
        {!final && stages.length === 0 && <li className="running">◌ {t('stage.waiting')}</li>}
        {final === 'unavailable' && <li className="muted">{t('stage.unavailable')}</li>}
        {final === 'interrupted' && <li className="stopped">✖ {t('stage.interrupted')}</li>}
      </ol>
    </div>
  )
}
