// HoloBody.jsx — the body as a 3D hologram (spec §7-2, Body screen). A simple figure built from rounded shapes,
// drawn with a glowing-edge "hologram" shader: rim light, moving scan lines, a faint wireframe and a projector
// ring under the feet. Each part carries its region; caution and warning parts pulse. Colours come from the CSS
// tokens and from the levels the page passes in: the figure decides nothing.
// Click a part to select its region (the right arm has no sensor: onNoSensor). Drag to turn the figure.
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

// Body parts: [region (null = no sensor), geometry, position, rotation z, scale]. Units ≈ metres, feet at y 0,
// the figure faces the camera (+z), so the person's left is on the viewer's right (+x).
function parts() {
  const capsule = (r, len) => new THREE.CapsuleGeometry(r, len, 8, 24)
  // Torso as one continuous outline (shoulders → waist → hips), cut in two at y 1.12: chest above, abdomen below.
  // [radius, y] from bottom to top, turned around the body axis and flattened front-to-back.
  const lathe = (pts) => new THREE.LatheGeometry(pts.map(([r, y]) => new THREE.Vector2(r, y)), 40)
  const chest = lathe([[0, 1.12], [0.142, 1.12], [0.152, 1.2], [0.175, 1.32], [0.2, 1.41], [0.185, 1.46], [0.1, 1.5], [0, 1.51]])
  const belly = lathe([[0, 0.8], [0.15, 0.8], [0.165, 0.86], [0.15, 0.97], [0.138, 1.05], [0.142, 1.12], [0, 1.12]])
  const flat = [1, 1, 0.62]
  return [
    ['head', new THREE.SphereGeometry(0.12, 32, 24), [0, 1.64, 0], 0, [0.88, 1.08, 0.95]],
    ['head', new THREE.CylinderGeometry(0.05, 0.055, 0.1, 20), [0, 1.52, 0], 0, [1, 1, 1]],
    ['heart', chest, [0, 0, 0], 0, flat],
    ['core', belly, [0, 0, 0], 0, flat],
    // arms hang just clear of the torso (a small gap at the shoulder) and tilt slightly outwards
    [null, capsule(0.045, 0.56), [-0.28, 1.13, 0], -0.1, [1, 1, 1]], // right arm (viewer's left): no sensor
    ['wrist', capsule(0.045, 0.56), [0.28, 1.13, 0], 0.1, [1, 1, 1]], // left arm, EDA band on the wrist
    ['wrist', new THREE.TorusGeometry(0.055, 0.012, 10, 32), [0.304, 0.89, 0], 0.1, [1, 1, 1]], // the band
    ['legs', capsule(0.065, 0.62), [-0.1, 0.42, 0], 0, [1, 1, 1]],
    ['legs', capsule(0.065, 0.62), [0.1, 0.42, 0], 0, [1, 1, 1]],
  ]
}

function webglAvailable() {
  try {
    const c = document.createElement('canvas')
    return !!(c.getContext('webgl2') || c.getContext('webgl'))
  } catch {
    return false
  }
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

export default function HoloBody({ levels, selected, onSelect, onNoSensor, label, unavailableText }) {
  const hostRef = useRef(null)
  const stateRef = useRef({ levels, selected, onSelect, onNoSensor })
  const [failed, setFailed] = useState(() => !webglAvailable())
  // the render loop reads the latest props from here, so the scene is built once
  useEffect(() => { stateRef.current = { levels, selected, onSelect, onNoSensor } })

  useEffect(() => {
    const host = hostRef.current
    if (!host) return undefined
    let renderer
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
    for (const [region, geometry, pos, rotZ, scale] of parts()) {
      const material = new THREE.ShaderMaterial({
        vertexShader: VERT, fragmentShader: FRAG, transparent: true, depthWrite: false,
        blending: THREE.AdditiveBlending,
        uniforms: { uColor: { value: new THREE.Color() }, uTime: { value: 0 }, uBoost: { value: 1 }, uPulse: { value: 0 } },
      })
      const wire = new THREE.MeshBasicMaterial({ wireframe: true, transparent: true, depthWrite: false, blending: THREE.AdditiveBlending })
      const mesh = new THREE.Mesh(geometry, material)
      const lines = new THREE.Mesh(geometry, wire)
      for (const m of [mesh, lines]) {
        m.position.set(...pos)
        m.rotation.z = rotZ
        m.scale.set(...scale)
        figure.add(m)
      }
      mesh.userData = { region, wire }
      meshes.push(mesh)
      disposables.push(geometry, material, wire)
    }

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
    const ray = new THREE.Raycaster()
    const ndc = new THREE.Vector2()
    let down = null
    let turn = 0
    let lastDrag = -Infinity
    function hit(ev) {
      const box = renderer.domElement.getBoundingClientRect()
      ndc.set(((ev.clientX - box.left) / box.width) * 2 - 1, -((ev.clientY - box.top) / box.height) * 2 + 1)
      ray.setFromCamera(ndc, camera)
      return ray.intersectObjects(meshes, false)[0]?.object ?? null
    }
    function onDown(ev) { down = { x: ev.clientX, y: ev.clientY, turn, moved: false } }
    function onMove(ev) {
      if (down) {
        const dx = ev.clientX - down.x
        if (Math.abs(dx) > 4) down.moved = true
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
      if (!part) return
      const { onSelect: select, onNoSensor: noSensor } = stateRef.current
      if (part.userData.region) select(part.userData.region)
      else noSensor?.()
    }
    const el = renderer.domElement
    el.addEventListener('pointerdown', onDown)
    window.addEventListener('pointermove', onMove)
    window.addEventListener('pointerup', onUp)

    // Render loop: uniforms follow the latest levels and selection without rebuilding the scene
    let frame = 0
    const clock = new THREE.Clock()
    function draw() {
      const t = reduceMotion ? 0 : clock.getElapsedTime()
      const { levels: lv, selected: sel } = stateRef.current
      // a slow sway so the figure reads as 3D; paused for a few seconds after the user turns it
      const idle = performance.now() - lastDrag > 3000
      figure.rotation.y = turn + (reduceMotion || !idle ? 0 : Math.sin(t * 0.35) * 0.45)
      for (const mesh of meshes) {
        const { region, wire } = mesh.userData
        const l = region ? (looks[lv[region]] ?? looks.plain) : looks.none
        const on = region && region === sel
        const u = mesh.material.uniforms
        u.uColor.value.copy(l.color)
        u.uTime.value = t
        u.uBoost.value = l.boost * (on ? 1.5 : 1)
        u.uPulse.value = reduceMotion ? 0 : l.pulse
        wire.color.copy(l.color)
        wire.opacity = on ? 0.32 : 0.1
      }
      renderer.render(scene, camera)
      frame = requestAnimationFrame(draw)
    }
    draw()

    return () => {
      cancelAnimationFrame(frame)
      ro.disconnect()
      el.removeEventListener('pointerdown', onDown)
      window.removeEventListener('pointermove', onMove)
      window.removeEventListener('pointerup', onUp)
      disposables.forEach((d) => d.dispose())
      renderer.dispose()
      el.remove()
    }
  }, [])

  if (failed) return <p className="panel-empty muted">{unavailableText}</p>
  return <div ref={hostRef} className="body-figure holo" role="img" aria-label={label} />
}
