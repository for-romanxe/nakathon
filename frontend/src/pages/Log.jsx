// Log.jsx — symptom chat (spec §7-4, scenario S2/S9). The only screen where free text reaches the model.
// Flow: report -> (rules) -> optional confirm question -> pipeline stages -> result card -> event detail.
import { useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { api, runPipeline } from '../api/client.js'
import { isUrgentReport, formatTs } from '../api/contract.js'
import { CURRENT_CREW } from '../session.js'
import { useT } from '../i18n/index.jsx'
import PipelineProgress from '../components/PipelineProgress.jsx'

const EXAMPLES = ['log.example.dizzy', 'log.example.headache', 'log.example.chest']

export default function Log() {
  const { t, lang } = useT()
  const [text, setText] = useState('')
  // idle: can send | question: waiting for the yes/no answer | running: rules + pipeline in progress
  const [phase, setPhase] = useState('idle')
  const busy = phase !== 'idle'
  const [items, setItems] = useState([]) // chat items for this session
  const [todayEvents, setTodayEvents] = useState([])
  const [results, setResults] = useState(0) // refetch today's reports only when a new result arrives
  const bottom = useRef(null)

  useEffect(() => {
    api.getToday(CURRENT_CREW, lang).then((d) => setTodayEvents(d.events)).catch(() => {})
  }, [lang, results])

  useEffect(() => { bottom.current?.scrollIntoView({ block: 'end' }) }, [items])

  const push = (item) => setItems((list) => [...list, { key: `${Date.now()}-${list.length}`, ...item }])
  const update = (key, patch) => setItems((list) => list.map((i) => (i.key === key ? { ...i, ...patch } : i)))

  async function finish(eventId, urgent) {
    const key = `run-${eventId}`
    setItems((list) => [...list, { key, kind: 'pipeline', stages: [], final: null }])
    try {
      const final = await runPipeline(eventId, {
        urgent,
        onStage: (stage) => setItems((list) => list.map((i) => (i.key === key ? { ...i, stages: [...i.stages, stage] } : i))),
      })
      update(key, { final })
      const event = await api.getEvent(eventId)
      push({ kind: 'result', event })
      setResults((n) => n + 1)
    } catch {
      update(key, { final: 'interrupted' })
      push({ kind: 'error' })
    } finally {
      setPhase('idle') // the input never stays locked
    }
  }

  async function send(value) {
    const report = value.trim()
    if (!report || busy) return
    setPhase('running')
    setText('')
    push({ kind: 'me', text: report })
    try {
      const res = await api.postSymptom(CURRENT_CREW, report, lang)
      const first = await api.getEvent(res.event_id) // the rules already ran: level warning means the model is skipped (§5.4)
      const urgent = first.level === 'warning'
      if (!urgent && res.needs_question) {
        push({ kind: 'question', eventId: res.event_id, question: res.question, answered: null })
        setPhase('question') // input stays closed until this report is answered and finished
        return
      }
      await finish(res.event_id, urgent)
    } catch {
      push({ kind: 'error' })
      setPhase('idle')
    }
  }

  async function answer(item, value) {
    if (phase !== 'question') return
    setPhase('running')
    update(item.key, { answered: value })
    try {
      const { saved } = await api.postAnswer(item.eventId, value)
      if (!saved) push({ kind: 'note', text: t('log.answer_not_saved') }) // finish() then shows the event as it really is
      await finish(item.eventId, false)
    } catch {
      push({ kind: 'error' })
      setPhase('idle')
    }
  }

  return (
    <section className="page log">
      <h1>{t('log.title')}</h1>
      <p className="muted">{t('log.hint')}</p>

      <section className="panel chat">
        {items.length === 0 && <p className="panel-empty muted">{t('log.empty')}</p>}
        <ul className="chat-list">
          {items.map((item) => (
            <li key={item.key} className={`chat-item ${item.kind}`}>
              {item.kind === 'me' && <p className="bubble-me">{item.text}</p>}
              {item.kind === 'question' && (
                <div className="bubble-sys">
                  <p>{item.question}</p>
                  <div className="choice-buttons">
                    {['yes', 'no'].map((v) => (
                      <button
                        key={v}
                        type="button"
                        className={item.answered === v ? 'selected' : ''}
                        disabled={item.answered != null || phase !== 'question'}
                        onClick={() => answer(item, v)}
                      >
                        {t(`common.${v}`)}
                      </button>
                    ))}
                  </div>
                </div>
              )}
              {item.kind === 'pipeline' && <PipelineProgress stages={item.stages} final={item.final} />}
              {item.kind === 'result' && <ResultCard event={item.event} />}
              {item.kind === 'note' && <p className="bubble-sys muted">{item.text}</p>}
              {item.kind === 'error' && <p className="bubble-sys error">{t('log.error')}</p>}
            </li>
          ))}
        </ul>
        <div ref={bottom} />
      </section>

      <form className="composer" onSubmit={(e) => { e.preventDefault(); send(text) }}>
        <label htmlFor="symptom-input" className="sr-only">{t('log.input_label')}</label>
        <textarea
          id="symptom-input"
          rows={2}
          maxLength={4000}
          value={text}
          placeholder={phase === 'question' ? t('log.answer_first') : t('log.placeholder')}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={(e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send(text) } }}
          disabled={busy}
        />
        <button type="submit" className="btn-primary" disabled={busy || !text.trim()}>{t('log.send')}</button>
      </form>
      <div className="examples">
        {EXAMPLES.map((k) => (
          <button key={k} type="button" className="btn-secondary" disabled={busy} onClick={() => send(t(k))}>
            {t(k)}
          </button>
        ))}
      </div>

      {todayEvents.length > 0 && (
        <section className="panel">
          <div className="panel-head"><h2>{t('log.today_reports')}</h2></div>
          <ul className="event-list">
            {todayEvents.map((e) => (
              <li key={e.id}>
                <Link to={`/events/${e.id}`}>
                  <span className={`badge lv-${e.level}`}>{t(`level.${e.level}`)}</span>
                  <span>{e.symptom_text}</span>
                  <span className="num muted">{formatTs(e.ts, true)}</span>
                </Link>
              </li>
            ))}
          </ul>
        </section>
      )}
    </section>
  )
}

function ResultCard({ event }) {
  const { t } = useT()
  const urgent = event.level === 'warning' // full-screen warning + model skipped: decided by level (§5.4)
  const runs = event.runs ?? []
  const failedTwice = runs.length >= 2 && !runs.some((r) => r.ok)
  // Say only what actually happened: warning (and why), withheld (stage "hold" wins over any run count),
  // verified explanation, or no explanation yet
  const message = urgent
    ? t(isUrgentReport(event) ? 'log.result.urgent' : 'log.result.measured')
    : event.stage === 'hold' || failedTwice
      ? t(failedTwice ? 'event.withheld' : 'event.withheld_hold')
      : runs.some((r) => r.ok)
        ? t('log.result.normal')
        : t('log.result.pending')
  return (
    <div className={`result-card lv-${event.level}`}>
      <div className="result-head">
        <span className={`badge lv-${event.level}`}>{t(`level.${event.level}`)}</span>
        <b>{event.title}</b>
      </div>
      <p className="muted">{message}</p>
      <div className="result-actions">
        {urgent && <Link className="btn-primary" to={`/warning?event=${event.id}`}>{t('log.open_warning')}</Link>}
        <Link className={urgent ? 'btn-secondary' : 'btn-primary'} to={`/events/${event.id}`}>{t('log.open_event')}</Link>
      </div>
    </div>
  )
}
