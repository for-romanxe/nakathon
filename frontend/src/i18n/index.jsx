// i18n — every UI string comes from en.js / ko.js. Never hard-code display text in components.
// English is the primary language; Korean is the secondary version.
import { createContext, useContext, useState } from 'react'
import en from './en.js'
import ko from './ko.js'

const DICTS = { en, ko }
const LangContext = createContext(null)

export function LangProvider({ children }) {
  const [lang, setLang] = useState('en')
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
