// BodyFigure.jsx — the pixel body (spec §7-2): small square cells inside a body outline, coloured per region.
// Regions at caution or warning have their cells pushed outwards ("scattered"). Outline after the team mockup
// (mockup/app/app.js), redrawn mirror-symmetric about x = 110 with a gap between the arms and the torso and
// between the legs. The figure only draws the levels it is given; it decides nothing.
import { useMemo, useRef } from 'react'
import { REGIONS } from './bodyRegions.js'

const W = 220
const H = 460
const MID = W / 2 // the body's centre line; outline and cell grid are both symmetric about it
const CELL = 4 // cell pitch in figure units
const DOT = 3.1 // drawn square (smaller than the pitch so the cells read as pixels)
// Every path on the left of MID has a mirror on the right: x' = 220 − x
const OUTLINE = [
  'M66 96 Q110 80 154 96 L160 200 Q156 250 148 262 L72 262 Q64 250 60 200 Z', // torso
  'M55 100 Q38 108 34 140 L24 232 Q22 246 30 248 L40 248 Q48 246 48 232 L53 150 Z', // right arm (viewer's left)
  'M165 100 Q182 108 186 140 L196 232 Q198 246 190 248 L180 248 Q172 246 172 232 L167 150 Z', // left arm
  'M74 266 L106 266 L106 330 L102 430 Q102 444 92 444 L80 444 Q70 444 72 430 L66 330 Z', // right leg
  'M146 266 L114 266 L114 330 L118 430 Q118 444 128 444 L140 444 Q150 444 148 430 L154 330 Z', // left leg
]

// Cell centres on a grid that is symmetric about MID (… MID−6, MID−2, MID+2, MID+6 …)
function axis(from, to, mid) {
  const out = []
  for (let d = CELL / 2; mid - d >= from || mid + d <= to; d += CELL) {
    if (mid - d >= from) out.push(mid - d)
    if (mid + d <= to) out.push(mid + d)
  }
  return out.sort((a, b) => a - b)
}

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
  const xs = axis(0, W, MID)
  for (let y = CELL / 2; y < H; y += CELL) {
    for (const x of xs) {
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
// that colours them), so a click on the margin or outside the body hits no cell. Returns the cell or null.
function cellAt(cells, x, y) {
  let hit = null
  let bd = Infinity
  for (const c of cells) {
    const d = Math.max(Math.abs(c.x - x), Math.abs(c.y - y))
    if (d <= CELL / 2 && d < bd) { bd = d; hit = c }
  }
  return hit
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

export default function BodyFigure({ levels, selected, onSelect, onNoSensor, label, unavailableText }) {
  const svgRef = useRef(null)
  const cells = useMemo(() => getCells(), [])

  if (cells.length === 0) return <p className="panel-empty muted">{unavailableText}</p>

  // Click anywhere on the figure: turn the screen point into figure coordinates and pick the region there.
  // A body cell without a region (the right arm: no sensor there) tells the page so it can explain why.
  function handleClick(ev) {
    const pt = toFigure(svgRef.current, ev.clientX, ev.clientY)
    const cell = pt && cellAt(cells, pt.x, pt.y)
    if (cell?.region) onSelect(cell.region)
    else if (cell) onNoSensor?.()
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
        return <rect key={i} className={cls} x={x - DOT / 2} y={y - DOT / 2} width={DOT} height={DOT} rx={0.5} />
      })}
    </svg>
  )
}
