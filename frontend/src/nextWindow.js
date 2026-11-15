// nextWindow.js — the next comm window as one label. next_window_at {sol, time} skips the blackout (CONTRACT §5.1,
// #51), so in a blackout it reads "Sol 57 · 08:00"; the time-only next_window is the fallback for an older backend.
const HHMM = /^(?:[01]\d|2[0-3]):[0-5]\d$/
const validAt = (at) => Number.isInteger(at?.sol) && HHMM.test(at?.time ?? '')

export function nextWindowLabel(m) {
  if (validAt(m?.next_window_at)) return `Sol ${m.next_window_at.sol} · ${m.next_window_at.time}`
  return HHMM.test(m?.next_window ?? '') ? m.next_window : '–'
}

// {sol, time} of that window (tomorrow's first one if today's have passed), or null when the mission state does not
// say where it is — callers then show no time and do not move the clock
export function nextWindowJump(m) {
  if (validAt(m?.next_window_at)) return { sol: m.next_window_at.sol, time: m.next_window_at.time }
  if (!Number.isInteger(m?.clock?.sol) || !HHMM.test(m?.clock?.time ?? '') || !HHMM.test(m?.next_window ?? '')) return null
  return { sol: m.clock.sol + (m.next_window <= m.clock.time ? 1 : 0), time: m.next_window }
}
