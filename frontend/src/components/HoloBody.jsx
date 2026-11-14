// HoloBody.jsx — the body as a 3D hologram (spec §7-2, Body screen). A simple figure built from rounded shapes,
// drawn with a glowing-edge "hologram" shader: rim light, moving scan lines, a faint wireframe and a projector
// ring under the feet. Each part carries its region; caution and warning parts pulse. Colours come from the CSS
// tokens and from the levels the page passes in: the figure decides nothing.
// Click a part to select its region (each arm and each leg on its own). Drag to turn the figure.
// Parts a symptom report points at get a ringed "!" mark (marks prop); the right arm has no sensor ('none').
import { useEffect, useRef, useState } from 'react'
import * as THREE from 'three'

const VERT = /* glsl */ `
  varying vec3 vN;
  varying vec3 vView;
  varying float vY;
  void main() {
    vec4 world = modelMatrix * vec4(position, 1.0);
    vY = world.y;
    vec4 mv = viewMatrix * world;
    vView = normalize(-mv.xyz);
    vN = normalize(normalMatrix * normal);
    gl_Position = projectionMatrix * mv;
  }
`
const FRAG = /* glsl */ `
  uniform vec3 uColor;
  uniform float uTime;
  uniform float uBoost;
  uniform float uPulse;
  varying vec3 vN;
  varying vec3 vView;
  varying float vY;
  void main() {
    float rim = pow(1.0 - abs(dot(normalize(vN), normalize(vView))), 2.2);
    float scan = 0.6 + 0.4 * step(0.5, fract(vY * 70.0 - uTime * 0.5));
    float pulse = 1.0 + uPulse * 0.45 * sin(uTime * (2.5 + uPulse * 2.5));
    float alpha = (0.08 + rim * 0.85) * scan * uBoost * pulse;
    gl_FragColor = vec4(uColor * (0.55 + rim * 1.3) * uBoost, alpha);
  }
`

const V = (x, y, z = 0) => new THREE.Vector3(x, y, z)
const DOWN = V(0, -1, 0)
const HEART_AT = V(0.035, 1.3, 0.02) // inside the chest, a little to the person's left

// A tapered limb segment from a to b (radius r1 at a, r2 at b) with rounded ends: a lathe turned to point a → b
function segment(a, b, r1, r2) {
  const dir = b.clone().sub(a)
  const len = dir.length()
  const pts = []
  for (let k = 0; k <= 6; k++) { const t = (k / 6) * (Math.PI / 2); pts.push(new THREE.Vector2(r1 * Math.sin(t), r1 * Math.cos(t))) }
  for (let k = 0; k <= 6; k++) { const t = (k / 6) * (Math.PI / 2); pts.push(new THREE.Vector2(r2 * Math.cos(t), -len - r2 * Math.sin(t))) }
  return { geo: new THREE.LatheGeometry(pts.reverse(), 20), quat: new THREE.Quaternion().setFromUnitVectors(DOWN, dir.normalize()) }
}

