// BodyFigure.jsx — the pixel body (spec §7-2): small square cells inside a body outline, coloured per region.
// Regions at caution or warning have their cells pushed outwards ("scattered"). Outline paths come from the
// team mockup (mockup/app/app.js). The figure only draws the levels it is given; it decides nothing.
import { useMemo, useRef } from 'react'
import { REGIONS } from './bodyRegions.js'

const W = 220
const H = 460
const CELL = 7 // cell pitch in figure units
const OUTLINE = [
  'M62 96 Q110 78 158 96 L166 200 Q160 250 150 262 L70 262 Q60 250 54 200 Z', // torso
  'M62 98 Q40 110 36 150 L26 236 Q24 250 34 252 L44 252 Q52 250 54 236 L64 160 Z', // right arm (viewer's left)
  'M158 98 Q180 110 184 150 L194 236 Q196 250 186 252 L176 252 Q168 250 166 236 L156 160 Z', // left arm
  'M72 262 L104 262 L108 330 L104 430 Q104 444 92 444 L78 444 Q68 444 70 430 L62 330 Z', // legs
  'M116 262 L148 262 L158 330 L150 430 Q152 444 142 444 L128 444 Q116 444 116 430 L112 330 Z',
]

const CHEST_END = 178 // torso cells above this y are the chest (heart), below it the core (temperature)

// Which region a body point belongs to, by the body part (outline shape) it is in, so every part of the body
// that has a sensor is covered, not just a circle around a centre. The right arm (viewer's left) has no sensor
// and stays unassigned. Order matters where shapes overlap (shoulders go to the torso).
function partRegion(ctx, parts, x, y) {
  const inside = (p) => ctx.isPointInPath(p, x, y)
  if (inside(parts.head) || inside(parts.neck)) return 'head'
  if (inside(parts.torso)) return y < CHEST_END ? 'heart' : 'core'
  if (inside(parts.leftArm)) return 'wrist' // EDA band on the left wrist: the whole left arm selects it
  if (parts.legs.some(inside)) return 'legs'
  if (inside(parts.rightArm)) return null
  return undefined // outside the body
}

// Which cells are inside the body, and which region each belongs to. Computed once with a canvas hit test.
// Needs the browser canvas API; without it (no DOM, or no 2D context) it returns [] and the figure is skipped.
function buildCells() {
  if (typeof document === 'undefined' || typeof Path2D === 'undefined') return []
  const ctx = document.createElement('canvas').getContext?.('2d')
  if (!ctx) return []
  const [torso, rightArm, leftArm, legL, legR] = OUTLINE.map((d) => new Path2D(d))
  const head = new Path2D()
  head.ellipse(110, 42, 26, 32, 0, 0, Math.PI * 2)
  const neck = new Path2D()
  neck.rect(98, 72, 24, 18)
  const parts = { head, neck, torso, leftArm, rightArm, legs: [legL, legR] }
  let seed = 7
  const rnd = () => { seed = (seed * 9301 + 49297) % 233280; return seed / 233280 }
  const cells = []
  for (let y = CELL / 2; y < H; y += CELL) {
    for (let x = CELL / 2; x < W; x += CELL) {
      const region = partRegion(ctx, parts, x, y)
      if (region === undefined) continue
      const r = region && REGIONS.find((g) => g.id === region)
      const raw = r ? Math.hypot(x - r.cx * W, y - r.cy * H) : 0
      cells.push({ x, y, region, raw, seed: rnd() })
    }
  }
  // dist: 0 at the region centre, 1 at its farthest cell (drives how far cells scatter)
  const far = {}
  for (const c of cells) if (c.region) far[c.region] = Math.max(far[c.region] ?? 0, c.raw)
  return cells.map(({ raw, ...c }) => ({ ...c, dist: c.region && far[c.region] ? raw / far[c.region] : 0 }))
}

// The region under a figure point is the region of the body cell under it. Each cell owns the whole CELL × CELL
// square around its centre (the drawn square is smaller only for looks), so the gaps between cells inside the
// body are clickable too. Cells exist only inside the body outline and already carry their region (same rule
// that colours them), so a click on the margin, outside the body, or on the right arm selects nothing.
function regionAt(cells, x, y) {
  let hit = null
  let bd = Infinity
  for (const c of cells) {
    const d = Math.max(Math.abs(c.x - x), Math.abs(c.y - y))
    if (d <= CELL / 2 && d < bd) { bd = d; hit = c }
  }
  return hit?.region ? REGIONS.find((r) => r.id === hit.region) : null
}

// Screen point -> figure (viewBox) point. Uses the SVG's own point API (no DOMPoint needed); if that is
// missing, falls back to the bounding box with the default "xMidYMid meet" scaling of the viewBox.
function toFigure(svg, clientX, clientY) {
  if (!svg) return null
  const ctm = svg.getScreenCTM?.()
  if (ctm && svg.createSVGPoint) {
    const p = svg.createSVGPoint()
    p.x = clientX
    p.y = clientY
    return p.matrixTransform(ctm.inverse())
  }
  const box = svg.getBoundingClientRect()
  const scale = Math.min(box.width / W, box.height / H)
  if (!scale) return null
  const offX = (box.width - W * scale) / 2
  const offY = (box.height - H * scale) / 2
  return { x: (clientX - box.left - offX) / scale, y: (clientY - box.top - offY) / scale }
}

let cellCache = null
// Cells are the same for every render; keep a good result, but never keep an empty one (try again next time)
function getCells() {
  if (!cellCache?.length) cellCache = buildCells()
  return cellCache
}

export default function BodyFigure({ levels, selected, onSelect, label, unavailableText }) {
  const svgRef = useRef(null)
  const cells = useMemo(() => getCells(), [])

  if (cells.length === 0) return <p className="panel-empty muted">{unavailableText}</p>

  // Click anywhere on the figure: turn the screen point into figure coordinates and pick the region there
  function handleClick(ev) {
    const pt = toFigure(svgRef.current, ev.clientX, ev.clientY)
    const region = pt && regionAt(cells, pt.x, pt.y)
    if (region) onSelect(region.id)
  }

  return (
    <svg ref={svgRef} className="body-figure" viewBox={`0 0 ${W} ${H}`} role="group" aria-label={label} onClick={handleClick}>
      {cells.map((c, i) => {
        const level = c.region ? levels[c.region] : null
        const off = level === 'caution' || level === 'warning'
        let { x, y } = c
        // Scatter: some outer cells of an off region move outwards, more for warning
        if (off && c.dist > 0.35 && c.seed < (level === 'warning' ? 0.55 : 0.38)) {
          const r = REGIONS.find((g) => g.id === c.region)
          const ang = Math.atan2(y - r.cy * H, x - r.cx * W)
          const amp = (level === 'warning' ? 9 : 5) * c.dist
          x += Math.cos(ang) * amp
          y += Math.sin(ang) * amp
        }
        const cls = ['cell', level ? `cell-${level}` : 'cell-base', c.region && c.region === selected ? 'cell-selected' : '']
          .filter(Boolean).join(' ')
        return <rect key={i} className={cls} x={x - 2.75} y={y - 2.75} width={5.5} height={5.5} rx={0.8} />
      })}
    </svg>
  )
}
