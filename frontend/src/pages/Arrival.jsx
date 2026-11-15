// Arrival.jsx — "arriving on Mars": what the trip is expected to do to the body by the day of arrival.
// Frontend only (no backend, no model): published NASA population figures from data/arrival.json, each with its
// source, and the team's knowledge paragraphs. It shows ranges for the average crew member, never a forecast or a
// verdict for one person. The only input is the length of the trip, which scales the per-month bone figure.
import { useState } from 'react'
import data from '../data/arrival.json'
import Cite from '../components/Cite.jsx'
import { useT } from '../i18n/index.jsx'

const SCALE_MAX = 40 // % loss at the right end of every bar, so the bars can be compared

const fmt = (n) => (Number.isInteger(n) ? String(n) : n.toFixed(1))

// [low, high] % loss by arrival for a system with numbers, or null for a note-only system
function rangeFor(s, months) {
  if (s.kind === 'per_month') return [s.low * months, s.high * months]
  if (s.kind === 'after_flight') return [s.low, s.high]
  return null
}

function LossBar({ low, high, floor }) {
  const { t } = useT()
  const pct = (v) => `${Math.min(100, (v / SCALE_MAX) * 100)}%`
  return (
    <div className="arrival-bar" role="img" aria-label={t('arrival.bar_label', { low: fmt(low), high: fmt(high) })}>
      <div className="arrival-bar-track">
        <span className="arrival-bar-range" style={{ left: pct(low), width: `calc(${pct(high)} - ${pct(low)})` }} />
        {floor != null && <span className="arrival-bar-floor" style={{ left: pct(100 - floor) }} title={t('arrival.floor', { n: floor })} />}
      </div>
      <div className="arrival-bar-scale muted small num"><span>0%</span><span>{SCALE_MAX}%</span></div>
    </div>
  )
}

function SystemCard({ s, months }) {
  const { t } = useT()
  const range = rangeFor(s, months)
  return (
    <article className="panel arrival-card">
      <div className="panel-head"><h2>{t(`arrival.${s.key}.title`)}</h2></div>
      <div className="arrival-body">
        {range ? (
          <>
            <p className="arrival-range">{t('arrival.range', { low: fmt(range[0]), high: fmt(range[1]) })}</p>
            <p className="muted small">{t(`arrival.${s.key}.basis`, { months })}</p>
            <LossBar low={range[0]} high={range[1]} floor={s.floor} />
            {s.floor != null && <p className="small">{t('arrival.floor', { n: s.floor })}</p>}
          </>
        ) : (
          <p className="arrival-range">{t(`arrival.${s.key}.what`)}</p>
        )}
        <p>{t(`arrival.${s.key}.help`)}</p>
        <div className="arrival-sources small">
          {s.sources.map((src) => (
            <a key={src.url} className="cite" href={src.url} target="_blank" rel="noreferrer">{src.label}</a>
          ))}
          {s.cites.map((c) => <Cite key={c} id={c} />)}
        </div>
      </div>
    </article>
  )
}

export default function Arrival() {
  const { t } = useT()
  const [months, setMonths] = useState(data.months.default)
  return (
    <section className="page page-wide arrival">
      <h1>{t('arrival.title')}</h1>
      <p className="notice lv-hold arrival-disclaimer">{t('arrival.disclaimer')}</p>

      <div className="panel arrival-trip">
        <label htmlFor="arrival-months">{t('arrival.months_label')}</label>
        <div className="arrival-trip-row">
          <span className="muted small">{t('arrival.depart')}</span>
          <input id="arrival-months" type="range" min={data.months.min} max={data.months.max} step="1"
            value={months} onChange={(e) => setMonths(Number(e.target.value))} />
          <span className="muted small">{t('arrival.arrive')}</span>
          <b className="num arrival-months">{t('arrival.months', { n: months })}</b>
        </div>
        <p className="muted small">{t('arrival.months_hint')}</p>
      </div>

      <div className="arrival-grid">
        {data.systems.map((s) => <SystemCard key={s.key} s={s} months={months} />)}
      </div>
      <p className="muted small">{t('arrival.footer')}</p>
    </section>
  )
}
