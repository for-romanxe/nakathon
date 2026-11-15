// procedureCheck.js — is a GET /events/{id}/procedure response safe to draw? (#47 FE-03)
// Returns the procedure ready for the screen, or null (the screen then shows its fallback) when a required field is
// missing, has the wrong shape, or the parts disagree with each other. This does not decide anything for the
// backend: a response whose people, `done`, approvals and `current_step` do not fit together is not shown at all.
import { CREW_IDS } from './session.js'

const isText = (v) => typeof v === 'string' && v.length > 0
const isCrew = (v) => CREW_IDS.includes(v)
const unique = (list) => new Set(list).size === list.length

// Designated consenters who agreed to a step. Only called on a checked procedure, where each person appears once
export const agreed = (p, step) => p.consenters.filter((c) => step.approvals.some((a) => a.crew === c))

export function usableProcedure(p) {
  if (p?.available !== true || !Array.isArray(p.steps) || !Array.isArray(p.consenters)) return null
  // people: a real patient, real consenters, each named once, and the patient is never one of them
  if (!isCrew(p.patient) || !p.consenters.every(isCrew) || !unique(p.consenters) || p.consenters.includes(p.patient)) return null
  if (!Number.isInteger(p.required) || p.required < 1 || p.required > p.consenters.length) return null
  if (!p.steps.every((s) => isText(s?.step_id) && isText(s?.text) && (s.approvals == null || Array.isArray(s.approvals)))) return null
  const steps = p.steps.map((s) => ({ ...s, approvals: s.approvals ?? [] }))
  // every approval is one designated consenter, at most once per step (so no duplicate and no patient vote)
  for (const s of steps) {
    const who = s.approvals.map((a) => a?.crew)
    if (!who.every((c) => p.consenters.includes(c)) || !unique(who)) return null
  }
  const proc = { ...p, steps }
  const consentSteps = steps.filter((s) => s.needs_consent === true)
  // done must be a boolean that matches the consents on that step
  if (!consentSteps.every((s) => typeof s.done === 'boolean' && s.done === (agreed(proc, s).length >= proc.required))) return null
  // current_step must be the first consent step still open, or null when there is none
  const firstOpen = consentSteps.find((s) => !s.done)?.step_id ?? null
  if ((proc.current_step ?? null) !== firstOpen) return null
  return proc
}
