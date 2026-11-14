// Trends.jsx — one metric over 7/30/90 days (spec §7-3): daily readings against the 14-day baseline,
// the ±2σ/±3σ zones from the contract sensitivity, and the period's events. Verdicts stay with the backend:
// points are not coloured by level and nothing here is recomputed from z.
import { Link } from 'react-router-dom'
import { useEffect, useRef, useState } from 'react'
import Chart from 'chart.js/auto'
import { api } from '../api/client.js'
import { METRIC_KEYS, METRICS, metricLabel, formatMetric, formatTs, SENSITIVITY } from '../api/contract.js'
import { useT } from '../i18n/index.jsx'
import { CURRENT_CREW } from '../session.js'
import { useMission } from '../mission.jsx'

const PERIODS = [7, 30, 90]
// Only these sources get a label; anything else shows the value alone
const PREFLIGHT_SOURCE = { synthetic_scenario: 'trends.preflight_synthetic', manual: 'trends.preflight_manual' }
const DAY_MS = 86400000
const [CAUTION_SD, WARNING_SD] = SENSITIVITY.standard // e.g. 2 and 3

function dayKey(ts) {
  const key = typeof ts === 'string' ? ts.slice(0, 10) : ''
  return /^\d{4}-\d{2}-\d{2}$/.test(key) ? key : null
}

function dayNumber(key) {
  const [y, m, d] = key.split('-').map(Number)
  return Math.round(Date.UTC(y, m - 1, d) / DAY_MS)
}

function dayKeyFromNumber(n) {
  return new Date(n * DAY_MS).toISOString().slice(0, 10)
}

function formatDay(n, lang, withYear) {
  const options = withYear
    ? { year: 'numeric', month: 'short', day: 'numeric', timeZone: 'UTC' }
    : { month: 'short', day: 'numeric', timeZone: 'UTC' }
  try {
    return new Intl.DateTimeFormat(lang || undefined, options).format(new Date(n * DAY_MS))
  } catch {
    return dayKeyFromNumber(n)
  }
}

function isPositive(n) {
  return Number.isFinite(n) && n > 0
}

function normalize(data) {
  const points = (Array.isArray(data?.points) ? data.points : [])
    .map((p) => {
      const key = dayKey(p?.ts)
      const value = typeof p?.value === 'number' ? p.value : NaN
      return key && Number.isFinite(value) ? { ts: p.ts, key, day: dayNumber(key), value } : null
    })
    .filter(Boolean)
    .sort((a, b) => (a.ts < b.ts ? -1 : a.ts > b.ts ? 1 : 0))

  const events = (Array.isArray(data?.events) ? data.events : [])
    .map((e) => {
      const key = dayKey(e?.ts)
      return e && e.id != null ? { ...e, key, day: key ? dayNumber(key) : null } : null
    })
    .filter(Boolean)
    .sort((a, b) => String(a.ts).localeCompare(String(b.ts)))

  const mean = typeof data?.baseline?.mean === 'number' && Number.isFinite(data.baseline.mean)
    ? data.baseline.mean
    : null
  const sd = typeof data?.baseline?.sd === 'number' && isPositive(data.baseline.sd)
    ? data.baseline.sd
    : null

  // preflight is { value, source } | null; older backends and the fixtures leave it out
  const pv = data?.preflight?.value
  const preflight = typeof pv === 'number' && Number.isFinite(pv) ? { value: pv, source: data.preflight.source } : null

  return { points, events, baseline: { mean, sd }, preflight }
}

// Chart.js draws on a canvas, so it needs real colour values: read them from the design tokens
function tokens() {
  const css = getComputedStyle(document.documentElement)
  const v = (name) => css.getPropertyValue(name).trim()
  return {
    text: v('--text'), muted: v('--muted'), line: v('--line'), surface: v('--bezel'),
    accent: v('--accent'), caution: v('--caution'), warning: v('--warning'), mono: v('--mono'),
  }
}

