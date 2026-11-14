// Crew.jsx — medical officer (CMO) screen (spec §17): four crew cards from GET /crew + each /today,
// then the transmission queue to Earth (GET /tx) with receipt and link-simulation controls.
// Levels are the backend verdicts, drawn as they come. The route only opens for the CMO (App.jsx).
import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api, USE_FIXTURES } from '../api/client.js'
import { metricLabel } from '../api/contract.js'
import { useMission } from '../mission.jsx'
import { CURRENT_CREW } from '../session.js'
import { useT } from '../i18n/index.jsx'

const LEVEL_ICONS = { normal: '✔', advisory: '•', caution: '▲', warning: '✖', hold: '↻' }
const OFF_LEVELS = ['advisory', 'caution', 'warning'] // metrics a CMO should see on the card
const TX_PRIORITY_CLASS = { warning: 'lv-warning', caution: 'lv-caution', daily: 'neutral' }
const TX_STATUS_CLASS = { queued: 'lv-hold', sent: 'neutral', acked: 'lv-normal', missing: 'lv-warning' }
const NOT_SHARED = 'not_shared' // the crew member turned medical officer access off (or the backend said 403)

function formatZ(z) {
  if (z == null) return ''
  const r = Math.round(z * 10) / 10
  return `${r > 0 ? '+' : r < 0 ? '−' : '±'}${Math.abs(r).toFixed(1)}σ`
}

function badgeClass(level) {
  return level === 'advisory' ? 'neutral' : `lv-${level}`
}

