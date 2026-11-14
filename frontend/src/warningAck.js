// warningAck.js — remembers which crew/sol warning was acknowledged, so Today does not reopen the
// full-screen warning after the crew member has seen it. Kept for the app session only.
const acked = new Set()

export const warningKey = (crewId, sol) => `${crewId}:${sol}`
export const isWarningAcked = (key) => acked.has(key)
export const ackWarning = (key) => acked.add(key)
