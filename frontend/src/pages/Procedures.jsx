// Procedures.jsx — on-device documents (spec §7-5): list + search on the left, the open document on the right.
// /procedures?id=hrp:sm-03#p5 opens that document and highlights paragraph 5 (source links land here).
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

export default function Procedures() {
  const { t, lang } = useT()
  const [params] = useSearchParams()
  const { docId: askedId, n } = parseRef(params.get('id'))
  const [list, setList] = useState(null)
  const [error, setError] = useState(false)
  const [query, setQuery] = useState('')
  const [doc, setDoc] = useState(null) // { id, data } | { id, missing: true }
  const highlight = useRef(null)

  useEffect(() => {
    api.getDocs().then(setList).catch(() => setError(true))
  }, [])

  const openId = askedId ?? list?.docs[0]?.id ?? null

  useEffect(() => {
    if (!openId) return
    let alive = true
    api.getDoc(openId)
      .then((data) => alive && setDoc({ id: openId, data }))
      .catch(() => alive && setDoc({ id: openId, missing: true }))
    return () => { alive = false }
  }, [openId])

  const shown = doc?.id === openId ? doc : null

  // Bring the highlighted paragraph into view once the document is on screen
  useEffect(() => {
    highlight.current?.scrollIntoView({ block: 'center', behavior: 'smooth' })
  }, [shown, n])

  if (error) return <section className="page"><p className="error">{t('common.error')}</p></section>
  if (!list) return <section className="page"><p className="muted">{t('common.loading')}</p></section>

  const found = list.docs.filter((d) => matches(d, query.trim()))
  const paragraphs = shown?.data?.paragraphs ?? []
  const paraMissing = shown?.data && n != null && !paragraphs.some((p) => p.n === n)

  return (
    <section className="page proc-page">
      <h1>{t('nav.procedures')}</h1>
      <div className="proc-layout">
        <aside className="panel proc-list">
          <div className="proc-search">
            <label className="sr-only" htmlFor="proc-search">{t('proc.search')}</label>
            <input id="proc-search" type="search" value={query} placeholder={t('proc.search')}
              onChange={(e) => setQuery(e.target.value)} />
          </div>
          <ul>
            {found.map((d) => (
              <li key={d.id}>
                <Link to={`/procedures?id=${encodeURIComponent(d.id)}`} className={d.id === openId ? 'on' : ''}
                  aria-current={d.id === openId ? 'page' : undefined}>
                  <span className="cite">{d.id}</span>
                  <span className="proc-title">{d.title}</span>
                  <span className="muted small">
                    {d.org}{d.paragraphs && ` · ${t('proc.paragraphs', { n: d.paragraphs.length })}`}
                  </span>
                </Link>
              </li>
            ))}
          </ul>
          {found.length === 0 && <p className="panel-empty muted">{t('proc.no_results')}</p>}
          <p className="panel-empty muted small">
            {t('proc.count', { n: list.docs.length })} {t('proc.fictional')}
            {list.sample && ` ${t('proc.sample')}`}
          </p>
        </aside>

        <article className="panel proc-doc">
          {/* No document asked for and an empty list: nothing will load, so say so instead of "Loading" */}
          {!openId && <p className="panel-empty muted">{t('proc.empty')}</p>}
          {openId && !shown && <p className="panel-empty muted">{t('common.loading')}</p>}
          {shown?.missing && (
            <p className="notice lv-hold">{t('proc.doc_missing', { id: shown.id })}</p>
          )}
          {shown?.data && (
            <>
              <div className="panel-head">
                <h2><span className="cite">{shown.data.id}</span> {shown.data.title}</h2>
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
      </div>
    </section>
  )
}
