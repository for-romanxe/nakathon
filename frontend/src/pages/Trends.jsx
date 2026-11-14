import { Link } from 'react-router-dom'
import { useEffect, useRef, useState } from 'react'
import Chart from 'chart.js/auto'
import { api } from '../api/client.js'
import { METRIC_KEYS, METRICS, metricLabel, formatMetric, formatTs, SENSITIVITY } from '../api/contract.js'
import { useT } from '../i18n/index.jsx'
import { CURRENT_CREW } from '../session.js'
import { useMission } from '../mission.jsx'

const PERIODS = [7, 30, 90]
const DAY_MS = 86400000

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

  return { points, events, baseline: { mean, sd } }
}

function buildChartConfig({ points, events, baseline }, metric, lang, t) {
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
      spanGaps: false,
      tension: 0,
      pointRadius: 3,
      borderWidth: 2,
    },
  ]

  if (baseline.mean != null) {
    const flat = (y) => [{ x: firstDay, y }, { x: lastDay, y }]
    datasets.push({
      type: 'line',
      label: t('trends.baseline'),
      data: flat(baseline.mean),
      pointRadius: 0,
      borderWidth: 1,
      borderDash: [6, 4],
    })
    if (baseline.sd != null) {
      for (const k of SENSITIVITY.standard) {
        for (const sign of [1, -1]) {
          datasets.push({
            type: 'line',
            label: `${sign > 0 ? '+' : '−'}${k}σ`,
            data: flat(baseline.mean + sign * k * baseline.sd),
            pointRadius: 0,
            borderWidth: 1,
            borderDash: [2, 4],
          })
        }
      }
    }
  }

  const markers = events
    .filter((e) => e.day != null && e.day >= firstDay && e.day <= lastDay && byDay.has(e.day))
    .map((e) => ({ x: e.day, y: byDay.get(e.day), title: e.title }))
  if (markers.length) {
    datasets.push({
      type: 'scatter',
      label: t('trends.events'),
      data: markers,
      pointStyle: 'triangle',
      pointRadius: 7,
      showLine: false,
    })
  }

  return {
    type: 'line',
    data: { datasets },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      animation: false,
      parsing: false,
      scales: {
        x: {
          type: 'linear',
          min: firstDay,
          max: lastDay,
          ticks: {
            stepSize: 1,
            callback: (v) => (Number.isInteger(v) ? formatDay(v, lang, false) : ''),
          },
        },
        y: {
          title: { display: Boolean(unit), text: unit || '' },
        },
      },
      plugins: {
        tooltip: {
          callbacks: {
            title: (items) => (items.length ? formatDay(items[0].parsed.x, lang, true) : ''),
            label: (item) => {
              const raw = item.raw || {}
              if (raw.title) return String(raw.title)
              return `${item.dataset.label}: ${formatMetric(metric, item.parsed.y)}`
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
    <div style={{ position: 'relative', height: 320 }}>
      <canvas ref={canvasRef} role="img" aria-label={t('trends.chart')} />
    </div>
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
    <section className="page">
      <h1>{t('nav.trends')}</h1>
      <div className="tx-actions">
        <label>{t('trends.metric')}{' '}
          <select value={metric} onChange={event => setMetric(event.target.value)}>
            {METRIC_KEYS.map(id => <option key={id} value={id}>{metricLabel(id, lang)}</option>)}
          </select>
        </label>
        <label>{t('trends.period')}{' '}
          <select value={days} onChange={event => setDays(Number(event.target.value))}>
            {PERIODS.map(n => <option key={n} value={n}>{t('trends.days', { n })}</option>)}
          </select>
        </label>
      </div>
      {!current && <p role="status">{t('common.loading')}</p>}
      {current?.error && <p role="alert">{t('common.error')}</p>}
      {data && data.points.length === 0 && <p>{t('trends.empty')}</p>}
      {data?.points.length > 0 && (
        <section className="panel">
          <TrendChart data={data} metric={metric} lang={lang} t={t} />
          <p>{data.baseline.mean == null ? t('trends.baseline_missing') : (
            <>{t('trends.baseline')} · {formatMetric(metric, data.baseline.mean)} {unit}</>
          )}</p>
          <table className="facts-table">
            <caption>{t('trends.readings')}</caption>
            <thead><tr><th scope="col">{t('trends.date')}</th><th scope="col">{t('trends.value')} ({unit})</th></tr></thead>
            <tbody>
              {data.points.map(point => (
                <tr key={point.ts}><td>{point.key}</td><td>{formatMetric(metric, point.value)}</td></tr>
              ))}
            </tbody>
          </table>
        </section>
      )}
      {data?.events.length > 0 && (
        <section className="panel">
          <h2>{t('trends.events')}</h2>
          <ul>
            {data.events.map(event => (
              <li key={event.id}><Link to={`/events/${event.id}`}>{formatTs(event.ts)} · {event.title}</Link></li>
            ))}
          </ul>
        </section>
      )}
    </section>
  )
}