// Baseline and the ±2σ/±3σ zones, drawn behind the data. A plugin instead of extra datasets keeps them
// out of the tooltip, so hovering only ever reports readings and events.
const zonesPlugin = {
  id: 'zones',
  beforeDatasetsDraw(chart, _args, o) {
    if (o.mean == null) return
    const { ctx, chartArea: a, scales: { y } } = chart
    const Y = (v) => Math.min(a.bottom, Math.max(a.top, y.getPixelForValue(v)))
    const hline = (value, color, dash) => {
      ctx.strokeStyle = color
      ctx.setLineDash(dash)
      ctx.beginPath()
      ctx.moveTo(a.left, Math.round(Y(value)) + 0.5)
      ctx.lineTo(a.right, Math.round(Y(value)) + 0.5)
      ctx.stroke()
    }
    ctx.save()
    ctx.lineWidth = 1
    if (o.sd != null) {
      const inner = CAUTION_SD * o.sd
      const outer = WARNING_SD * o.sd
      ctx.fillStyle = o.cautionFill // between ±2σ and ±3σ
      for (const s of [1, -1]) {
        const y1 = Y(o.mean + s * inner)
        const y2 = Y(o.mean + s * outer)
        ctx.fillRect(a.left, Math.min(y1, y2), a.right - a.left, Math.abs(y2 - y1))
      }
      ctx.fillStyle = o.warningFill // beyond ±3σ
      const top = Y(o.mean + outer)
      const bottom = Y(o.mean - outer)
      ctx.fillRect(a.left, a.top, a.right - a.left, top - a.top)
      ctx.fillRect(a.left, bottom, a.right - a.left, a.bottom - bottom)
      for (const s of [1, -1]) {
        hline(o.mean + s * inner, o.cautionLine, [4, 4])
        hline(o.mean + s * outer, o.warningLine, [4, 4])
      }
    }
    hline(o.mean, o.baselineLine, [6, 4])
    ctx.restore()
  },
}

function buildChartConfig({ points, events, baseline, preflight }, metric, lang, t) {
  const c = tokens()
  const firstDay = Math.min(...points.map(p => p.day), ...events.map(e => e.day ?? Infinity))
  const lastDay = Math.max(firstDay + 1, ...points.map(p => p.day), ...events.map(e => e.day ?? -Infinity))

  const byDay = new Map()
  for (const p of points) byDay.set(p.day, p.value)

  const series = []
  for (let d = firstDay; d <= lastDay; d += 1) {
    series.push({ x: d, y: byDay.has(d) ? byDay.get(d) : null })
  }

  const unit = METRICS?.[metric]?.unit
  const datasets = [
    {
      type: 'line',
      label: metricLabel(metric, lang),
      data: series,
      spanGaps: false, // a missing day stays a gap
      tension: 0,
      borderColor: c.text,
      borderWidth: 2,
      pointRadius: 4,
      pointHoverRadius: 6,
      pointBackgroundColor: c.text,
      pointBorderColor: c.surface, // 2px surface ring keeps points apart from the zone lines
      pointBorderWidth: 2,
      order: 1,
    },
  ]

  const markers = events
    .filter((e) => e.day != null && e.day >= firstDay && e.day <= lastDay && byDay.has(e.day))
    .map((e) => ({ x: e.day, y: byDay.get(e.day), title: e.title }))
  if (markers.length) {
    datasets.push({
      type: 'scatter',
      label: t('trends.events'),
      data: markers,
      pointStyle: 'triangle',
      pointRadius: 8,
      pointHoverRadius: 10,
      pointBackgroundColor: c.accent,
      pointBorderColor: c.surface,
      pointBorderWidth: 2,
      showLine: false,
      order: 0,
    })
  }

  // Preflight reference: a dataset, not part of the zones plugin, so it shows without a baseline and the y scale includes it
  if (preflight) {
    datasets.push({
      type: 'line',
      label: t('trends.preflight'),
      data: [{ x: firstDay, y: preflight.value }, { x: lastDay, y: preflight.value }],
      borderColor: c.accent,
      borderWidth: 2,
      borderDash: [2, 4],
      pointRadius: 0,
      pointHoverRadius: 0,
      tension: 0,
      order: 2,
    })
  }

  // Keep the ±3σ zone in view even when the readings sit close to the baseline
  const pad = baseline.sd != null ? (WARNING_SD + 0.5) * baseline.sd : null
  const tickFont = { family: c.mono, size: 11 }

  return {
    type: 'line',
    data: { datasets },
    plugins: [zonesPlugin],
    options: {
      responsive: true,
      maintainAspectRatio: false,
      animation: false,
      parsing: false,
      interaction: { mode: 'nearest', axis: 'x', intersect: false },
      scales: {
        x: {
          type: 'linear',
          min: firstDay - 0.3, // a little room so the first and last points and markers are not cut in half
          max: lastDay + 0.3,
          grid: { display: false },
          border: { color: c.line },
          ticks: {
            stepSize: 1,
            autoSkip: true,
            maxTicksLimit: 8,
            color: c.muted,
            font: tickFont,
            callback: (v) => (Number.isInteger(v) && v >= firstDay && v <= lastDay ? formatDay(v, lang, false) : ''),
          },
        },
        y: {
          suggestedMin: pad != null ? baseline.mean - pad : undefined,
          suggestedMax: pad != null ? baseline.mean + pad : undefined,
          grid: { color: c.line, lineWidth: 0.5 },
          border: { display: false },
          ticks: { color: c.muted, font: tickFont, maxTicksLimit: 6 },
          title: { display: Boolean(unit), text: unit || '', color: c.muted },
        },
      },
      plugins: {
        legend: { display: false }, // the HTML legend below names every mark and zone
        zones: {
          mean: baseline.mean,
          sd: baseline.sd,
          baselineLine: c.muted,
          cautionLine: `${c.caution}99`,
          warningLine: `${c.warning}99`,
          cautionFill: `${c.caution}1a`,
          warningFill: `${c.warning}12`,
        },
        tooltip: {
          backgroundColor: c.surface,
          borderColor: c.line,
          borderWidth: 1,
          titleColor: c.text,
          bodyColor: c.text,
          bodyFont: tickFont,
          displayColors: false,
          callbacks: {
            title: (items) => (items.length ? formatDay(items[0].parsed.x, lang, true) : ''),
            label: (item) => {
              const raw = item.raw || {}
              if (raw.title) return `▲ ${raw.title}`
              if (item.parsed.y == null) return null
              return `${item.dataset.label}: ${formatMetric(metric, item.parsed.y)} ${unit ?? ''}`
            },
          },
        },
      },
    },
  }
}

