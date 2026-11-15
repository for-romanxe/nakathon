// i18n — every UI string comes from en.js / ko.js. Never hard-code display text in components.
// English is the primary language; Korean is the secondary version.
import { createContext, useContext, useState } from 'react'
import en from './en.js'
import ko from './ko.js'

const DICTS = { en, ko }
const LangContext = createContext(null)
// The chosen language survives a reload and switching crew member (both reload the page). Browser storage may be
// unavailable (private window, blocked site data): then it is English as before.
const LANG_KEY = 'crew-health-lang'
function storedLang() {
  try { return DICTS[localStorage.getItem(LANG_KEY)] ? localStorage.getItem(LANG_KEY) : 'en' } catch { return 'en' }
}

export function LangProvider({ children }) {
  const [lang, setLangState] = useState(storedLang)
  const setLang = (next) => {
    setLangState(next)
    try { localStorage.setItem(LANG_KEY, next) } catch { /* this page only */ }
  }
  return <LangContext.Provider value={{ lang, setLang }}>{children}</LangContext.Provider>
}

// t('nav.today') or t('today.greeting.morning', { name: 'A' })
export function useT() {
  const { lang, setLang } = useContext(LangContext)
  const t = (key, vars = {}) => {
    const text = DICTS[lang][key] ?? DICTS.en[key] ?? key // a missing key shows itself, so gaps are easy to spot
    return text.replace(/\{(\w+)\}/g, (_, k) => vars[k] ?? `{${k}}`)
  }
  return { t, lang, setLang }
}
