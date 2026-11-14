// DeviationScale.jsx — a small instrument strip: where a reading sits against the person's own baseline, in σ.
// The track runs from −4σ to +4σ with the caution (±2–3σ) and warning (beyond ±3σ) zones marked, as on the
// Trends chart. It only draws the z it is given; the needle colour comes from the backend level, never from z.
const RANGE = 4

export default function DeviationScale({ z, level }) {
  const known = typeof z === 'number' && Number.isFinite(z)
  const clamped = known ? Math.max(-RANGE, Math.min(RANGE, z)) : 0
  const left = `${((clamped + RANGE) / (2 * RANGE)) * 100}%`
  const tint = level === 'caution' || level === 'warning' ? level : 'plain'
  return (
    <span className={`dev-scale${known ? '' : ' dev-unknown'}`} aria-hidden="true">
      <span className="dev-track" />
      <span className="dev-zero" />
      {known && <span className={`dev-needle dev-${tint}`} style={{ left }} />}
    </span>
  )
}