function TrendChart({ data, metric, lang, t }) {
  const canvasRef = useRef(null)

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return undefined
    const chart = new Chart(canvas, buildChartConfig(data, metric, lang, t))
    return () => chart.destroy()
  }, [data, metric, lang, t])

  return (
    <div className="trend-chart">
      <canvas ref={canvasRef} role="img" aria-label={t('trends.chart')} />
    </div>
  )
}

function Legend({ metric, lang, t, baseline, hasEvents, preflight }) {
  return (
    <ul className="trend-legend">
      <li><i className="sw sw-line" aria-hidden="true" />{metricLabel(metric, lang)}</li>
      {baseline.mean != null && <li><i className="sw sw-baseline" aria-hidden="true" />{t('trends.baseline')}</li>}
      {baseline.sd != null && (
        <>
          <li><i className="sw sw-caution" aria-hidden="true" />{t('trends.zone_caution', { a: CAUTION_SD, b: WARNING_SD })}</li>
          <li><i className="sw sw-warning" aria-hidden="true" />{t('trends.zone_warning', { b: WARNING_SD })}</li>
        </>
      )}
      {preflight && <li><i className="sw" aria-hidden="true" style={{ borderTop: '2px dashed var(--accent)' }} />{t('trends.preflight')}</li>}
      {hasEvents && <li><i className="sw sw-event" aria-hidden="true">▲</i>{t('trends.event_marker')}</li>}
    </ul>
  )
}

// Plain numbers for the period: no verdicts, no z (the backend owns those)
function Summary({ data, metric, t }) {
  const values = data.points.map((p) => p.value)
  const unit = METRICS[metric].unit
  const latest = data.points[data.points.length - 1]
  const avg = values.reduce((s, v) => s + v, 0) / values.length
  const cell = (v) => <><span className="num">{formatMetric(metric, v)}</span> <span className="muted small">{unit}</span></>
  return (
    <dl className="trend-summary">
      <div><dt>{t('trends.latest')} <span className="muted">· {latest.key}</span></dt><dd>{cell(latest.value)}</dd></div>
      <div><dt>{t('trends.avg')}</dt><dd>{cell(avg)}</dd></div>
      <div><dt>{t('trends.min')}</dt><dd>{cell(Math.min(...values))}</dd></div>
      <div><dt>{t('trends.max')}</dt><dd>{cell(Math.max(...values))}</dd></div>
      <div>
        <dt>{t('trends.baseline')}</dt>
        <dd>
          {data.baseline.mean == null ? <span className="muted">{t('trends.baseline_missing')}</span> : (
            <>
              {cell(data.baseline.mean)}
              {data.baseline.sd != null && <span className="muted small num"> σ {formatMetric(metric, data.baseline.sd)}</span>}
            </>
          )}
        </dd>
      </div>
      {data.preflight && (
        <div>
          <dt>{t('trends.preflight')}</dt>
          <dd>
            {cell(data.preflight.value)}
            {Object.hasOwn(PREFLIGHT_SOURCE, data.preflight.source) && (
              <span className="muted small"> · {t(PREFLIGHT_SOURCE[data.preflight.source])}</span>
            )}
          </dd>
        </div>
      )}
      <div><dt>{t('trends.count')}</dt><dd className="num">{values.length}</dd></div>
    </dl>
  )
}

