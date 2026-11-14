// HoloBody.jsx — the body as a 3D blueprint wireframe (spec §7-2, Body screen).
//
// Visual approach adapted from redradman/artemis (MIT License, Copyright (c) 2026 Radman Rakhshandehroo,
// https://github.com/redradman/artemis): every part is drawn with lines only — its edges (strong) plus its full
// wireframe (faint) — on a navy cyanotype sheet with a two-level grid; the selected part turns to the accent colour
// while the others step back; leader labels sit in two columns, joined to their parts by thin lines.
// Adapted for this app: parts of a region at caution / warning take that status colour (the backend's level; the
// figure decides nothing), the heart beats with a soft light (asked for on 11/14), L / R tags and report "!" marks.
// Click a part (or its label) to select its region; each arm and each leg is its own region. Drag to turn.
import { useEffect, useRef, useState } from 'react'
import * as THREE from 'three'

const V = (x, y, z = 0) => new THREE.Vector3(x, y, z)
const DOWN = V(0, -1, 0)
const HEART_AT = V(0.035, 1.3, 0.02) // inside the chest, a little to the person's left

// Blueprint palette (as in the reference's blueprint mode): paper-cyan lines, sky-cyan accent, navy sheet
const PAPER = 0xdceafe
const ACCENT = 0x8fd2ff
const NAVY = 0x0b2e55

// A tapered limb segment from a to b (radius r1 at a, r2 at b) with rounded ends: a lathe turned to point a → b
function segment(a, b, r1, r2) {
  const dir = b.clone().sub(a)
  const len = dir.length()
  const pts = []
  for (let k = 0; k <= 6; k++) { const t = (k / 6) * (Math.PI / 2); pts.push(new THREE.Vector2(r1 * Math.sin(t), r1 * Math.cos(t))) }
  for (let k = 0; k <= 6; k++) { const t = (k / 6) * (Math.PI / 2); pts.push(new THREE.Vector2(r2 * Math.cos(t), -len - r2 * Math.sin(t))) }
  return { geo: new THREE.LatheGeometry(pts.reverse(), 16), quat: new THREE.Quaternion().setFromUnitVectors(DOWN, dir.normalize()) }
}

// Body parts: { region, geo, pos, quat | rotX | rotZ, scale }. Units ≈ metres, feet at y 0, the figure faces the
// camera (+z), so the person's left is on the viewer's right (+x).
function parts() {
  const lathe = (pts, seg = 28) => new THREE.LatheGeometry(pts.map(([r, y]) => new THREE.Vector2(r, y)), seg)
  const out = []
  const add = (region, geo, pos, extra = {}) => out.push({ region, geo, pos, ...extra })
  const limb = (region, a, b, r1, r2) => { const s = segment(a, b, r1, r2); add(region, s.geo, a, { quat: s.quat }) }

  // Head, with a nose so the face (the front) is clear when the figure turns
  add('head', new THREE.SphereGeometry(0.115, 20, 14), V(0, 1.635), { scale: [0.86, 1.1, 0.98] })
  add('head', new THREE.ConeGeometry(0.018, 0.045, 8), V(0, 1.615, 0.112), { rotX: Math.PI / 2 })
  limb('head', V(0, 1.54), V(0, 1.47), 0.048, 0.054) // neck
  // Torso in one piece (shoulders → chest → waist → hips), flattened front to back: Torso · Temperature
  add('core', lathe([[0, 0.78], [0.13, 0.78], [0.158, 0.84], [0.162, 0.9], [0.145, 0.99], [0.138, 1.06], [0.15, 1.16],
    [0.172, 1.28], [0.195, 1.38], [0.2, 1.42], [0.18, 1.47], [0.09, 1.5], [0, 1.505]]), V(0, 0), { scale: [1, 1, 0.6] })
  // Heart inside the chest, apex pointing down to the person's left: Heart · Circulation
  add('heart', lathe([[0, -0.07], [0.02, -0.05], [0.042, -0.02], [0.056, 0.012], [0.054, 0.042], [0.034, 0.064], [0, 0.07]], 16),
    HEART_AT, { rotZ: 0.45, scale: [1, 1, 0.85], heart: true })
  for (const side of [-1, 1]) { // −1: the person's right (viewer's left), +1: the person's left
    const sx = (v) => v * side
    const arm = side > 0 ? 'left_arm' : 'right_arm' // the EDA band is on the left wrist; the right arm has no sensor
    const leg = side > 0 ? 'left_leg' : 'right_leg'
    add(arm, new THREE.SphereGeometry(0.05, 12, 8), V(sx(0.235), 1.44)) // shoulder
    limb(arm, V(sx(0.25), 1.41), V(sx(0.285), 1.15), 0.046, 0.038) // upper arm
    limb(arm, V(sx(0.285), 1.15), V(sx(0.31), 0.92), 0.038, 0.03) // forearm
    add(arm, new THREE.SphereGeometry(0.045, 10, 8), V(sx(0.315), 0.85, 0.01), { scale: [0.62, 1.2, 0.42] }) // hand
    limb(leg, V(sx(0.095), 0.82), V(sx(0.09), 0.47), 0.075, 0.052) // thigh
    limb(leg, V(sx(0.09), 0.47), V(sx(0.085), 0.08), 0.052, 0.036) // calf
    limb(leg, V(sx(0.085), 0.045, -0.02), V(sx(0.092), 0.035, 0.12), 0.036, 0.03) // foot, toes forward
  }
  add('left_arm', new THREE.TorusGeometry(0.038, 0.01, 6, 20), V(0.306, 0.95), { rotX: Math.PI / 2 }) // EDA band
  return out
}

