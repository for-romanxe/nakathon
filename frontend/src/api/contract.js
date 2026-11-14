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

export const PIPELINE_STAGES = enums.pipeline_stage // collect → rules → symptom → question → retrieve → generate → verify → done | hold
export const VERIFY_CHECKS = enums.verify_check // numbers, cites, level, schema, wording
export const OVERRIDE_REASONS = enums.override_reason
export const IMMEDIATE_WARNING_CODES = enums.immediate_warning_codes

// Condition names come only from the fixed on-device list (CONTRACT §0-3)
export function conditionLabel(id, lang) {
  const c = enums.conditions[id]
  return c ? (lang === 'ko' ? c.ko : c.en) : id
}
