// GuideWhy.jsx — "Why?" on a guide item (spec S13, ⑤). Answers only from documents on this device: the
// paragraphs the guide item cites. If none of them is on the device, it says it cannot answer (abstain)
// instead of making something up. Each citation is looked up on its own: a failed request shows an error
// for that citation only (with retry), never as "no answer", and paragraphs already found stay.
import { useRef, useState } from 'react'
import { api } from '../api/client.js'
import Cite from './Cite.jsx'
import { useT } from '../i18n/index.jsx'

// One citation -> { id, status: 'found' | 'missing' | 'error', title?, text? }
async function lookUp(id) {
  const [docId, para] = id.split('#p')
  try {
    const doc = await api.getDoc(docId)
    const p = doc?.paragraphs?.find((x) => String(x.n) === para)
    return p ? { id, status: 'found', title: doc.title, text: p.text } : { id, status: 'missing' }
  } catch (e) {
    return { id, status: e?.code === 'doc_not_found' ? 'missing' : 'error' } // not on this device vs. failed
  }
}

export default function GuideWhy({ cites }) {
  const { t } = useT()
  const list = cites ?? []
  const key = list.join('|')
  const [open, setOpen] = useState(false)
  // { key, results: { [id]: result | 'loading' } } — results belong to the citations they were asked for
  const [answer, setAnswer] = useState(null)
  const requestRef = useRef(0) // a response is used only if no newer request (or close) came after it
  const results = answer?.key === key ? answer.results : null

  function load(ids) {
    const request = ++requestRef.current
    setAnswer((a) => {
      const prev = a?.key === key ? a.results : {}
      return { key, results: { ...prev, ...Object.fromEntries(ids.map((id) => [id, 'loading'])) } }
    })
    for (const id of ids) {
      lookUp(id).then((r) => {
        if (requestRef.current !== request) return // closed, retried or cites changed meanwhile: drop it
        setAnswer((a) => (a?.key === key ? { key, results: { ...a.results, [id]: r } } : a))
      })
    }
  }

  function toggle() {
    if (open) {
      requestRef.current++ // stop listening to anything still in flight
      setOpen(false)
      // unfinished lookups are forgotten so they start again next time
      if (results) setAnswer({ key, results: Object.fromEntries(Object.entries(results).filter(([, r]) => r !== 'loading')) })
      return
    }
    setOpen(true)
    const todo = list.filter((id) => !results?.[id] || results[id] === 'loading' || results[id].status === 'error')
    if (todo.length) load(todo)
  }

  const values = list.map((id) => results?.[id]).filter(Boolean)
  const loading = values.some((r) => r === 'loading')
  const found = values.filter((r) => r.status === 'found')
  const failed = values.filter((r) => r.status === 'error').map((r) => r.id)
  const settled = !loading && values.length === list.length

  return (
    <div className="why">
      <button type="button" className="why-btn" aria-expanded={open} onClick={toggle}>
        {t('why.ask')}
      </button>
      {open && (
        <div className="why-answer" aria-live="polite">
          {found.length > 0 && (
            <>
              <p className="muted small">{t('why.from_docs')}</p>
              {found.map((f) => (
                <blockquote key={f.id} className="why-quote">
                  <p>{f.text}</p>
                  <footer className="small"><span className="muted">{f.title}</span> <Cite id={f.id} /></footer>
                </blockquote>
              ))}
            </>
          )}
          {loading && <p className="muted">{t('common.loading')}</p>}
          {!loading && failed.length > 0 && (
            <p className="error">
              {t('why.error')}{' '}
              <button type="button" className="btn-ghost" onClick={() => load(failed)}>{t('why.retry')}</button>
            </p>
          )}
          {settled && found.length === 0 && failed.length === 0 && <p className="muted">{t('why.abstain')}</p>}
        </div>
      )}
    </div>
  )
}