// Body parts: { region (null = no sensor), geo, pos, quat | rotX | rotZ, scale }. Units ≈ metres, feet at y 0,
// the figure faces the camera (+z), so the person's left is on the viewer's right (+x).
function parts() {
  const lathe = (pts, seg = 40) => new THREE.LatheGeometry(pts.map(([r, y]) => new THREE.Vector2(r, y)), seg)
  const out = []
  const add = (region, geo, pos, extra = {}) => out.push({ region, geo, pos, ...extra })
  const limb = (region, a, b, r1, r2) => { const s = segment(a, b, r1, r2); add(region, s.geo, a, { quat: s.quat }) }

  // Head, with a nose so the face (the front) is clear when the figure turns
  add('head', new THREE.SphereGeometry(0.115, 32, 24), V(0, 1.635), { scale: [0.86, 1.1, 0.98] })
  add('head', new THREE.ConeGeometry(0.018, 0.045, 12), V(0, 1.615, 0.112), { rotX: Math.PI / 2 })
  limb('head', V(0, 1.54), V(0, 1.47), 0.048, 0.054) // neck
  // Torso in one piece (shoulders → chest → waist → hips), flattened front to back: Torso · Temperature
  add('core', lathe([[0, 0.78], [0.13, 0.78], [0.158, 0.84], [0.162, 0.9], [0.145, 0.99], [0.138, 1.06], [0.15, 1.16],
    [0.172, 1.28], [0.195, 1.38], [0.2, 1.42], [0.18, 1.47], [0.09, 1.5], [0, 1.505]]), V(0, 0), { scale: [1, 1, 0.6] })
  // Heart inside the chest, apex pointing down to the person's left: Heart · Circulation
  add('heart', lathe([[0, -0.07], [0.02, -0.05], [0.042, -0.02], [0.056, 0.012], [0.054, 0.042], [0.034, 0.064], [0, 0.07]], 28),
    HEART_AT, { rotZ: 0.45, scale: [1, 1, 0.85], heart: true })
  for (const side of [-1, 1]) { // −1: the person's right (viewer's left), +1: the person's left
    const sx = (v) => v * side
    const arm = side > 0 ? 'left_arm' : 'right_arm' // the EDA band is on the left wrist; the right arm has no sensor
    const leg = side > 0 ? 'left_leg' : 'right_leg'
    add(arm, new THREE.SphereGeometry(0.05, 20, 14), V(sx(0.235), 1.44)) // shoulder
    limb(arm, V(sx(0.25), 1.41), V(sx(0.285), 1.15), 0.046, 0.038) // upper arm
    limb(arm, V(sx(0.285), 1.15), V(sx(0.31), 0.92), 0.038, 0.03) // forearm
    add(arm, new THREE.SphereGeometry(0.045, 16, 12), V(sx(0.315), 0.85, 0.01), { scale: [0.62, 1.2, 0.42] }) // hand
    limb(leg, V(sx(0.095), 0.82), V(sx(0.09), 0.47), 0.075, 0.052) // thigh
    limb(leg, V(sx(0.09), 0.47), V(sx(0.085), 0.08), 0.052, 0.036) // calf
    limb(leg, V(sx(0.085), 0.045, -0.02), V(sx(0.092), 0.035, 0.12), 0.036, 0.03) // foot, toes forward
  }
  add('left_arm', new THREE.TorusGeometry(0.038, 0.01, 10, 32), V(0.306, 0.95), { rotX: Math.PI / 2 }) // EDA band
  return out
}

// Where each callout line starts (a point on the part), in figure coordinates
const ANCHOR_AT = {
  head: V(0, 1.66, 0.1),
  heart: HEART_AT,
  core: V(0, 1.0, 0.1),
  left_arm: V(0.3, 1.02, 0.03),
  right_arm: V(-0.3, 1.02, 0.03),
  left_leg: V(0.09, 0.47, 0.05),
  right_leg: V(-0.09, 0.47, 0.05),
}

// Where a symptom-report mark (!) floats for each region: just in front of / beside the part
const MARK_AT = {
  head: V(0, 1.8, 0.05),
  heart: V(0.115, 1.18, 0.16), // in front of the chest, just below the heart's glow and clear of the shoulder
  core: V(0, 1.0, 0.13),
  left_arm: V(0.4, 1.1, 0.04),
  right_arm: V(-0.4, 1.1, 0.04),
  left_leg: V(0.2, 0.5, 0.06),
  right_leg: V(-0.2, 0.5, 0.06),
}

// A soft round glow (for the heart) and a letter label (L / R), drawn once on small canvases
function glowTexture() {
  const c = document.createElement('canvas')
  c.width = c.height = 128
  const g = c.getContext('2d')
  const grad = g.createRadialGradient(64, 64, 0, 64, 64, 64)
  grad.addColorStop(0, 'rgba(255,255,255,1)')
  grad.addColorStop(0.25, 'rgba(255,255,255,0.55)')
  grad.addColorStop(1, 'rgba(255,255,255,0)')
  g.fillStyle = grad
  g.fillRect(0, 0, 128, 128)
  return new THREE.CanvasTexture(c)
}
function letterTexture(text) {
  const c = document.createElement('canvas')
  c.width = c.height = 128
  const g = c.getContext('2d')
  g.strokeStyle = 'rgba(255,255,255,0.7)'
  g.lineWidth = 5
  g.beginPath()
  g.arc(64, 64, 54, 0, Math.PI * 2)
  g.stroke()
  g.fillStyle = '#fff'
  g.font = `600 ${text.length > 1 ? 44 : 64}px "IBM Plex Mono", "IBM Plex Sans KR", monospace`
  g.textAlign = 'center'
  g.textBaseline = 'middle'
  g.fillText(text, 64, 68)
  return new THREE.CanvasTexture(c)
}

function token(name, fallback) {
  const v = getComputedStyle(document.documentElement).getPropertyValue(name).trim()
  return new THREE.Color(v || fallback)
}

