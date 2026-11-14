// BodyFigure.jsx — the pixel body (spec §7-2): small square cells inside a body outline, coloured per region.
// Regions at caution or warning have their cells pushed outwards ("scattered"). Outline paths come from the
// team mockup (mockup/app/app.js). The figure only draws the levels it is given; it decides nothing.
import { useMemo } from 'react'
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

function regionDistance(region, nx, ny) {
  return Math.hypot((nx - region.cx) * 0.48, ny - region.cy)
}

// Which cells are inside the body, and which region each belongs to. Computed once with a canvas hit test.
function buildCells() {
  const ctx = document.createElement('canvas').getContext('2d')
  const shapes = OUTLINE.map((d) => new Path2D(d))
  const head = new Path2D()
  head.ellipse(110, 42, 26, 32, 0, 0, Math.PI * 2)
  const neck = new Path2D()
  neck.rect(98, 72, 24, 18)
  shapes.push(head, neck)
  let seed = 7
  const rnd = () => { seed = (seed * 9301 + 49297) % 233280; return seed / 233280 }
  const cells = []
  for (let y = CELL / 2; y < H; y += CELL) {
    for (let x = CELL / 2; x < W; x += CELL) {
      if (!shapes.some((p) => ctx.isPointInPath(p, x, y))) continue
      const nx = x / W
      const ny = y / H
      let region = null
      let best = Infinity
      for (const r of REGIONS) {
        const d = regionDistance(r, nx, ny)
        if (d < r.r && d < best) { best = d; region = r }
      }
      cells.push({ x, y, region: region?.id ?? null, dist: region ? best / region.r : 0, seed: rnd() })
    }
  }
  return cells
}

let cellCache = null

export default function BodyFigure({ levels, selected, onSelect, label }) {
  const cells = useMemo(() => (cellCache ??= buildCells()), [])

  return (
    <svg className="body-figure" viewBox={`0 0 ${W} ${H}`} role="group" aria-label={label}>
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
      {/* Click targets: one per region, bigger than the cells */}
      {REGIONS.map((r) => (
        <ellipse
          key={r.id}
          className={`body-hit${r.id === selected ? ' on' : ''}`}
          cx={r.cx * W}
          cy={r.cy * H}
          rx={(r.r / 0.48) * W * 1.15}
          ry={r.r * H * 1.15}
          tabIndex={-1}
          onClick={() => onSelect(r.id)}
        />
      ))}
    </svg>
  )
}
