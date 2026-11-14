// Body.jsx — Body screen (spec §7-2): pixel body + region list + region detail.
// Region colour = the most serious backend level among that region's metrics (GET /crew/{id}/today).
// Nothing is recomputed from z; each metric row shows its own backend level.
import { lazy, Suspense, useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { api } from '../api/client.js'
import { METRICS, metricLabel, formatMetric } from '../api/contract.js'
// three.js is large: load the hologram only when the Body screen opens
const HoloBody = lazy(() => import('../components/HoloBody.jsx'))
import Cite from '../components/Cite.jsx'
import { REGIONS } from '../components/bodyRegions.js'
import { reportsByRegion } from '../components/bodyLocations.js'
import { useMission } from '../mission.jsx'
import { CURRENT_CREW } from '../session.js'
import { useT } from '../i18n/index.jsx'

const LEVEL_ICONS = { normal: '✔', advisory: '•', caution: '▲', warning: '✖', hold: '↻', none: '–' }
const RANK = { normal: 0, advisory: 1, caution: 2, warning: 3 }
const DOCS_RETRY_MS = 10000

// Most serious backend level among the region's metrics; a region whose metrics are all on hold is "hold"
function regionLevel(metrics) {
  const judged = metrics.filter((m) => m.level && m.level !== 'hold')
  if (judged.length === 0) return 'hold' // no readings, or all on hold: not judged, never shown as normal
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

function buildRegions(today) {
  const byMetric = Object.fromEntries((today.metrics ?? []).map((m) => [m.metric, m]))
  return REGIONS.map((r) => {
    const rows = r.metrics.map((k) => byMetric[k]).filter(Boolean)
    // a part nothing measures is "no sensor", not "hold" (hold means a reading exists but is not judged yet)
    return { ...r, rows, level: r.sensor === 'none' ? 'none' : regionLevel(rows) }
  })
}

// Worst level among the reports that point at each region (for the "!" marks)
function markLevels(reports) {
  const out = {}
  for (const [region, list] of Object.entries(reports)) {
    out[region] = list.reduce((worst, { event }) => ((RANK[event.level] ?? -1) > (RANK[worst] ?? -1) ? event.level : worst), null) ?? 'normal'
  }
  return out
}

// First off region (caution or worse), otherwise the heart
function defaultRegionId(regions) {
  return regions.find((r) => RANK[r.level] >= RANK.caution)?.id ?? 'heart'
}

export default function Body() {
  const { t, lang } = useT()
  const { mission } = useMission()
  const sol = mission?.clock?.sol
  const [result, setResult] = useState(null)
  const navigate = useNavigate()
  const [picked, setPicked] = useState(null)
  const [openable, setOpenable] = useState({}) // "doc#pN" -> true when that paragraph exists on this device
  const key = `${lang}:${sol}`

  useEffect(() => {
    let active = true
    api.getToday(CURRENT_CREW, lang)
      .then((today) => {
        if (!active) return
        setResult({ key, today })
        setPicked((p) => p ?? defaultRegionId(buildRegions(today))) // only the first time; a user's pick stays
      })
      .catch(() => active && setResult({ key, error: true }))
    return () => { active = false }
  }, [lang, sol, key])

  // Check each region's source against the documents the Procedures screen will show; link only real paragraphs
  // A failed request (network, server) is not the same as "no such paragraph": links stay hidden while unknown
  // and the check runs again every DOCS_RETRY_MS until it gets an answer.
  useEffect(() => {
    let active = true
    let timer = null
    async function check() {
      try {
        const { docs } = await api.getDocs()
        const found = {}
        for (const r of REGIONS) {
          if (!r.doc) continue
          const [docId, para] = r.doc.split('#p')
          const has = (doc) => !!doc?.paragraphs?.some((p) => String(p.n) === para)
          const listed = docs.find((d) => d.id === docId)
          if (has(listed) || !listed) { found[r.doc] = has(listed); continue }
          // The list may carry no paragraphs, an empty array, or only some: ask for the full document.
          // Only "document not found" means no link; any other error goes to the retry below.
          const doc = await api.getDoc(docId).catch((e) => {
            if (e?.code === 'doc_not_found') return null
            throw e
          })
          found[r.doc] = has(doc)
        }
        if (active) setOpenable(found)
      } catch {
        if (active) timer = setTimeout(check, DOCS_RETRY_MS)
      }
    }
    check()
    return () => { active = false; clearTimeout(timer) }
  }, [])

  const current = result?.key === key ? result : null
  if (current?.error) return <section className="page"><p className="error">{t('common.error')}</p></section>
  if (!current) return <section className="page"><p className="muted">{t('common.loading')}</p></section>

  const today = current.today
  const regions = buildRegions(today) // always all regions, with or without readings
  const levels = Object.fromEntries(regions.map((r) => [r.id, r.level]))
  const reports = reportsByRegion(today.events) // where today's symptom reports say it hurts
  const marks = markLevels(reports)
  const selectedId = regions.some((r) => r.id === picked) ? picked : defaultRegionId(regions)
  // the selected region stays selected even when it has no readings; its table shows an empty state
  const sel = regions.find((r) => r.id === selectedId)
  // Today's events for the region, each with why it is listed:
  // - "reading": one of the region's readings was at caution or warning at report time (advisory is not linked)
  // - "report": the report says it hurts here (from the backend's locations, or found in the report text)
  const related = new Map()
  for (const e of today.events ?? []) {
    if ((e.findings ?? []).some((f) => sel.metrics.includes(f.metric) && RANK[f.level] >= RANK.caution)) {
      related.set(e.id, { event: e, reading: true })
    }
  }
  for (const r of reports[sel.id] ?? []) {
    related.set(r.event.id, { ...related.get(r.event.id), event: r.event, report: r })
  }
  const relatedList = [...related.values()].sort((a, b) => b.event.id - a.event.id)
  const counts = { caution: regions.filter((r) => r.level === 'caution').length, warning: regions.filter((r) => r.level === 'warning').length }

  // "Record a symptom here": open the Log with the part already written, the crew member adds how it feels
  function recordHere() {
    navigate('/log', { state: { prefill: t(`body.prefill.${sel.id}`) } })
  }

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
                  {marks[r.id] && (
                    <span className={`body-mark ${badgeClass(marks[r.id])}`} title={t('body.legend.reported')}>
                      <span aria-hidden="true">!</span><span className="sr-only">{t('body.legend.reported')}</span>
                    </span>
                  )}
                </button>
              </li>
            ))}
          </ul>
          <ul className="body-legend">
            <li><i className="sw cell-normal" aria-hidden="true" />{t('body.legend.normal')}</li>
            <li><i className="sw cell-caution" aria-hidden="true" />{t('body.legend.caution')}</li>
            <li><i className="sw cell-warning" aria-hidden="true" />{t('body.legend.warning')}</li>
            <li><i className="sw cell-hold" aria-hidden="true" />{t('body.legend.hold')}</li>
            <li><i className="sw cell-base" aria-hidden="true" />{t('body.legend.no_sensor')}</li>
            <li><span className="body-mark" aria-hidden="true">!</span>{t('body.legend.reported')}</li>
          </ul>
        </section>

        <section className="panel body-figure-panel">
          <div className="panel-head">
            <h2>{t('body.figure')}</h2>
            <span className="muted small">{t('body.figure_hint')}</span>
          </div>
          <Suspense fallback={<p className="panel-empty muted">{t('common.loading')}</p>}>
            <HoloBody levels={levels} selected={selectedId} marks={marks} label={t('body.figure_label')}
              callouts={regions.map((r) => ({ id: r.id, text: t(`body.region.${r.id}`), level: r.level, reported: !!marks[r.id] }))}
              texts={{ rotate: t('body.ctrl.rotate'), labels: t('body.ctrl.labels'), reset: t('body.ctrl.reset') }}
              sideLabels={{ left: t('body.side.left'), right: t('body.side.right') }}
              onSelect={setPicked} unavailableText={t('body.figure_unavailable')} />
          </Suspense>
        </section>

        <section className={`panel body-detail lv-${sel.level}`}>
          <div className="panel-head">
            <h2>{t(`body.region.${sel.id}`)}</h2>
            <span className={`badge ${badgeClass(sel.level)}`}>{LEVEL_ICONS[sel.level]} {t(`level.${sel.level}`)}</span>
          </div>
          {sel.sensor === 'none' && <p className="panel-empty muted">{t('body.sensor.none')}</p>}
          {sel.sensor === 'whole' && <p className="panel-empty muted small">{t('body.sensor.whole')}</p>}
          {sel.sensor !== 'none' && <table className="facts-table">
            <thead>
              <tr>
                <th>{t('event.col.metric')}</th>
                <th className="right">{t('event.col.value')}</th>
                <th className="right">{t('event.col.baseline')}</th>
                <th className="right">σ</th>
              </tr>
            </thead>
            <tbody>
              {sel.rows.length === 0 && (
                <tr><td colSpan={4} className="muted">{t('body.no_rows')}</td></tr>
              )}
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
          </table>}
          <div className="body-note">
            <p>{t(`body.note.${sel.id}`)}</p>
            {sel.doc && openable[sel.doc] && <p className="muted small">{t('body.source')} <Cite id={sel.doc} /></p>}
          </div>
          <div className="panel-head body-subhead">
            <h2>{t('body.related')}</h2>
            <span className="muted small">{relatedList.length}</span>
          </div>
          {relatedList.length === 0 && <p className="panel-empty muted">{t('body.none')}</p>}
          <ul className="event-list">
            {relatedList.map(({ event: e, reading, report }) => (
              <li key={e.id}>
                <Link to={`/events/${e.id}`}>
                  <span className={`badge ${badgeClass(e.level)}`}>{t(`level.${e.level}`)}</span>
                  <span className="body-event">
                    <span>{e.symptom_text ? `“${e.symptom_text}”` : e.title}</span>
                    <span className="muted small">
                      {[
                        reading && t('body.why.reading'),
                        report && t(report.source === 'backend' ? 'body.why.report' : 'body.why.report_text'),
                        report && !report.sideStated && t('body.why.no_side'),
                      ].filter(Boolean).join(' · ')}
                    </span>
                  </span>
                  <span className="num muted small">#{e.id}</span>
                </Link>
              </li>
            ))}
          </ul>
          <div className="response">
            <button type="button" className="btn-secondary" onClick={recordHere}>{t('body.record_here')}</button>
          </div>
        </section>
      </div>
    </section>
  )
}
