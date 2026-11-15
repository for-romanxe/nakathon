// nextWindow.js — the next comm window as one label. next_window_at {sol, time} skips the blackout (CONTRACT §5.1,
// #51), so in a blackout it reads "Sol 57 · 08:00"; the time-only next_window is the fallback for an older backend.
export function nextWindowLabel(m) {
  const at = m?.next_window_at
  if (Number.isInteger(at?.sol) && typeof at?.time === 'string') return `Sol ${at.sol} · ${at.time}`
  return m?.next_window ?? '–'
}

// Body for POST /demo/clock that lands on that window (tomorrow's first one if today's have passed)
export function nextWindowJump(m) {
  const at = m?.next_window_at
  if (Number.isInteger(at?.sol) && typeof at?.time === 'string') return { sol: at.sol, time: at.time }
  return { sol: m.clock.sol + (m.next_window <= m.clock.time ? 1 : 0), time: m.next_window }
}
