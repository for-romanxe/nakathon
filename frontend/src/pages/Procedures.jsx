// Procedures.jsx — on-device documents (spec §7-5). Two views on one route:
//   /procedures              every document as a card, filling the screen (search on top)
//   /procedures?id=hrp:sm-03#p5  that document on its own, paragraph 5 highlighted (source links land here)
// The search text rides along as ?q= so "← All documents" comes back to the same filtered grid.
import { useEffect, useRef, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { api } from '../api/client.js'
import { useT } from '../i18n/index.jsx'

// "hrp:sm-03#p5" -> { docId: "hrp:sm-03", n: 5 }; no paragraph -> n null
function parseRef(ref) {
  const [docId, para] = (ref ?? '').split('#')
  const m = /^p(\d+)$/.exec(para ?? '')
  return { docId: docId || null, n: m ? Number(m[1]) : null }
}

function matches(doc, q) {
  if (!q) return true
  const s = q.toLowerCase()
  return doc.id.toLowerCase().includes(s) || doc.title.toLowerCase().includes(s)
    || (doc.paragraphs ?? []).some((p) => p.text.toLowerCase().includes(s))
}

const withQuery = (q, extra = {}) => {
  const p = new URLSearchParams({ ...extra, ...(q ? { q } : {}) })
  const s = p.toString()
  return `/procedures${s ? `?${s}` : ''}`
}

export default function Procedures() {
  const { t, lang } = useT()
  const [params, setParams] = useSearchParams()
  const { docId: openId, n } = parseRef(params.get('id'))
  const query = params.get('q') ?? ''
  const [list, setList] = useState(null)
  const [error, setError] = useState(false)
  const [doc, setDoc] = useState(null) // { id, data } | { id, missing: true }
  const highlight = useRef(null)

  useEffect(() => {
    api.getDocs().then(setList).catch(() => setError(true))
  }, [])

  useEffect(() => {
    if (!openId) return undefined
    let alive = true
    api.getDoc(openId)
      .then((data) => alive && setDoc({ id: openId, data }))
      .catch(() => alive && setDoc({ id: openId, missing: true }))
    return () => { alive = false }
  }, [openId])

  const shown = openId && doc?.id === openId ? doc : null

  // Bring the highlighted paragraph into view once the document is on screen; the grid starts at the top
  useEffect(() => {
    if (shown) highlight.current?.scrollIntoView({ block: 'center', behavior: 'smooth' })
    else window.scrollTo({ top: 0 })
  }, [shown, n, openId])

  if (error) return <section className="page"><p className="error">{t('common.error')}</p></section>

  // ---- One document ----
  if (openId) {
    const paragraphs = shown?.data?.paragraphs ?? []
    const paraMissing = shown?.data && n != null && !paragraphs.some((p) => p.n === n)
    return (
      <section className="page proc-page">
        <Link className="back-link" to={withQuery(query)}>{t('proc.back')}</Link>
        <article className="panel proc-doc">
          {!shown && <p className="panel-empty muted">{t('common.loading')}</p>}
          {shown?.missing && <p className="notice lv-hold">{t('proc.doc_missing', { id: shown.id })}</p>}
          {shown?.data && (
            <>
              <div className="panel-head">
                <h1 className="proc-doc-title"><span className="cite">{shown.data.id}</span> {shown.data.title}</h1>
                <span className="muted small">{shown.data.org}</span>
              </div>
              {paraMissing && <p className="notice lv-hold">{t('proc.para_missing', { id: `${shown.id}#p${n}` })}</p>}
              {lang !== 'ko' && <p className="panel-empty muted small">{t('proc.korean_only')}</p>}
              <ol className="proc-paras">
                {paragraphs.map((p) => {
                  const on = p.n === n
                  return (
                    <li key={p.n} id={`p${p.n}`} ref={on ? highlight : null} className={on ? 'hl' : ''} lang="ko">
                      <span className="cite proc-pid">#p{p.n}</span>
                      <p>{p.text}</p>
                    </li>
                  )
                })}
              </ol>
            </>
          )}
        </article>
      </section>
    )
  }

  // ---- Every document as a card ----
  if (!list) return <section className="page"><p className="muted">{t('common.loading')}</p></section>
  const found = list.docs.filter((d) => matches(d, query.trim()))
  return (
    <section className="page proc-page">
      <div className="proc-top">
        <h1>{t('nav.procedures')}</h1>
        <div className="proc-search">
          <label className="sr-only" htmlFor="proc-search">{t('proc.search')}</label>
          <input id="proc-search" type="search" value={query} placeholder={t('proc.search')}
            onChange={(e) => setParams(e.target.value ? { q: e.target.value } : {}, { replace: true })} />
        </div>
      </div>
      {list.docs.length === 0 && <p className="panel panel-empty muted">{t('proc.empty')}</p>}
      {list.docs.length > 0 && found.length === 0 && <p className="panel panel-empty muted">{t('proc.no_results')}</p>}
      <ul className="proc-grid">
        {found.map((d) => (
          <li key={d.id}>
            <Link className="panel proc-card" to={withQuery(query, { id: d.id })}>
              <span className="cite">{d.id}</span>
              <span className="proc-title">{d.title}</span>
              {d.paragraphs?.[0]?.text && <span className="proc-excerpt" lang="ko">{d.paragraphs[0].text}</span>}
              <span className="muted small proc-meta">
                {d.org}{d.paragraphs && ` · ${t('proc.paragraphs', { n: d.paragraphs.length })}`}
              </span>
            </Link>
          </li>
        ))}
      </ul>
      <p className="muted small">
        {t('proc.count', { n: list.docs.length })}
        {list.sample && ` ${t('proc.fictional')} ${t('proc.sample')}`}
      </p>
    </section>
  )
}
