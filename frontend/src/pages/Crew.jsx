// Crew.jsx — medical officer (CMO) screen (spec §17): four crew cards from GET /crew + each /today,
// then the transmission queue to Earth (GET /tx). Levels are the backend verdicts, drawn as they come.
import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api/client.js'
import { metricLabel } from '../api/contract.js'
import { useMission } from '../mission.jsx'
import { CURRENT_CREW } from '../session.js'
import { useT } from '../i18n/index.jsx'

const LEVEL_ICONS = { normal: '✔', advisory: '•', caution: '▲', warning: '✖', hold: '↻' }
const OFF_LEVELS = ['advisory', 'caution', 'warning'] // metrics a CMO should see on the card
const TX_PRIORITY_CLASS = { warning: 'lv-warning', caution: 'lv-caution', daily: 'neutral' }
const TX_STATUS_CLASS = { queued: 'lv-hold', sent: 'neutral', acked: 'lv-normal', missing: 'lv-warning' }

function formatZ(z) {
  if (z == null) return ''
  const r = Math.round(z * 10) / 10
  return `${r > 0 ? '+' : r < 0 ? '−' : '±'}${Math.abs(r).toFixed(1)}σ`
}

function badgeClass(level) {
  return level === 'advisory' ? 'neutral' : `lv-${level}`
}

function CrewCard({ member, today, failed }) {
  const { t, lang } = useT()
  if (failed || !today) {
    return (
      <article className="panel crew-card">
        <div className="panel-head"><h2>{member.name}</h2><span className="muted small">{member.role}</span></div>
        <p className={`panel-empty ${failed ? 'error' : 'muted'}`}>{t(failed ? 'crew.card_error' : 'common.loading')}</p>
      </article>
    )
  }
  const level = today.status.level
  const off = today.metrics.filter((m) => OFF_LEVELS.includes(m.level))
  const holds = today.metrics.filter((m) => m.level === 'hold')
  const open = today.events.filter((e) => e.status !== 'closed')

  return (
    <article className={`panel crew-card lv-${level}`}>
      <div className="panel-head">
        <h2>
          {member.name}
          {member.cmo && <span className="crew-tag">{t('crew.cmo')}</span>}
        </h2>
        <span className={`badge ${badgeClass(level)}`}>{LEVEL_ICONS[level]} {t(`level.${level}`)}</span>
      </div>
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
      </dl>
    </article>
  )
}

export default function Crew() {
  const { t, lang } = useT()
  const { mission } = useMission()
  const sol = mission?.clock.sol
  const [crew, setCrew] = useState(null)
  const [todays, setTodays] = useState({}) // id -> /today, or null when that fetch failed
  const [error, setError] = useState(false)
  const [queue, setQueue] = useState(null)
  const [queueError, setQueueError] = useState(false)
  const [busy, setBusy] = useState(false)
  const [note, setNote] = useState(null)

  // Refetch when the demo clock moves to a new sol, like Today
  useEffect(() => {
    let alive = true
    api.getCrew()
      .then((list) => {
        if (!alive) return
        setCrew(list)
        // One failing /today must not hide the other three cards
        list.forEach((c) =>
          api.getToday(c.id, lang)
            .then((d) => alive && setTodays((m) => ({ ...m, [c.id]: d })))
            .catch(() => alive && setTodays((m) => ({ ...m, [c.id]: null }))),
        )
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
  }, [lang, sol])

  async function run(action) {
    setBusy(true)
    setNote(null)
    try {
      const q = await action()
      setQueue(q)
      setQueueError(false)
      return q
    } catch {
      setNote(t('crew.tx.failed'))
      return null
    } finally {
      setBusy(false)
    }
  }

  async function sendNow() {
    const q = await run(() => api.sendTx())
    // POST /tx/send only sends inside a comm window; anything still queued waits for the next one
    if (q?.some((p) => p.status === 'queued')) setNote(t('crew.tx.no_window', { time: mission?.next_window ?? '–' }))
  }

  if (error) return <section className="page"><p className="error">{t('common.error')}</p></section>
  if (!crew) return <section className="page"><p className="muted">{t('common.loading')}</p></section>

  const cmo = crew.find((c) => c.cmo)
  const viewer = crew.find((c) => c.id === CURRENT_CREW)
  const nameOf = (id) => crew.find((c) => c.id === id)?.name ?? id
  const waiting = queue?.some((p) => p.status === 'queued' || p.status === 'missing')

  return (
    <section className="page page-wide">
      <h1>{t('nav.crew')}</h1>
      {/* Spec §17: CMO only. Viewer switching arrives with Settings (POST /demo/viewer), so until then
          a non-CMO viewer still sees the screen, with a clear note instead of a lock */}
      <p className={`status ${viewer?.cmo ? 'lv-normal' : 'lv-hold'}`}>
        <span aria-hidden="true">{viewer?.cmo ? '✔' : '🔒'}</span>
        {viewer?.cmo
          ? t('crew.cmo_view', { name: viewer.name })
          : t('crew.cmo_only', { cmo: cmo?.name ?? '–', viewer: viewer?.name ?? CURRENT_CREW })}
      </p>

      <div className="crew-grid">
        {crew.map((c) => (
          <CrewCard key={c.id} member={c} today={todays[c.id]} failed={todays[c.id] === null} />
        ))}
      </div>

      <section className="panel">
        <div className="panel-head">
          <h2>{t('crew.tx.title')}</h2>
          <span className="muted small">
            {t('crew.tx.window', { time: mission?.next_window ?? '–' })} · {t('topbar.delay')}{' '}
            {mission ? t('topbar.minutes', { n: mission.one_way_delay_min }) : '–'}
          </span>
        </div>
        {queueError && <p className="panel-empty error">{t('crew.tx.error')}</p>}
        {!queueError && queue?.length === 0 && <p className="panel-empty muted">{t('crew.tx.empty')}</p>}
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
              </tr>
            </thead>
            <tbody>
              {queue.map((p) => (
                <tr key={p.seq}>
                  <td className="num right">{p.seq}</td>
                  <td>{p.crew ? nameOf(p.crew) : t('crew.tx.all')}</td>
                  <td>
                    {p.event_id != null
                      ? <Link to={`/events/${p.event_id}`} className="cite">{t('crew.tx.kind_event', { id: p.event_id })}</Link>
                      : t('crew.tx.kind_daily')}
                  </td>
                  <td><span className={`badge ${TX_PRIORITY_CLASS[p.priority] ?? 'neutral'}`}>{t(`crew.tx.priority.${p.priority}`)}</span></td>
                  <td><span className={`badge ${TX_STATUS_CLASS[p.status] ?? 'neutral'}`}>{t(`crew.tx.status.${p.status}`)}</span></td>
                  <td className="num right">{p.attempts}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
        <div className="response">
          <button type="button" className="btn-primary" onClick={sendNow} disabled={busy || !waiting}>
            {t('crew.tx.send')}
          </button>
          <button type="button" className="btn-secondary" onClick={() => run(() => api.queueDaily())} disabled={busy}>
            {t('crew.tx.add_daily')}
          </button>
          {note && <span className="muted small" role="status">{note}</span>}
        </div>
        <p className="panel-empty muted small">{t('crew.tx.hint')}</p>
      </section>
    </section>
  )
}