// How each level looks: colour token, brightness, pulse. Read from the CSS tokens once per mount.
function palette() {
  return {
    warning: { color: token('--warning', '#f0524a'), boost: 1.25, pulse: 1 },
    caution: { color: token('--caution', '#f2c230'), boost: 1.15, pulse: 0.55 },
    hold: { color: token('--hold', '#c9d2dc'), boost: 0.6, pulse: 0 },
    plain: { color: token('--accent', '#5cc8e0'), boost: 0.9, pulse: 0 }, // normal, advisory (no colour of its own)
    none: { color: token('--muted', '#8a98a9'), boost: 0.45, pulse: 0 }, // no sensor
  }
}

// Callout layout: labels sit in a column at each side, at the height of their part, spread apart so they never
// overlap; a line runs from the label to a dot on the part. Recomputed every frame as the figure turns.
const CALLOUT_GAP = 30
const CALLOUT_EDGE = 10
function layoutSide(items, h) {
  items.sort((a, b) => a.y - b.y)
  let prev = -Infinity
  for (const it of items) { it.ly = Math.max(it.y, prev + CALLOUT_GAP, 56); prev = it.ly } // 56: below the buttons
  let next = h - 16 // push back up if the column ran off the bottom
  for (let i = items.length - 1; i >= 0; i--) { items[i].ly = Math.min(items[i].ly, next); next = items[i].ly - CALLOUT_GAP }
}

