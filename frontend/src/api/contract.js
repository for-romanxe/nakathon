// contract.js — shared enums loaded from /contracts (CONTRACT §0-3: load, never hard-code).
import enums from '../../../contracts/enums.json'

export const METRICS = enums.metrics // { hr: { label_en, label_ko, unit, decimals, source }, ... }
export const METRIC_KEYS = Object.keys(enums.metrics)
export const SENSITIVITY = enums.sensitivity // { standard: [advisory, warning], ... }

export function metricLabel(key, lang) {
  const m = METRICS[key]
  return m ? (lang === 'ko' ? m.label_ko : m.label_en) : key
}

export function formatMetric(key, value) {
  if (value == null) return '–'
  return Number(value).toFixed(METRICS[key]?.decimals ?? 1)
}