export default function Trends() {
  const { t, lang } = useT()
  const { mission } = useMission()
  const sol = mission?.clock?.sol
  const [metric, setMetric] = useState(METRIC_KEYS[0])
  const [days, setDays] = useState(7)
  const [result, setResult] = useState(null)
  const key = `${metric}:${days}:${sol}`

  useEffect(() => {
    let active = true
    api.getTrends(CURRENT_CREW, metric, days)
      .then(data => { if (active) setResult({ key, data: normalize(data) }) })
      .catch(() => { if (active) setResult({ key, error: true }) })
    return () => { active = false }
  }, [metric, days, key])

  const current = result?.key === key ? result : null
  const data = current?.data
  const unit = METRICS[metric].unit

  return (
    <section className="page trend-page">
      <h1>{t('nav.trends')}</h1>
      <div className="trend-controls">
        <div className="seg" role="group" aria-label={t('trends.metric')}>
          {METRIC_KEYS.map(id => (
            <button key={id} type="button" aria-pressed={id === metric} onClick={() => setMetric(id)}>
              {metricLabel(id, lang)}
            </button>
          ))}
        </div>
        <div className="seg" role="group" aria-label={t('trends.period')}>
          {PERIODS.map(n => (
            <button key={n} type="button" aria-pressed={n === days} onClick={() => setDays(n)}>
              {t('trends.days', { n })}
            </button>
          ))}
        </div>
      </div>
      {!current && <p className="muted" role="status">{t('common.loading')}</p>}
      {current?.error && <p className="error" role="alert">{t('common.error')}</p>}
      {data && data.points.length === 0 && <p className="muted">{t('trends.empty')}</p>}
      {data?.points.length > 0 && (
        <section className="panel">
          <div className="panel-head">
            <h2>{metricLabel(metric, lang)} <span className="muted small">{unit}</span></h2>
            <span className="muted small num">{data.points[0].key} – {data.points[data.points.length - 1].key}</span>
          </div>
          <TrendChart data={data} metric={metric} lang={lang} t={t} />
          <Legend metric={metric} lang={lang} t={t} baseline={data.baseline} hasEvents={data.events.length > 0} preflight={data.preflight} />
          <Summary data={data} metric={metric} t={t} />
          <details className="trend-table">
            <summary>{t('trends.show_table', { n: data.points.length })}</summary>
            <table className="facts-table">
              <caption className="sr-only">{t('trends.readings')}</caption>
              <thead><tr><th scope="col">{t('trends.date')}</th><th scope="col" className="right">{t('trends.value')} ({unit})</th></tr></thead>
              <tbody>
                {data.points.map(point => (
                  <tr key={point.ts}><td className="num">{point.key}</td><td className="num right">{formatMetric(metric, point.value)}</td></tr>
                ))}
              </tbody>
            </table>
          </details>
        </section>
      )}
      {data?.events.length > 0 && (
        <section className="panel">
          <div className="panel-head"><h2>{t('trends.events')}</h2></div>
          <ul className="event-list">
            {data.events.map(event => (
              <li key={event.id}>
                <Link to={`/events/${event.id}`}>
                  <span className={`badge ${event.level === 'advisory' ? 'neutral' : `lv-${event.level}`}`}>{t(`level.${event.level}`)}</span>
                  <span>{event.title}</span>
                  <span className="num muted small">{formatTs(event.ts)}</span>
                </Link>
              </li>
            ))}
          </ul>
        </section>
      )}
    </section>
  )
}
