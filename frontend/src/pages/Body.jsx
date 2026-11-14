// Body.jsx — Body screen (spec §7-2): pixel body + region list + region detail.
// Region colour = the most serious backend level among that region's metrics (GET /crew/{id}/today).
// Nothing is recomputed from z; each metric row shows its own backend level.
import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api/client.js'
import { METRICS, metricLabel, formatMetric } from '../api/contract.js'
import BodyFigure from '../components/BodyFigure.jsx'
import Cite from '../components/Cite.jsx'
import { REGIONS } from '../components/bodyRegions.js'
import { useMission } from '../mission.jsx'
import { CURRENT_CREW } from '../session.js'
import { useT } from '../i18n/index.jsx'

const LEVEL_ICONS = { normal: '✔', advisory: '•', caution: '▲', warning: '✖', hold: '↻' }
const RANK = { normal: 0, advisory: 1, caution: 2, warning: 3 }

// Most serious backend level among the region's metrics; a region whose metrics are all on hold is "hold"
function regionLevel(metrics) {
  const judged = metrics.filter((m) => m.level && m.level !== 'hold')
  if (judged.length === 0) return metrics.length ? 'hold' : 'normal'
  return judged.reduce((worst, m) => ((RANK[m.level] ?? 0) > RANK[worst] ? m.level : worst), 'normal')
}

function formatZ(z) {
  if (z == null) return '–'
  const r = Math.round(z * 10) / 10
  return `${r > 0 ? '+' : r < 0 ? '−' : '±'}${Math.abs(r).toFixed(1)}σ`
}

function badgeClass(level) {
  return level === 'advisory' ? 'neutral' : `lv-${level}`
}

export default function Body() {
  const { t, lang } = useT()
  const { mission } = useMission()
  const sol = mission?.clock?.sol
  const [result, setResult] = useState(null)
  const [picked, setPicked] = useState(null)
  const key = `${lang}:${sol}`

  useEffect(() => {
    let active = true
    api.getToday(CURRENT_CREW, lang)
      .then((today) => active && setResult({ key, today }))
      .catch(() => active && setResult({ key, error: true }))
    return () => { active = false }
  }, [lang, sol, key])

  const current = result?.key === key ? result : null
  if (current?.error) return <section className="page"><p className="error">{t('common.error')}</p></section>
  if (!current) return <section className="page"><p className="muted">{t('common.loading')}</p></section>

  const today = current.today
  const byMetric = Object.fromEntries((today.metrics ?? []).map((m) => [m.metric, m]))
  const regions = REGIONS.map((r) => {
    const metrics = r.metrics.map((k) => byMetric[k]).filter(Boolean)
    return { ...r, rows: metrics, level: regionLevel(metrics) }
  })
  const levels = Object.fromEntries(regions.map((r) => [r.id, r.level]))
  // Open the first off region by default, otherwise the heart
  const selectedId = picked ?? regions.find((r) => RANK[r.level] >= RANK.caution)?.id ?? 'heart'
  const sel = regions.find((r) => r.id === selectedId)
  const related = (today.events ?? []).filter((e) => (e.findings ?? []).some((f) => sel.metrics.includes(f.metric)))
  const counts = { caution: regions.filter((r) => r.level === 'caution').length, warning: regions.filter((r) => r.level === 'warning').length }

  return (
    <section className="page body-page">
      <h1>{t('nav.body')}</h1>
      <div className="body-layout">
        <section className="panel body-list">
          <div className="panel-head">
            <h2>{t('body.regions')}</h2>
            <span className="muted small">{t('body.counts', counts)}</span>
          </div>
          <ul>
            {regions.map((r) => (
              <li key={r.id}>
                <button type="button" className={r.id === selectedId ? 'on' : ''} aria-pressed={r.id === selectedId}
                  onClick={() => setPicked(r.id)}>
                  <span className={`badge ${badgeClass(r.level)}`}>{LEVEL_ICONS[r.level]} {t(`level.${r.level}`)}</span>
                  <span>{t(`body.region.${r.id}`)}</span>
                </button>
              </li>
            ))}
          </ul>
          <ul className="body-legend">
            <li><i className="sw cell-normal" aria-hidden="true" />{t('body.legend.normal')}</li>
            <li><i className="sw cell-caution" aria-hidden="true" />{t('body.legend.caution')}</li>
            <li><i className="sw cell-warning" aria-hidden="true" />{t('body.legend.warning')}</li>
            <li><i className="sw cell-hold" aria-hidden="true" />{t('body.legend.hold')}</li>
          </ul>
        </section>

        <section className="panel body-figure-panel">
          <div className="panel-head">
            <h2>{t('body.figure')}</h2>
            <span className="muted small">{t('body.figure_hint')}</span>
          </div>
          <BodyFigure levels={levels} selected={selectedId} onSelect={setPicked} label={t('body.figure_label')} />
        </section>

        <section className={`panel body-detail lv-${sel.level}`}>
          <div className="panel-head">
            <h2>{t(`body.region.${sel.id}`)}</h2>
            <span className={`badge ${badgeClass(sel.level)}`}>{LEVEL_ICONS[sel.level]} {t(`level.${sel.level}`)}</span>
          </div>
          <table className="facts-table">
            <thead>
              <tr>
                <th>{t('event.col.metric')}</th>
                <th className="right">{t('event.col.value')}</th>
                <th className="right">{t('event.col.baseline')}</th>
                <th className="right">σ</th>
              </tr>
            </thead>
            <tbody>
              {sel.rows.map((m) => (
                <tr key={m.metric} className={m.level === 'caution' || m.level === 'warning' ? `lv-${m.level} off` : ''}>
                  <td>
                    {metricLabel(m.metric, lang)}
                    {m.level === 'hold' && m.hold_reason && <div className="muted small">{t(`hold.${m.hold_reason}`)}</div>}
                  </td>
                  <td className="num right">{formatMetric(m.metric, m.value)} <span className="muted small">{METRICS[m.metric]?.unit}</span></td>
                  <td className="num right">{formatMetric(m.metric, m.baseline)}</td>
                  <td className="right">
                    <span className={`badge ${badgeClass(m.level)}`}>{LEVEL_ICONS[m.level]} {m.level === 'hold' ? t('level.hold') : formatZ(m.z)}</span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          <div className="body-note">
            <p>{t(`body.note.${sel.id}`)}</p>
            {sel.doc && <p className="muted small">{t('body.source')} <Cite id={sel.doc} /></p>}
          </div>
          <div className="panel-head body-subhead">
            <h2>{t('body.related')}</h2>
            <span className="muted small">{related.length}</span>
          </div>
          {related.length === 0 && <p className="panel-empty muted">{t('body.none')}</p>}
          <ul className="event-list">
            {related.map((e) => (
              <li key={e.id}>
                <Link to={`/events/${e.id}`}>
                  <span className={`badge ${badgeClass(e.level)}`}>{t(`level.${e.level}`)}</span>
                  <span>{e.title}</span>
                  <span className="num muted small">#{e.id}</span>
                </Link>
              </li>
            ))}
          </ul>
        </section>
      </div>
    </section>
  )
}