// Reports the crew member shared with the medical officer (GET /crew shared_event_ids)
function SharedReports({ ids }) {
  const { t } = useT()
  return (
    <>
      <dt>{t('crew.shared')}</dt>
      <dd className="crew-chips">
        {ids.map((id) => <Link key={id} to={`/events/${id}`} className="cite">#{id}</Link>)}
        {ids.length === 0 && <span className="muted">{t('crew.none')}</span>}
      </dd>
    </>
  )
}

function CrewCard({ member, today }) {
  const { t, lang } = useT()
  const shared = member.shared_event_ids ?? []
  const head = (extra) => (
    <div className="panel-head">
      <h2>
        {member.name}
        {member.cmo && <span className="crew-tag">{t('crew.cmo')}</span>}
      </h2>
      {extra}
    </div>
  )
  if (today === undefined || today === null || today === NOT_SHARED) {
    const key = today === NOT_SHARED ? 'crew.not_shared' : today === null ? 'crew.card_error' : 'common.loading'
    return (
      <article className="panel crew-card">
        {head(<span className="muted small">{member.role}</span>)}
        <p className={`panel-empty ${today === null ? 'error' : 'muted'}`}>{t(key)}</p>
        {today === NOT_SHARED && shared.length > 0 && <dl className="crew-rows"><SharedReports ids={shared} /></dl>}
      </article>
    )
  }
  const level = today.status.level
  const off = today.metrics.filter((m) => OFF_LEVELS.includes(m.level))
  const holds = today.metrics.filter((m) => m.level === 'hold')
  const open = today.events.filter((e) => e.status !== 'closed')

  return (
    <article className={`panel crew-card lv-${level}`}>
      {head(<span className={`badge ${badgeClass(level)}`}>{LEVEL_ICONS[level]} {t(`level.${level}`)}</span>)}
      <dl className="crew-rows">
        <dt>{t('crew.role')}</dt>
        <dd>{member.role}</dd>
        <dt>{t('crew.status')}</dt>
        <dd>{today.status.text || t(`today.status.${level}`)}</dd>
        <dt>{t('crew.checkin')}</dt>
        <dd>
          {t(today.checkin.morning_done ? 'crew.checkin_done' : 'crew.checkin_pending')}
          <span className="muted"> · {t('crew.streak', { n: today.streak })}</span>
        </dd>
        <dt>{t('crew.off_metrics')}</dt>
        <dd className="crew-chips">
          {off.map((m) => (
            <span key={m.metric} className={`badge ${badgeClass(m.level)}`}>
              {LEVEL_ICONS[m.level]} {metricLabel(m.metric, lang)} {formatZ(m.z)}
            </span>
          ))}
          {off.length === 0 && holds.length === 0 && <span className="muted">{t('crew.none')}</span>}
          {holds.length > 0 && (
            <span className="muted">
              {LEVEL_ICONS.hold} {t('crew.hold_count', { n: holds.length })}
              {holds[0].hold_reason && ` · ${t(`hold.${holds[0].hold_reason}`)}`}
            </span>
          )}
        </dd>
        <dt>{t('crew.open_events')}</dt>
        <dd className="crew-chips">
          {open.map((e) => (
            <Link key={e.id} to={`/events/${e.id}`} className={`badge ${badgeClass(e.level)} crew-event`}>
              #{e.id} {t(`level.${e.level}`)}
            </Link>
          ))}
          {open.length === 0 && <span className="muted">{t('crew.none')}</span>}
        </dd>
        <SharedReports ids={shared} />
      </dl>
    </article>
  )
}

export default function Crew() {
  const { t, lang } = useT()
  const { mission, refresh } = useMission()
  const sol = mission?.clock.sol
  const [crew, setCrew] = useState(null)
  // Each /today result is tagged with the lang + sol it was fetched for; results from an earlier lang/sol are
  // never shown, so stale cards (or a failure hidden behind old data) cannot appear while reloading
  const loadKey = `${lang}:${sol}`
  const [loaded, setLoaded] = useState({ key: null, todays: {} }) // todays: id -> /today | NOT_SHARED | null (failed)
  const todays = loaded.key === loadKey ? loaded.todays : {}
  const [error, setError] = useState(false)
  const [queue, setQueue] = useState(null)
  const [queueError, setQueueError] = useState(false)
  const [busy, setBusy] = useState(false)
  const [note, setNote] = useState(null)
  const [amplitude, setAmplitude] = useState('3')
  const [comparison, setComparison] = useState(null)

  // Refetch when the demo clock moves to a new sol, like Today
  useEffect(() => {
    let alive = true
    const put = (id, value) =>
      setLoaded((prev) => ({ key: loadKey, todays: { ...(prev.key === loadKey ? prev.todays : {}), [id]: value } }))
    api.getCrew()
      .then((list) => {
        if (!alive) return
        setCrew(list)
        // One failing /today must not hide the other three cards
        list.forEach((c) => {
          if (c.cmo_access === false && c.id !== CURRENT_CREW) return put(c.id, NOT_SHARED)
          api.getToday(c.id, lang)
            .then((d) => alive && put(c.id, d))
            .catch((e) => alive && put(c.id, e.code === 'forbidden' ? NOT_SHARED : null))
        })
      })
      .catch(() => alive && setError(true))
    api.getTx()
      .then((q) => {
        if (!alive) return
        setQueue(q)
        setQueueError(false)
      })
      .catch(() => alive && setQueueError(true))
    return () => { alive = false }
  }, [lang, sol, loadKey])

  async function run(action) {
    setBusy(true)
    setNote(null)
    try {
      return await action()
    } catch {
      setNote(t('crew.tx.failed'))
      return null
    } finally {
      setBusy(false)
    }
  }

  // Queue actions return the whole queue
  async function runQueue(action) {
    const q = await run(action)
    if (q) {
      setQueue(q)
      setQueueError(false)
    }
    return q
  }

  async function sendNow() {
    const q = await runQueue(() => api.sendTx())
    // POST /tx/send only sends inside a comm window; anything still queued waits for the next one
    if (!q?.some((p) => p.status === 'queued')) return
    // Ask for the window now: the shared mission state may still hold the old one right after "next window"
    const latest = await api.getMission().catch(() => mission)
    setNote(t('crew.tx.no_window', { time: latest?.next_window ?? '–' }))
  }

  // Demo: move the clock to the next comm window (tomorrow if today's has passed)
  function nextWindow() {
    return run(async () => {
      const { clock, next_window } = await api.getMission()
      const nextSol = clock.sol + (next_window <= clock.time ? 1 : 0)
      await api.setDemoClock({ sol: nextSol, time: next_window })
      refresh()
      return true
    })
  }

  if (error) return <section className="page"><p className="error">{t('common.error')}</p></section>
  if (!crew) return <section className="page"><p className="muted">{t('common.loading')}</p></section>

  const viewer = crew.find((c) => c.id === CURRENT_CREW)
  const nameOf = (id) => crew.find((c) => c.id === id)?.name ?? id
  const waiting = queue?.some((p) => p.status === 'queued' || p.status === 'missing')
  const amplitudeOk = Number(amplitude) >= 1.1 && Number(amplitude) <= 10
  const backendOnly = busy || USE_FIXTURES // receipts, simulation and the demo clock need the real backend
  const percent = (rate) => (rate * 100).toFixed(3) + '%'

  return (
    <section className="page page-wide">
      <h1>{t('nav.crew')}</h1>
      <p className="status lv-normal">
        <span aria-hidden="true">✔</span>
        {t('crew.cmo_view', { name: viewer?.name ?? CURRENT_CREW })}
      </p>

      <div className="crew-grid">
        {crew.map((c) => <CrewCard key={c.id} member={c} today={todays[c.id]} />)}
      </div>

      <section className="panel">
        <div className="panel-head">
          <h2>{t('tx.title')}</h2>
          <span className="muted small">
            {t('crew.tx.window', { time: mission?.next_window ?? '–' })} · {t('topbar.delay')}{' '}
            {mission ? t('topbar.minutes', { n: mission.one_way_delay_min }) : '–'}
          </span>
        </div>
        {queueError && <p className="panel-empty error">{t('crew.tx.error')}</p>}
        {!queueError && queue?.length === 0 && <p className="panel-empty muted">{t('tx.empty')}</p>}
        {!queueError && !queue && <p className="panel-empty muted">{t('common.loading')}</p>}
        {queue?.length > 0 && (
          <table className="facts-table">
            <thead>
              <tr>
                <th className="right">{t('crew.tx.seq')}</th>
                <th>{t('crew.tx.crew')}</th>
                <th>{t('crew.tx.kind')}</th>
                <th>{t('crew.tx.priority')}</th>
                <th>{t('crew.tx.status')}</th>
                <th className="right">{t('crew.tx.attempts')}</th>
                <th><span className="sr-only">{t('crew.tx.actions')}</span></th>
              </tr>
            </thead>
            <tbody aria-live="polite">
              {queue.map((p) => (
                <tr key={p.seq}>
                  <td className="num right">{p.seq}</td>
                  <td>{p.crew ? nameOf(p.crew) : t('crew.tx.all')}</td>
                  <td>
                    {p.event_id != null
                      ? <Link to={`/events/${p.event_id}`} className="cite">{t('crew.tx.kind_event', { id: p.event_id })}</Link>
                      : t('crew.tx.kind_daily')}
                    {p.hash && <div className="num muted small">{p.hash.slice(0, 12)}</div>}
                  </td>
                  <td><span className={`badge ${TX_PRIORITY_CLASS[p.priority] ?? 'neutral'}`}>{t(`crew.tx.priority.${p.priority}`)}</span></td>
                  <td><span className={`badge ${TX_STATUS_CLASS[p.status] ?? 'neutral'}`}>{t(`tx.status.${p.status}`)}</span></td>
                  <td className="num right">{p.attempts}</td>
                  <td>
                    <div className="tx-actions">
                      {p.status === 'sent' && (
                        <button type="button" className="btn-secondary small" disabled={backendOnly}
                          onClick={() => runQueue(() => api.recordReceipt(p.seq, 'missing', p.attempts))}>{t('tx.missing')}</button>
                      )}
                      {(p.status === 'sent' || p.status === 'missing') && (
                        <button type="button" className="btn-secondary small" disabled={backendOnly}
                          onClick={() => runQueue(() => api.recordReceipt(p.seq, 'acked', p.attempts))}>{t('tx.ack')}</button>
                      )}
                      <button type="button" className="btn-secondary small" disabled={backendOnly || !amplitudeOk}
                        onClick={() => run(async () => setComparison(await api.simulateTransmission(p.seq, Number(amplitude))))}>
                        {t('tx.compare')}
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
        <div className="response">
          <button type="button" className="btn-primary" onClick={sendNow} disabled={busy || !waiting}>
            {t('tx.send')}
          </button>
          <button type="button" className="btn-secondary" onClick={() => runQueue(() => api.queueDaily())} disabled={busy}>
            {t('tx.queue_daily')}
          </button>
          <button type="button" className="btn-secondary" onClick={() => runQueue(() => api.getTx())} disabled={busy}>
            {t('tx.refresh')}
          </button>
          <button type="button" className="btn-secondary" onClick={nextWindow} disabled={backendOnly}>
            {t('tx.next_window')}
          </button>
          <label className="tx-amplitude">
            {t('tx.amplitude')}
            <input type="number" min="1.1" max="10" step="0.1" value={amplitude}
              onChange={(e) => setAmplitude(e.target.value)} />
          </label>
          {note && <span className="muted small" role="status">{note}</span>}
        </div>
        {USE_FIXTURES && <p className="panel-empty muted small">{t('tx.connect')}</p>}
        <p className="panel-empty muted small">{t('crew.tx.hint')}</p>
      </section>

      {comparison && (
        <section className="panel tx-results">
          <h2>{t('tx.comparison', { seq: comparison.seq, bits: comparison.packet_bits })}</h2>
          <table>
            <thead><tr>{['amplitude', 'bit_errors', 'success', 'energy'].map((key) => <th key={key} scope="col">{t(`tx.${key}`)}</th>)}</tr></thead>
            <tbody>{[comparison.narrow, comparison.wide].map((result) => (
              <tr className="num" key={result.amplitude}>
                <td>±{result.amplitude}</td>
                <td>{percent(result.bit_error_rate)}</td>
                <td>{result.successful_packets} / {comparison.trials}</td>
                <td>{result.relative_energy_per_bit.toFixed(1)}×</td>
              </tr>
            ))}</tbody>
          </table>
        </section>
      )}
    </section>
  )
}