// Where each label's leader line ends on the part, in figure coordinates
const ANCHOR_AT = {
  head: V(0, 1.66, 0.1),
  heart: HEART_AT,
  core: V(0, 1.0, 0.1),
  left_arm: V(0.3, 1.02, 0.03),
  right_arm: V(-0.3, 1.02, 0.03),
  left_leg: V(0.09, 0.47, 0.05),
  right_leg: V(-0.09, 0.47, 0.05),
}

// Where a symptom-report mark (!) floats when labels are off (with labels on, the label carries the "!")
const MARK_AT = {
  head: V(0, 1.8, 0.05),
  heart: V(0.115, 1.18, 0.16),
  core: V(0, 1.0, 0.13),
  left_arm: V(0.4, 1.1, 0.04),
  right_arm: V(-0.4, 1.1, 0.04),
  left_leg: V(0.2, 0.5, 0.06),
  right_leg: V(-0.2, 0.5, 0.06),
}

// A soft round glow (for the heart) and a ringed letter (L / R / !), drawn once on small canvases
function glowTexture() {
  const c = document.createElement('canvas')
  c.width = c.height = 128
  const g = c.getContext('2d')
  const grad = g.createRadialGradient(64, 64, 0, 64, 64, 64)
  grad.addColorStop(0, 'rgba(255,255,255,1)')
  grad.addColorStop(0.25, 'rgba(255,255,255,0.45)')
  grad.addColorStop(1, 'rgba(255,255,255,0)')
  g.fillStyle = grad
  g.fillRect(0, 0, 128, 128)
  return new THREE.CanvasTexture(c)
}
function letterTexture(text) {
  const c = document.createElement('canvas')
  c.width = c.height = 128
  const g = c.getContext('2d')
  g.strokeStyle = 'rgba(255,255,255,0.8)'
  g.lineWidth = 4
  g.beginPath()
  g.arc(64, 64, 54, 0, Math.PI * 2)
  g.stroke()
  g.fillStyle = '#fff'
  g.font = `500 ${text.length > 1 ? 44 : 60}px "IBM Plex Mono", "IBM Plex Sans KR", monospace`
  g.textAlign = 'center'
  g.textBaseline = 'middle'
  g.fillText(text, 64, 68)
  return new THREE.CanvasTexture(c)
}

function token(name, fallback) {
  const v = getComputedStyle(document.documentElement).getPropertyValue(name).trim()
  return new THREE.Color(v || fallback)
}

// Leader-label layout (after the reference's Labels): a label goes to the side of the screen its part is on, with
// a small dead zone around the middle so it does not flip back and forth; the leader is longer for parts near the
// silhouette and shorter for parts deep inside; labels on one side are spread so they never overlap.
const ROW = 26
const TOP = 56 // below the control buttons
const EDGE = 12
const TEXT_GAP = 9
// When a side has more labels than rows fit between the buttons and the bottom, the ones that would land under
// the buttons are hidden instead of overlapping (the region list still has every part).
function spread(items, h) {
  items.sort((a, b) => a.y - b.y)
  let prev = -Infinity
  for (const it of items) { it.ly = Math.max(it.y, prev + ROW, TOP); prev = it.ly }
  let next = h - 14
  for (let i = items.length - 1; i >= 0; i--) { items[i].ly = Math.min(items[i].ly, next); next = items[i].ly - ROW }
  for (const it of items) it.hidden = it.ly < TOP
}

