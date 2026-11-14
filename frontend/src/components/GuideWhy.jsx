// GuideWhy.jsx — "Why?" on a guide item (spec S13, ⑤). Answers only from documents on this device: the
// paragraphs the guide item cites. If none of them is on the device, it says it cannot answer (abstain)
// instead of making something up. A failed request is shown as an error with retry, never as "no answer".
import { useState } from 'react'
import { api } from '../api/client.js'
import Cite from './Cite.jsx'
import { useT } from '../i18n/index.jsx'

async function findParagraphs(cites) {
  const found = []
  for (const id of cites) {
    const [docId, para] = id.split('#p')
    const doc = await api.getDoc(docId).catch((e) => {
      if (e?.code === 'doc_not_found') return null // not on this device: skip it
      throw e
    })
    const p = doc?.paragraphs?.find((x) => String(x.n) === para)
    if (p) found.push({ id, title: doc.title, text: p.text })
  }
  return found
}

export default function GuideWhy({ cites }) {
  const { t } = useT()
  const [open, setOpen] = useState(false)
  const [state, setState] = useState(null) // null | 'loading' | 'error' | { found: [...] }

  function load() {
    setState('loading')
    findParagraphs(cites ?? [])
      .then((found) => setState({ found }))
      .catch(() => setState('error'))
  }

  function toggle() {
    const next = !open
    setOpen(next)
    if (next && (state === null || state === 'error')) load()
  }

  return (
    <div className="why">
      <button type="button" className="why-btn" aria-expanded={open} onClick={toggle}>
        {t('why.ask')}
      </button>
      {open && (
        <div className="why-answer" aria-live="polite">
          {state === 'loading' && <p className="muted">{t('common.loading')}</p>}
          {state === 'error' && (
            <p className="error">
              {t('why.error')}{' '}
              <button type="button" className="btn-ghost" onClick={load}>{t('why.retry')}</button>
            </p>
          )}
          {state?.found?.length > 0 && (
            <>
              <p className="muted small">{t('why.from_docs')}</p>
              {state.found.map((f) => (
                <blockquote key={f.id} className="why-quote">
                  <p>{f.text}</p>
                  <footer className="small"><span className="muted">{f.title}</span> <Cite id={f.id} /></footer>
                </blockquote>
              ))}
            </>
          )}
          {state?.found?.length === 0 && <p className="muted">{t('why.abstain')}</p>}
        </div>
      )}
    </div>
  )
}