// marks: { [regionId]: level } — regions a symptom report points at, coloured by that report's level
// callouts: [{ id, text, level, reported }] — the labels drawn beside the figure (blueprint style)
// texts: { rotate, labels, reset } — the control button words
export default function HoloBody({ levels, selected, onSelect, marks, callouts = [], texts = {}, label, unavailableText, sideLabels }) {
  const hostRef = useRef(null)
  const lineRefs = useRef({})
  const labelRefs = useRef({})
  const resetRef = useRef(() => {})
  const [autoRotate, setAutoRotate] = useState(false)
  // labels start on where there is room beside the figure; on a phone they start off (the list is right below)
  const [labelsOn, setLabelsOn] = useState(() => typeof window === 'undefined' || window.innerWidth >= 480)
  const stateRef = useRef({ levels, selected, onSelect, marks, autoRotate, labelsOn })
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
      queueMicrotask(() => setFailed(true)) // WebGL refused after all: show the note; the region list still works
      return undefined
    }
    renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2))
    host.appendChild(renderer.domElement)
    const reduceMotion = window.matchMedia?.('(prefers-reduced-motion: reduce)').matches
    const looks = palette()

    const scene = new THREE.Scene()
    const camera = new THREE.PerspectiveCamera(28, 1, 0.1, 20)
    camera.position.set(0, 1.0, 4.3)
    camera.lookAt(0, 0.92, 0)
    const figure = new THREE.Group()
    scene.add(figure)

    const meshes = []
    const disposables = []
    let heartMesh = null
    for (const part of parts()) {
      const material = new THREE.ShaderMaterial({
        vertexShader: VERT, fragmentShader: FRAG, transparent: true, depthWrite: false,
        blending: THREE.AdditiveBlending, side: THREE.DoubleSide,
        uniforms: { uColor: { value: new THREE.Color() }, uTime: { value: 0 }, uBoost: { value: 1 }, uPulse: { value: 0 } },
      })
      const wire = new THREE.MeshBasicMaterial({ wireframe: true, transparent: true, depthWrite: false, blending: THREE.AdditiveBlending })
      const mesh = new THREE.Mesh(part.geo, material)
      const lines = new THREE.Mesh(part.geo, wire)
      for (const m of [mesh, lines]) {
        m.position.copy(part.pos)
        if (part.quat) m.quaternion.copy(part.quat)
        if (part.rotX) m.rotation.x = part.rotX
        if (part.rotZ) m.rotation.z = part.rotZ
        if (part.scale) m.scale.set(...part.scale)
        figure.add(m)
      }
      mesh.userData = { region: part.region, wire, lines, heart: !!part.heart, baseScale: mesh.scale.clone() }
      if (part.heart) heartMesh = mesh
      meshes.push(mesh)
      disposables.push(part.geo, material, wire)
    }

    // The heart's light: a soft glow around it that beats
    const glowMap = glowTexture()
    const glow = new THREE.Sprite(new THREE.SpriteMaterial({ map: glowMap, transparent: true, depthWrite: false, blending: THREE.AdditiveBlending }))
    glow.position.copy(HEART_AT)
    figure.add(glow)
    disposables.push(glowMap, glow.material)

    // L / R beside the shoulders: they turn with the figure, so the sides stay readable from the back too
    for (const [text, x] of [[leftLabel, 0.44], [rightLabel, -0.44]]) {
      const map = letterTexture(text)
      const tag = new THREE.Sprite(new THREE.SpriteMaterial({ map, color: looks.plain.color, transparent: true, opacity: 0.9, depthWrite: false }))
      tag.position.set(x, 1.5, 0)
      tag.scale.setScalar(0.13)
      figure.add(tag)
      disposables.push(map, tag.material)
    }

    // Symptom-report marks: a ringed "!" beside each part a report points at (hidden until there is one).
    // A different shape from the part's own glow, so "measured" and "reported" are never confused.
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

    // Projector under the feet: two thin rings and a faint disc
    const accent = looks.plain.color
    const base = [
      [new THREE.RingGeometry(0.3, 0.315, 96), 0.7],
      [new THREE.RingGeometry(0.42, 0.425, 96), 0.3],
      [new THREE.CircleGeometry(0.3, 64), 0.08],
    ]
    for (const [geometry, opacity] of base) {
      const material = new THREE.MeshBasicMaterial({ color: accent, transparent: true, opacity, depthWrite: false, blending: THREE.AdditiveBlending, side: THREE.DoubleSide })
      const ring = new THREE.Mesh(geometry, material)
      ring.rotation.x = -Math.PI / 2
      ring.position.y = 0.005
      scene.add(ring)
      disposables.push(geometry, material)
    }

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
      const box = renderer.domElement.getBoundingClientRect()
      ndc.set(((ev.clientX - box.left) / box.width) * 2 - 1, -((ev.clientY - box.top) / box.height) * 2 + 1)
      ray.setFromCamera(ndc, camera)
      // intersectObjects returns every part along the ray (front to back), not only the first one, so the heart is
      // in the list even behind the torso. The heart sits inside the see-through torso: a click over it picks the
      // heart, not the torso in front of it.
      const hits = ray.intersectObjects(meshes, false)
      return (hits.find((h) => h.object.userData.heart) ?? hits[0])?.object ?? null
    }
    // The canvas captures the pointer on press, so move / release / cancel reach it even outside the canvas
    function onDown(ev) {
      down = { x: ev.clientX, y: ev.clientY, turn, moved: false, id: ev.pointerId }
      try { el.setPointerCapture(ev.pointerId) } catch { /* capture not possible: the cancel handlers still reset */ }
    }
    function onCancel() { down = null }
    function onMove(ev) {
      if (down) {
        const dx = ev.clientX - down.x
        // any movement past a few pixels (either direction) makes it a drag: releasing then selects nothing
        if (Math.hypot(dx, ev.clientY - down.y) > 4) down.moved = true
        if (down.moved) { turn = down.turn + dx * 0.01; lastDrag = performance.now() }
        return
      }
      renderer.domElement.style.cursor = hit(ev) ? 'pointer' : 'grab'
    }
    function onUp(ev) {
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

    // Callouts: project each part's anchor to the screen, lay the labels out per side, draw the lines
    const projected = new THREE.Vector3()
    function placeCallouts() {
      const w = host.clientWidth
      const h = host.clientHeight
      const sides = { left: [], right: [] }
      for (const [id, at] of Object.entries(ANCHOR_AT)) {
        const box = labelRefs.current[id]
        const line = lineRefs.current[id]
        if (!box || !line) continue
        projected.copy(at).applyMatrix4(figure.matrixWorld).project(camera)
        const x = ((projected.x + 1) / 2) * w
        const y = ((1 - projected.y) / 2) * h
        // a label goes to the side of the screen its part is on right now (so it follows the figure round)
        sides[x < w / 2 ? 'left' : 'right'].push({ id, x, y, box, line, bw: box.offsetWidth, bh: box.offsetHeight })
      }
      for (const [side, items] of Object.entries(sides)) {
        layoutSide(items, h)
        for (const it of items) {
          const lx = side === 'left' ? CALLOUT_EDGE : w - CALLOUT_EDGE - it.bw
          const end = side === 'left' ? lx + it.bw + 4 : lx - 4
          it.box.style.transform = `translate(${lx}px, ${it.ly - it.bh / 2}px)`
          it.line.setAttribute('points', `${end},${it.ly} ${(end + it.x) / 2},${it.ly} ${it.x},${it.y}`)
          it.line.nextSibling?.setAttribute('cx', it.x)
          it.line.nextSibling?.setAttribute('cy', it.y)
        }
      }
    }

    // Render loop: uniforms follow the latest levels and selection without rebuilding the scene
    let frame = 0
    const clock = new THREE.Clock()
    let last = performance.now()
    function draw() {
      const t = reduceMotion ? 0 : clock.getElapsedTime()
      const now = performance.now()
      const dt = Math.min(0.1, (now - last) / 1000)
      last = now
      const { levels: lv, selected: sel, autoRotate: spin, labelsOn: showLabels } = stateRef.current
      // auto-rotate turns the figure all the way round; otherwise a slow sway so it reads as 3D.
      // Both pause for a few seconds after the user turns it by hand.
      const idle = now - lastDrag > 3000
      if (spin && idle && !reduceMotion) turn += dt * 0.4
      figure.rotation.y = turn + (spin || reduceMotion || !idle ? 0 : Math.sin(t * 0.35) * 0.45)
      figure.updateMatrixWorld()
      // heartbeat shape: a short swell about once a second (display only, not the measured rate)
      const beat = reduceMotion ? 0 : Math.pow(Math.max(0, Math.sin(t * Math.PI * 2 * 1.1)), 6)
      for (const mesh of meshes) {
        const { region, wire, heart, baseScale } = mesh.userData
        const l = region ? (looks[lv[region]] ?? looks.plain) : looks.none
        const on = region && region === sel
        const u = mesh.material.uniforms
        u.uColor.value.copy(l.color)
        u.uTime.value = t
        // the heart is a lit organ: always brighter than the shell around it, brightest when selected
        u.uBoost.value = l.boost * (on ? 1.5 : 1) * (heart ? 1.8 : 1)
        u.uPulse.value = reduceMotion ? 0 : l.pulse
        wire.color.copy(l.color)
        wire.opacity = on ? 0.32 : 0.1
        if (heart) {
          const s = 1 + 0.09 * beat
          mesh.scale.copy(baseScale).multiplyScalar(s)
          mesh.userData.lines.scale.copy(mesh.scale)
        }
      }
      const { marks: mk } = stateRef.current
      for (const s of markSprites) {
        const level = mk?.[s.userData.region]
        s.visible = level != null && !showLabels // with labels on, the "!" is on the label instead
        if (!s.visible) continue
        s.material.color.copy((looks[level] ?? looks.plain).color)
        s.scale.setScalar(0.12 * (1 + (reduceMotion ? 0 : 0.12 * Math.sin(t * 3))))
      }
      if (heartMesh) {
        const l = looks[lv.heart] ?? looks.plain
        const heartOn = sel === 'heart'
        glow.material.color.copy(l.color)
        glow.material.opacity = Math.min(1, (0.5 + 0.4 * beat) * (heartOn ? 1.25 : 0.75))
        glow.scale.setScalar((heartOn ? 0.46 : 0.32) * (1 + 0.15 * beat))
      }
      renderer.render(scene, camera)
      if (showLabels) placeCallouts()
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
  return (
    <div className="body-figure holo" role="group" aria-label={label}>
      <div ref={hostRef} className="holo-canvas" />
      {labelsOn && (
        <>
          <svg className="holo-lines" aria-hidden="true">
            {callouts.map((c) => (
              <g key={c.id} className={`lv-${c.level}${c.id === selected ? ' on' : ''}`}>
                <polyline ref={(el) => { lineRefs.current[c.id] = el }} points="" />
                <circle r="2.5" cx="-10" cy="-10" />
              </g>
            ))}
          </svg>
          {callouts.map((c) => (
            <button key={c.id} type="button" ref={(el) => { labelRefs.current[c.id] = el }}
              className={`holo-callout lv-${c.level}${c.id === selected ? ' on' : ''}`}
              aria-pressed={c.id === selected} onClick={() => onSelect(c.id)}>
              <span className="holo-callout-name">{c.text}</span>
              {c.reported && <span className="holo-callout-mark" aria-hidden="true">!</span>}
            </button>
          ))}
        </>
      )}
      <div className="holo-controls">
        <button type="button" aria-pressed={autoRotate} onClick={() => setAutoRotate((v) => !v)}>{texts.rotate ?? 'Auto-rotate'}</button>
        <button type="button" aria-pressed={labelsOn} onClick={() => setLabelsOn((v) => !v)}>{texts.labels ?? 'Labels'}</button>
        <button type="button" onClick={() => resetRef.current()}>{texts.reset ?? 'Reset'}</button>
      </div>
    </div>
  )
}