// marks: { [regionId]: level } — regions a symptom report points at, coloured by that report's level
// callouts: [{ id, text, level, reported }] — the labels drawn beside the figure
// texts: { rotate, labels, reset } — the control button words
export default function HoloBody({ levels, selected, onSelect, marks, callouts = [], texts = {}, label, unavailableText, sideLabels }) {
  const hostRef = useRef(null)
  const labelRefs = useRef({}) // id -> { line, end, tick, text }
  const resetRef = useRef(() => {})
  const [autoRotate, setAutoRotate] = useState(false)
  // labels start on where there is room beside the figure; on a phone they start off (the list is right below)
  const [labelsOn, setLabelsOn] = useState(() => typeof window === 'undefined' || window.innerWidth >= 480)
  const stateRef = useRef({ levels, selected, marks, autoRotate, labelsOn })
  // decided in the browser after mount (never during render), so a first render without WebGL can't stick
  const [failed, setFailed] = useState(false)
  const leftLabel = sideLabels?.left || 'L'
  const rightLabel = sideLabels?.right || 'R'
  // the render loop reads the latest props from here, so the scene is built once
  useEffect(() => { stateRef.current = { levels, selected, onSelect, marks, autoRotate, labelsOn } })

  useEffect(() => {
    const host = hostRef.current
    if (!host) return undefined
    let renderer
    // Creating the renderer is the WebGL check itself: no separate test canvas that would hold a second context
    try {
      renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true })
    } catch {
      queueMicrotask(() => setFailed(true)) // WebGL refused: show the note; the region list still works
      return undefined
    }
    renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2))
    host.appendChild(renderer.domElement)
    const reduceMotion = window.matchMedia?.('(prefers-reduced-motion: reduce)').matches
    const status = { caution: token('--caution', '#f2c230'), warning: token('--warning', '#f0524a') }
    const paper = new THREE.Color(PAPER)
    const accent = new THREE.Color(ACCENT)

    const scene = new THREE.Scene()
    scene.fog = new THREE.Fog(NAVY, 4.0, 6.5) // the far side of the figure fades a little, like depth on paper
    const camera = new THREE.PerspectiveCamera(28, 1, 0.1, 20)
    camera.position.set(0, 1.0, 4.3)
    camera.lookAt(0, 0.92, 0)
    const figure = new THREE.Group()
    scene.add(figure)

    // Each part: strong edges + faint full wireframe (lines only), and an invisible mesh for clicking
    const hitMaterial = new THREE.MeshBasicMaterial({ colorWrite: false, depthWrite: false })
    const pieces = []
    const disposables = [hitMaterial]
    let heartPiece = null
    for (const part of parts()) {
      const edges = new THREE.EdgesGeometry(part.geo, 15)
      const wire = new THREE.WireframeGeometry(part.geo)
      const main = new THREE.LineBasicMaterial({ transparent: true, depthWrite: false, fog: true })
      const mesh = new THREE.LineBasicMaterial({ transparent: true, depthWrite: false, fog: true })
      const group = new THREE.Group()
      const hit = new THREE.Mesh(part.geo, hitMaterial)
      group.add(new THREE.LineSegments(edges, main), new THREE.LineSegments(wire, mesh), hit)
      group.position.copy(part.pos)
      if (part.quat) group.quaternion.copy(part.quat)
      if (part.rotX) group.rotation.x = part.rotX
      if (part.rotZ) group.rotation.z = part.rotZ
      if (part.scale) group.scale.set(...part.scale)
      figure.add(group)
      hit.userData = { region: part.region, heart: !!part.heart }
      const piece = { region: part.region, group, hit, main, mesh, heart: !!part.heart, baseScale: group.scale.clone() }
      if (part.heart) heartPiece = piece
      pieces.push(piece)
      disposables.push(part.geo, edges, wire, main, mesh)
    }
    const hits = pieces.map((p) => p.hit)

    // The heart's light: a soft glow that beats (the one glow on the sheet)
    const glowMap = glowTexture()
    const glow = new THREE.Sprite(new THREE.SpriteMaterial({ map: glowMap, transparent: true, depthWrite: false, blending: THREE.AdditiveBlending }))
    glow.position.copy(HEART_AT)
    figure.add(glow)
    disposables.push(glowMap, glow.material)

    // L / R beside the shoulders: they turn with the figure, so the sides stay readable from the back too
    for (const [text, x] of [[leftLabel, 0.44], [rightLabel, -0.44]]) {
      const map = letterTexture(text)
      const tag = new THREE.Sprite(new THREE.SpriteMaterial({ map, color: paper, transparent: true, opacity: 0.75, depthWrite: false }))
      tag.position.set(x, 1.5, 0)
      tag.scale.setScalar(0.12)
      figure.add(tag)
      disposables.push(map, tag.material)
    }

    // Symptom-report marks for when the labels are off
    const markMap = letterTexture('!')
    const markSprites = Object.entries(MARK_AT).map(([region, at]) => {
      const s = new THREE.Sprite(new THREE.SpriteMaterial({ map: markMap, transparent: true, depthWrite: false, depthTest: false }))
      s.position.copy(at)
      s.visible = false
      s.userData.region = region
      figure.add(s)
      disposables.push(s.material)
      return s
    })
    disposables.push(markMap)

    // Floor mark: a thin circle with a centre cross, drawn like a datum on the sheet
    const floorPts = []
    for (let i = 0; i <= 96; i++) { const a = (i / 96) * Math.PI * 2; floorPts.push(V(Math.cos(a) * 0.36, 0.004, Math.sin(a) * 0.36)) }
    const floorGeo = new THREE.BufferGeometry().setFromPoints(floorPts)
    const crossGeo = new THREE.BufferGeometry().setFromPoints([V(-0.46, 0.004), V(0.46, 0.004), V(0, 0.004, -0.46), V(0, 0.004, 0.46)])
    const floorMat = new THREE.LineBasicMaterial({ color: PAPER, transparent: true, opacity: 0.35, fog: true })
    scene.add(new THREE.Line(floorGeo, floorMat), new THREE.LineSegments(crossGeo, floorMat))
    disposables.push(floorGeo, crossGeo, floorMat)

    // Size follows the container
    function resize() {
      const { clientWidth: w, clientHeight: h } = host
      if (!w || !h) return
      renderer.setSize(w, h, false)
      camera.aspect = w / h
      camera.updateProjectionMatrix()
    }
    const ro = new ResizeObserver(resize)
    ro.observe(host)
    resize()

    // Pointer: drag turns the figure, a click (little movement) picks the part under it
    const el = renderer.domElement
    const ray = new THREE.Raycaster()
    const ndc = new THREE.Vector2()
    let down = null
    let turn = 0
    let lastDrag = -Infinity
    function hit(ev) {
      const box = el.getBoundingClientRect()
      ndc.set(((ev.clientX - box.left) / box.width) * 2 - 1, -((ev.clientY - box.top) / box.height) * 2 + 1)
      ray.setFromCamera(ndc, camera)
      // intersectObjects returns every part along the ray (front to back), not only the first one, so the heart is
      // in the list even behind the torso: a click over the heart picks the heart, not the torso in front of it.
      const found = ray.intersectObjects(hits, false)
      return (found.find((h) => h.object.userData.heart) ?? found[0])?.object ?? null
    }
    // The canvas captures the pointer on press, so move / release / cancel reach it even outside the canvas
    function onDown(ev) {
      if (down) return // a second finger while one is down: ignored, the first pointer keeps the gesture
      down = { x: ev.clientX, y: ev.clientY, turn, moved: false, id: ev.pointerId }
      try { el.setPointerCapture(ev.pointerId) } catch { /* capture not possible: the cancel handlers still reset */ }
    }
    // only the pointer that started the gesture may move, release or cancel it
    const other = (ev) => down && ev.pointerId !== down.id
    function onCancel(ev) { if (!other(ev)) down = null }
    function onMove(ev) {
      if (other(ev)) return
      if (down) {
        const dx = ev.clientX - down.x
        // any movement past a few pixels (either direction) makes it a drag: releasing then selects nothing
        if (Math.hypot(dx, ev.clientY - down.y) > 4) down.moved = true
        if (down.moved) { turn = down.turn + dx * 0.01; lastDrag = performance.now() }
        return
      }
      el.style.cursor = hit(ev) ? 'pointer' : 'grab'
    }
    function onUp(ev) {
      if (other(ev)) return
      const wasClick = down && !down.moved
      down = null
      if (!wasClick) return
      const part = hit(ev)
      if (part?.userData.region) stateRef.current.onSelect(part.userData.region)
    }
    el.addEventListener('pointerdown', onDown)
    el.addEventListener('pointermove', onMove)
    el.addEventListener('pointerup', onUp)
    el.addEventListener('pointercancel', onCancel)
    el.addEventListener('lostpointercapture', onCancel)
    resetRef.current = () => { turn = 0; lastDrag = -Infinity }

    // Leader labels: project each part's anchor, choose a side, size the leader, spread, then write the SVG
    const projected = new THREE.Vector3()
    const lastSide = {}
    const SILHOUETTE = V(0.42, 0.95, 0) // just outside the shoulders / hands, in world space (does not turn)
    function placeLabels() {
      const w = host.clientWidth
      const h = host.clientHeight
      const maxLeader = Math.min(150, w * 0.2)
      // labels always start outside the body's outline, so a deep part (the heart) never has its name on the chest
      const clear = Math.abs(((SILHOUETTE.clone().project(camera).x + 1) / 2) * w - w / 2)
      const sides = { left: [], right: [] }
      for (const [id, at] of Object.entries(ANCHOR_AT)) {
        const r = labelRefs.current[id]
        if (!r?.text) continue
        projected.copy(at).applyMatrix4(figure.matrixWorld).project(camera)
        const x = ((projected.x + 1) / 2) * w
        const y = ((1 - projected.y) / 2) * h
        let side = lastSide[id] ?? (x < w / 2 ? 'left' : 'right')
        if (x < w * 0.47) side = 'left'
        else if (x > w * 0.53) side = 'right'
        lastSide[id] = side
        const depth = Math.min(1, Math.abs(x - w / 2) / (w * 0.26))
        const leader = 40 + (maxLeader - 40) * depth
        sides[side].push({ id, r, x, y, leader, tw: r.text.getComputedTextLength() })
      }
      for (const [side, items] of Object.entries(sides)) {
        spread(items, h)
        for (const it of items) {
          const left = side === 'left'
          let tick = left ? Math.min(it.x - it.leader, w / 2 - clear) : Math.max(it.x + it.leader, w / 2 + clear)
          tick = left ? Math.max(tick, EDGE + it.tw + TEXT_GAP) : Math.min(tick, w - EDGE - it.tw - TEXT_GAP)
          it.r.g.style.visibility = it.hidden ? 'hidden' : ''
          for (const line of [it.r.line, it.r.hit]) { // the visible leader and its wider click target
            line.setAttribute('x1', it.x)
            line.setAttribute('y1', it.y)
            line.setAttribute('x2', tick)
            line.setAttribute('y2', it.ly)
          }
          it.r.end.setAttribute('cx', it.x)
          it.r.end.setAttribute('cy', it.y)
          it.r.tick.setAttribute('cx', tick)
          it.r.tick.setAttribute('cy', it.ly)
          it.r.text.setAttribute('x', left ? tick - TEXT_GAP : tick + TEXT_GAP)
          it.r.text.setAttribute('y', it.ly + 4)
          it.r.text.setAttribute('text-anchor', left ? 'end' : 'start')
        }
      }
    }

    // Render loop: line colours follow the latest levels and selection without rebuilding the scene
    let frame = 0
    const clock = new THREE.Clock()
    let last = performance.now()
    function draw() {
      const t = reduceMotion ? 0 : clock.getElapsedTime()
      const now = performance.now()
      const dt = Math.min(0.1, (now - last) / 1000)
      last = now
      const { levels: lv, selected: sel, marks: mk, autoRotate: spin, labelsOn: showLabels } = stateRef.current
      // auto-rotate turns the figure all the way round; otherwise a slow sway so it reads as 3D.
      // Both pause for a few seconds after the user turns it by hand.
      const idle = now - lastDrag > 3000
      if (spin && idle && !reduceMotion) turn += dt * 0.4
      figure.rotation.y = turn + (spin || reduceMotion || !idle ? 0 : Math.sin(t * 0.35) * 0.45)
      figure.updateMatrixWorld()
      // heartbeat shape: a short swell about once a second (display only, not the measured rate)
      const beat = reduceMotion ? 0 : Math.pow(Math.max(0, Math.sin(t * Math.PI * 2 * 1.1)), 6)
      for (const p of pieces) {
        const level = lv[p.region]
        const off = level === 'caution' || level === 'warning'
        const on = p.region === sel
        // tone: selected → accent (status colour if off), off → status colour, no sensor → faint, else paper
        p.main.color.copy(off ? status[level] : on ? accent : paper)
        p.mesh.color.copy(p.main.color)
        const pulse = level === 'warning' && !reduceMotion ? 0.75 + 0.25 * Math.sin(t * 5) : 1
        p.main.opacity = (on ? 1 : off ? 0.85 : level === 'none' ? 0.3 : 0.6) * pulse
        p.mesh.opacity = on ? 0.45 : off ? 0.22 : level === 'none' ? 0.04 : 0.1
        if (p.heart) {
          p.main.opacity = Math.max(p.main.opacity, 0.9)
          p.group.scale.copy(p.baseScale).multiplyScalar(1 + 0.09 * beat)
        }
      }
      if (heartPiece) {
        const on = sel === 'heart'
        glow.material.color.copy(heartPiece.main.color)
        glow.material.opacity = Math.min(1, (0.35 + 0.35 * beat) * (on ? 1.3 : 0.8))
        glow.scale.setScalar((on ? 0.36 : 0.26) * (1 + 0.15 * beat))
      }
      for (const s of markSprites) {
        const level = mk?.[s.userData.region]
        s.visible = level != null && !showLabels // with labels on, the "!" is on the label instead
        if (!s.visible) continue
        s.material.color.copy(status[level] ?? paper)
        s.scale.setScalar(0.11 * (1 + (reduceMotion ? 0 : 0.1 * Math.sin(t * 3))))
      }
      renderer.render(scene, camera)
      if (showLabels) placeLabels()
      frame = requestAnimationFrame(draw)
    }
    draw()

    return () => {
      cancelAnimationFrame(frame)
      ro.disconnect()
      el.removeEventListener('pointerdown', onDown)
      el.removeEventListener('pointermove', onMove)
      el.removeEventListener('pointerup', onUp)
      el.removeEventListener('pointercancel', onCancel)
      el.removeEventListener('lostpointercapture', onCancel)
      disposables.forEach((d) => d.dispose())
      renderer.dispose()
      el.remove()
    }
  }, [leftLabel, rightLabel]) // rebuilt only when the language changes the L / R labels

  if (failed) return <p className="panel-empty muted">{unavailableText}</p>
  const STATUS_ICON = { caution: '▲', warning: '✖' }
  return (
    <div className="body-figure holo" role="group" aria-label={label}>
      <div ref={hostRef} className="holo-canvas" />
      {labelsOn && (
        <svg className="holo-labels">
          {callouts.map((c) => {
            // the render loop positions these elements directly every frame (no React state per frame)
            const keep = (key) => (el) => { (labelRefs.current[c.id] ??= {})[key] = el }
            const select = () => onSelect(c.id)
            return (
              <g key={c.id} ref={keep('g')} className={`holo-label lv-${c.level}${c.id === selected ? ' on' : ''}`}
                role="button" tabIndex={0} aria-pressed={c.id === selected} aria-label={c.text}
                onClick={select} onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); select() } }}>
                <line ref={keep('line')} className="holo-leader" />
                <line ref={keep('hit')} className="holo-leader-hit" />
                <circle ref={keep('end')} className="holo-end" r="2" cx="-9" cy="-9" />
                <circle ref={keep('tick')} className="holo-tick" r="1.6" cx="-9" cy="-9" />
                <text ref={keep('text')} className="holo-text" x="-999" y="-999">
                  {c.text}
                  {STATUS_ICON[c.level] && <tspan className="holo-status"> {STATUS_ICON[c.level]}</tspan>}
                  {c.reported && <tspan className="holo-mark"> !</tspan>}
                </text>
              </g>
            )
          })}
        </svg>
      )}
      <div className="holo-controls">
        <button type="button" aria-pressed={autoRotate} onClick={() => setAutoRotate((v) => !v)}>{texts.rotate ?? 'Auto-rotate'}</button>
        <button type="button" aria-pressed={labelsOn} onClick={() => setLabelsOn((v) => !v)}>{texts.labels ?? 'Labels'}</button>
        <button type="button" onClick={() => resetRef.current()}>{texts.reset ?? 'Reset view'}</button>
      </div>
    </div>
  )
}
