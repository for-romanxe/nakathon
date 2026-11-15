// procedureCheck.js — is a GET /events/{id}/procedure response safe to draw? (#47 FE-03)
// Returns the procedure ready for the screen, or null (the screen then shows its fallback) when a required field is
// missing, has the wrong shape, or the parts disagree with each other. This does not decide anything for the
// backend: a response whose `done`, approvals and `current_step` do not fit together is not shown at all.
const isText = (v) => typeof v === 'string' && v.length > 0

// Designated consenters who agreed to a step, each once
export const agreed = (p, step) => p.consenters.filter((c) => step.approvals.some((a) => a.crew === c))

export function usableProcedure(p) {
  if (p?.available !== true || !Array.isArray(p.steps) || !Array.isArray(p.consenters)) return null
  if (!p.consenters.every(isText) || !Number.isInteger(p.required) || p.required < 1) return null
  if (p.required > p.consenters.length) return null // a step that can never be done
  if (!p.steps.every((s) => isText(s?.step_id) && isText(s?.text) && (s.approvals == null || Array.isArray(s.approvals)))) return null
  const proc = {
    ...p,
    steps: p.steps.map((s) => ({ ...s, approvals: (s.approvals ?? []).filter((a) => isText(a?.crew)) })),
  }
  const consentSteps = proc.steps.filter((s) => s.needs_consent === true)
  // done must be a boolean that matches the distinct designated consents on that step
  if (!consentSteps.every((s) => typeof s.done === 'boolean' && s.done === (agreed(proc, s).length >= proc.required))) return null
  // current_step must be the first consent step still open, or null when there is none
  const firstOpen = consentSteps.find((s) => !s.done)?.step_id ?? null
  if ((proc.current_step ?? null) !== firstOpen) return null
  return proc
}
