import * as THREE from "./vendor/three.module.min.js";
import { OrbitControls } from "./vendor/OrbitControls.js";

const stage = document.querySelector("#wall");
const scene = new THREE.Scene();
scene.background = new THREE.Color("#0d1014");
scene.fog = new THREE.Fog("#0d1014", 10, 22);
const camera = new THREE.PerspectiveCamera(38, 1, .1, 40);
camera.position.set(5.9, 2.8, 8.8);
const renderer = new THREE.WebGLRenderer({ antialias: true, preserveDrawingBuffer: true });
renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
renderer.outputColorSpace = THREE.SRGBColorSpace;
renderer.shadowMap.enabled = true;
renderer.shadowMap.type = THREE.PCFSoftShadowMap;
stage.prepend(renderer.domElement);
const controls = new OrbitControls(camera, renderer.domElement);
controls.enableDamping = true;
controls.dampingFactor = .06;
controls.minDistance = 4;
controls.maxDistance = 15;
controls.target.set(0, 0, 0);
controls.autoRotate = true;
controls.autoRotateSpeed = .35;

const sculptureRoot = new THREE.Group();
const connections = new THREE.Group();
const micelle = new THREE.Group();
const structure = new THREE.Group();
const matter = new THREE.Group();
const residue = new THREE.Group();
const granular = new THREE.Group();
sculptureRoot.add(connections, micelle, structure, matter, residue, granular);
scene.add(sculptureRoot);
scene.add(new THREE.HemisphereLight("#dceaff", "#11151c", 1.35));
const key = new THREE.DirectionalLight("#ffd7b0", 2.5);
key.position.set(4, 7, 6); key.castShadow = true; scene.add(key);
const rim = new THREE.DirectionalLight("#5ca9ff", 3.1);
rim.position.set(-6, 2, -4); scene.add(rim);
const floor = new THREE.Mesh(new THREE.CircleGeometry(5.6, 64), new THREE.MeshBasicMaterial({ color: "#12161b", transparent: true, opacity: .72 }));
floor.rotation.x = -Math.PI / 2; floor.position.y = -3.15; scene.add(floor);
const shadow = new THREE.Mesh(new THREE.CircleGeometry(2.8, 64), new THREE.MeshBasicMaterial({ color: "#020305", transparent: true, opacity: .54, depthWrite: false }));
shadow.rotation.x = -Math.PI / 2; shadow.position.y = -3.12; shadow.scale.set(1.3, .48, 1); scene.add(shadow);
function resize() { const r = stage.getBoundingClientRect(); renderer.setSize(r.width, r.height, false); camera.aspect = r.width / r.height; camera.updateProjectionMatrix(); }
addEventListener("resize", resize); resize();

let audioContext = null, audioBuffer = null, source = null;
let events = [], granularEnvelope = [], breathEnvelope = [], seed = 1337, baseSeed = 1337;
let playing = false, playGeneration = 0, currentTrack = "chopin", revealedIndex = 0, impulseIndex = 0, playStartedAt = 0;
let pianoMode = false, pianoTime = 0, pianoLastFrame = performance.now() / 1000, pianoLastEvent = null;
const pianoVoices = new Map();
const pianoNotes = [["C4",261.63,"a",false],["C#4",277.18,"w",true],["D4",293.66,"s",false],["D#4",311.13,"e",true],["E4",329.63,"d",false],["F4",349.23,"f",false],["F#4",369.99,"t",true],["G4",392,"g",false],["G#4",415.3,"y",true],["A4",440,"h",false],["A#4",466.16,"u",true],["B4",493.88,"j",false],["C5",523.25,"k",false],["C#5",554.37,"o",true],["D5",587.33,"l",false],["D#5",622.25,"p",true],["E5",659.25,";",false]];
let rotationMode = "music", userRotationSpeed = .35, visualMode = "mycelium";
const myceliumPalette = ["#e9784f", "#f1b55b", "#76a8d9", "#ae7bc5", "#d85e72"];
const treePalette = ["#3f5140", "#687653", "#8b744f", "#a8754f", "#b89a5c", "#3f6864"];
function resizeObserver() { resize(); }
function random() { seed = (seed * 1664525 + 1013904223) >>> 0; return seed / 4294967296; }
function stableHash(value) { let hash = 2166136261; for (const char of String(value)) hash = Math.imul(hash ^ char.charCodeAt(0), 16777619); return hash >>> 0; }
function noteName(m) { const n = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]; return n[((m % 12) + 12) % 12] + (Math.floor(m / 12) - 1); }
function timeLabel(s) { return `${Math.floor(s / 60)}:${String(Math.floor(s % 60)).padStart(2, "0")}`; }
function colorFor(e) { const palette = visualMode === "tree" ? treePalette : myceliumPalette; const c = new THREE.Color(palette[Math.floor((e.brightness * 4.99 + e.pitch) % palette.length)]); c.offsetHSL((e.brightness - .5) * .06, 0, (e.energy - .5) * .08); return c; }
function enterPianoMode() { if (!pianoMode) { ++playGeneration; source?.stop(); playing = false; clearSculpture(); events = []; granularEnvelope = []; breathEnvelope = []; pianoTime = 0; pianoLastEvent = null; pianoMode = true; currentTrack = "piano"; seed = baseSeed; document.querySelector("#fileName").textContent = "Piano ao vivo"; document.querySelector("#eventCount").textContent = "0"; document.querySelector("#playButton").disabled = true; document.querySelector("#pngButton").disabled = false; document.querySelector("#jsonButton").disabled = false; document.querySelector("#status").textContent = "Toque o piano para construir a escultura…"; } }
function buildPiano() { const piano = document.querySelector("#piano"); for (const [name, frequency, key, black] of pianoNotes) { const button = document.createElement("button"); button.className = `key ${black ? "black" : "white"}`; button.dataset.key = key; button.setAttribute("aria-label", `${name} tecla ${key}`); button.innerHTML = `<span class="key-label">${key.toUpperCase()}</span>`; button.addEventListener("pointerdown", event => { event.preventDefault(); noteOn(name, frequency, button); }); button.addEventListener("pointerup", () => noteOff(name)); button.addEventListener("pointerleave", () => { if (pianoVoices.has(name)) noteOff(name); }); piano.append(button); } }
function liveMotifMeta(next) { const sequence = [...events.slice(-3), next]; if (sequence.length < 4) return { motifId: "free", motifOccurrence: 0, motifPhase: 0, motifStrength: 0 }; const signature = motifSignature(sequence); for (let start = 0; start <= events.length - 4; start++) { if (motifSignature(events.slice(start, start + 4)) !== signature) continue; const motifId = `live-${stableHash(signature) % 997}`; const occurrence = (events[start].motifOccurrence || 0) + 1; sequence.forEach((item, index) => { item.motifId = motifId; item.motifOccurrence = occurrence; item.motifPhase = index; item.motifStrength = 1; }); return { motifId, motifOccurrence: occurrence, motifPhase: 3, motifStrength: 1 }; } return { motifId: "free", motifOccurrence: 0, motifPhase: 0, motifStrength: 0 }; }
function noteOn(name, frequency, button) { if (pianoVoices.has(name)) return; enterPianoMode(); if (!audioContext) audioContext = new AudioContext(); audioContext.resume(); const now = audioContext.currentTime, output = audioContext.createGain(), filter = audioContext.createBiquadFilter(); output.gain.setValueAtTime(.0001, now); output.gain.exponentialRampToValueAtTime(.16, now + .008); output.gain.exponentialRampToValueAtTime(.065, now + .22); output.gain.setTargetAtTime(.0001, now + .22, 1.35); filter.type = "lowpass"; filter.frequency.setValueAtTime(Math.min(5200, frequency * 10), now); filter.frequency.exponentialRampToValueAtTime(Math.max(1800, frequency * 4.2), now + .9); filter.Q.value = .55; filter.connect(output).connect(audioContext.destination); const oscillators = [], partials = [[1, 1], [2.002, .34], [3.006, .16], [4.014, .085], [5.03, .045], [6.05, .022]]; for (const [ratio, level] of partials) { const oscillator = audioContext.createOscillator(), partialGain = audioContext.createGain(); oscillator.type = "sine"; oscillator.frequency.value = frequency * ratio; partialGain.gain.value = level; oscillator.connect(partialGain).connect(filter); oscillator.start(now); oscillators.push(oscillator); } const event = { time: pianoTime, pitch: Math.round(69 + 12 * Math.log2(frequency / 440)), energy: .42 + pianoVoices.size * .1, attack: .72, duration: .25, brightness: Math.min(1, (frequency - 220) / 500), group: Math.floor(pianoTime / .55), chordId: `piano-${Math.floor(pianoTime / .55)}`, voice: pianoVoices.size, order: events.length, motifId: "free", motifOccurrence: 0, motifPhase: 0, motifStrength: 0 }; Object.assign(event, liveMotifMeta(event)); events.push(event); addEvent(event, events.length - 1); pianoLastEvent = event; pianoVoices.set(name, { oscillators, output, button, event, started: pianoTime }); button.classList.add("active"); document.querySelector("#eventCount").textContent = events.length; document.querySelector("#lastNote").textContent = name; document.querySelector("#status").textContent = `Piano ao vivo · ${pianoVoices.size} tecla${pianoVoices.size === 1 ? "" : "s"}`; }
function noteOff(name) { const voice = pianoVoices.get(name); if (!voice) return; const now = audioContext.currentTime, held = Math.max(.25, pianoTime - voice.started); voice.event.duration = held; voice.output.gain.cancelScheduledValues(now); voice.output.gain.setTargetAtTime(.0001, now, .16); for (const oscillator of voice.oscillators) oscillator.stop(now + .8); voice.button.classList.remove("active"); pianoVoices.delete(name); if (held > .62) { const p = derived(voice.event); micelle.add(curvedFiber(p, { x: p.x, y: p.y + held * .5, z: p.z }, voice.event, "branch")); } }
function handlePianoKey(key, pressed) { const note = pianoNotes.find(item => item[2] === key.toLowerCase()); if (!note) return; const button = document.querySelector(`#piano [data-key="${CSS.escape(note[2])}"]`); if (pressed) noteOn(note[0], note[1], button); else noteOff(note[0]); }
function stopPianoVoices() { [...pianoVoices.keys()].forEach(noteOff); }
function motifTransform(e) {
  if (!e.motifId || e.motifId === "free") return { x: 0, z: 0, yScale: 1, sizeScale: 1 };
  const motif = stableHash(e.motifId), occurrence = Math.max(1, e.motifOccurrence || 1);
  const angle = ((motif % 17) / 17) * Math.PI * 2 + (occurrence - 1) * 1.47;
  const distance = .22 + ((motif >>> 5) % 5) * .07 + Math.min(.48, (occurrence - 1) * .16);
  return {
    x: Math.cos(angle) * distance,
    z: Math.sin(angle) * distance,
    yScale: .9 + ((motif + occurrence * 11) % 5) * .075,
    sizeScale: .9 + ((motif + occurrence * 7) % 4) * .08,
  };
}
function derived(e) {
  const register = (e.pitch - 36) / 48;
  const group = e.group ?? Math.floor(e.order / 3);
  const angle = (e.pitch % 12) / 12 * Math.PI * 2 + group * .17;
  const radius = .45 + register * 1.45 + e.energy * .42;
  const motif = e.motifId && e.motifId !== "free" ? stableHash(e.motifId) : stableHash(`${e.pitch}-${group}`);
  const fieldAngle = ((motif % 360) / 360) * Math.PI * 2 + (e.motifPhase || 0) * .16;
  const fieldRadius = e.motifId && e.motifId !== "free" ? .18 + (motif % 7) * .045 : 0;
  const occurrenceDrift = Math.min(.32, (e.motifOccurrence || 0) * .025);
  const fieldX = Math.cos(fieldAngle) * (fieldRadius + occurrenceDrift);
  const fieldZ = Math.sin(fieldAngle) * (fieldRadius + occurrenceDrift);
  const transform = motifTransform(e);
  const localY = register * 4.5 + e.energy * .5;
  const y = -2.55 + (localY + 2.55) * transform.yScale;
  return { x: Math.cos(angle) * radius + fieldX + transform.x + (e.attack - .5) * .22, y, z: Math.sin(angle) * radius + fieldZ + transform.z + (e.brightness - .5) * .72, fieldX: fieldX + transform.x, fieldZ: fieldZ + transform.z, radius, length: .25 + e.duration * 1.35, size: (.09 + e.energy * .17 + e.attack * .08) * transform.sizeScale };
}
function makeMaterial(e, rough = .68) { return new THREE.MeshStandardMaterial({ color: colorFor(e), roughness: rough, metalness: .08, flatShading: true }); }
function tubeBetween(a, b, radius, color, opacity = 1) {
  const va = new THREE.Vector3(a.x, a.y, a.z), vb = new THREE.Vector3(b.x, b.y, b.z), mid = va.clone().add(vb).multiplyScalar(.5), dir = vb.clone().sub(va);
  const mesh = new THREE.Mesh(new THREE.CylinderGeometry(radius, radius * 1.08, dir.length(), 7, 1), new THREE.MeshStandardMaterial({ color, roughness: .74, metalness: .1, transparent: opacity < 1, opacity }));
  mesh.position.copy(mid); mesh.quaternion.setFromUnitVectors(new THREE.Vector3(0, 1, 0), dir.normalize()); mesh.castShadow = true; return mesh;
}
function curvedFiber(a, b, e, kind = "branch") {
  const va = new THREE.Vector3(a.x, a.y, a.z), vb = new THREE.Vector3(b.x, b.y, b.z), mid = va.clone().add(vb).multiplyScalar(.5);
  const wobble = Math.sin((e.order + 1) * 2.17) * .16;
  mid.x += wobble; mid.y += kind === "root" ? -.18 : kind === "branch" ? .2 : .06; mid.z -= wobble * .7;
  const curve = new THREE.CatmullRomCurve3([va, mid, vb]);
  const tree = visualMode === "tree";
  const radius = tree ? kind === "root" ? .052 + e.energy * .035 : kind === "branch" ? .022 + e.attack * .024 : kind === "memory" ? .009 : .014 : kind === "root" ? .034 + e.energy * .025 : kind === "branch" ? .014 + e.attack * .018 : kind === "memory" ? .007 : .009;
  const opacity = tree ? kind === "root" ? .64 : kind === "memory" ? .52 : kind === "chord" ? .42 : .58 : kind === "root" ? .42 : kind === "chord" ? .34 : kind === "return" ? .38 : kind === "memory" ? .46 : .54;
  const mat = new THREE.MeshStandardMaterial({ color: colorFor(e), roughness: .55, metalness: .12, transparent: true, opacity });
  const mesh = new THREE.Mesh(new THREE.TubeGeometry(curve, 8, radius, 5, false), mat); mesh.castShadow = true; return mesh;
}
function musicalLine(a, b, e, kind) { return curvedFiber(a, b, e, kind === "chord" ? "chord" : kind === "return" ? "return" : "branch"); }

const grainMax = 9000;
const grainOrigin = new Float32Array(grainMax * 3), grainTarget = new Float32Array(grainMax * 3), grainVelocity = new Float32Array(grainMax * 3), grainBirth = new Float32Array(grainMax), grainLife = new Float32Array(grainMax), grainSize = new Float32Array(grainMax), grainColor = new Float32Array(grainMax * 3);
let grainCount = 0;
const grainGeometry = new THREE.BufferGeometry();
grainGeometry.setAttribute("aOrigin", new THREE.BufferAttribute(grainOrigin, 3)); grainGeometry.setAttribute("aTarget", new THREE.BufferAttribute(grainTarget, 3)); grainGeometry.setAttribute("aVelocity", new THREE.BufferAttribute(grainVelocity, 3)); grainGeometry.setAttribute("aBirth", new THREE.BufferAttribute(grainBirth, 1)); grainGeometry.setAttribute("aLife", new THREE.BufferAttribute(grainLife, 1)); grainGeometry.setAttribute("aSize", new THREE.BufferAttribute(grainSize, 1)); grainGeometry.setAttribute("aColor", new THREE.BufferAttribute(grainColor, 3)); grainGeometry.setDrawRange(0, 0);
const grainMaterial = new THREE.ShaderMaterial({ transparent: true, depthWrite: false, uniforms: { uTime: { value: 0 }, uActivity: { value: 1 } }, vertexShader: `attribute vec3 aOrigin;attribute vec3 aTarget;attribute vec3 aVelocity;attribute float aBirth;attribute float aLife;attribute float aSize;attribute vec3 aColor;uniform float uTime;varying vec3 vColor;varying float vAlpha;void main(){float age=max(0.0,uTime-aBirth);float t=min(age/aLife,1.0);float burst=exp(-age*1.25);float settle=1.0-exp(-age*2.4);vec3 p=aOrigin+aVelocity*age*(1.0-t*.9)+(aTarget-aOrigin)*settle;p.y-=.28*age*age;float swirl=sin(age*7.0+aBirth*3.0)*burst*.035;p.x+=swirl;p.z+=cos(age*6.0+aBirth*2.0)*burst*.035;vec4 mv=modelViewMatrix*vec4(p,1.0);gl_Position=projectionMatrix*mv;gl_PointSize=max(1.0,aSize*(1.0-t)*72.0/-mv.z);vColor=aColor;vAlpha=1.0-t;}`, fragmentShader: `uniform float uActivity;varying vec3 vColor;varying float vAlpha;void main(){vec2 p=gl_PointCoord-.5;float r=length(p);if(r>.5)discard;float edge=smoothstep(.5,.08,r);gl_FragColor=vec4(vColor,edge*vAlpha*.72*uActivity);}` });
granular.add(new THREE.Points(grainGeometry, grainMaterial));
const burstPool = Array.from({ length: 72 }, () => { const material = new THREE.MeshBasicMaterial({ color: "#ffffff", transparent: true, opacity: 0, wireframe: true, depthWrite: false }); const mesh = new THREE.Mesh(new THREE.IcosahedronGeometry(1, 1), material); mesh.visible = false; granular.add(mesh); return mesh; }); let burstIndex = 0;
function triggerBurst(e, p, strength = 1) { const mesh = burstPool[burstIndex++ % burstPool.length], material = mesh.material, now = performance.now() / 1000; mesh.position.set(p.x, p.y, p.z); mesh.scale.set(.08, .06, .08); mesh.visible = true; material.color.copy(colorFor(e)); material.opacity = .36 * Math.min(1, strength); mesh.userData = { born: now, life: .42 + e.duration * .38, radius: (.24 + e.attack * .62 + e.energy * .3) * strength, yStretch: 1.05 + e.duration * .34, zStretch: .82 + e.brightness * .25 }; }
function noteImpulse(e, p, strength = 1) { triggerBurst(e, p, strength); spawnGrains(e, p, Math.round(10 + e.attack * 34 + e.energy * 12)); }
function spawnGrains(e, p, count) {
  const now = performance.now() / 1000, col = colorFor(e);
  for (let i = 0; i < Math.round(count); i++) {
    const j = grainCount++ % grainMax, a = random() * Math.PI * 2, speed = .025 + random() * .12 * (.5 + e.attack), spread = .05 + random() * .18;
    grainOrigin[j * 3] = p.x + (random() - .5) * spread; grainOrigin[j * 3 + 1] = p.y + (random() - .5) * spread; grainOrigin[j * 3 + 2] = p.z + (random() - .5) * spread; grainTarget[j * 3] = p.x; grainTarget[j * 3 + 1] = p.y; grainTarget[j * 3 + 2] = p.z;
    grainVelocity[j * 3] = Math.cos(a) * speed; grainVelocity[j * 3 + 1] = .02 + random() * .13 + e.attack * .12; grainVelocity[j * 3 + 2] = Math.sin(a) * speed;
    grainBirth[j] = now; grainLife[j] = .45 + random() * .8 + e.duration * .45; grainSize[j] = 1.5 + random() * 3.5 + e.attack * 3; grainColor[j * 3] = col.r; grainColor[j * 3 + 1] = col.g; grainColor[j * 3 + 2] = col.b;
  }
  grainGeometry.setDrawRange(0, Math.min(grainCount, grainMax)); Object.values(grainGeometry.attributes).forEach(a => a.needsUpdate = true);
}

function addMatter(e, p) {
  if (visualMode === "tree" && e.pitch >= 53 && e.energy <= .72) return;
  const geo = new THREE.IcosahedronGeometry(p.size, 2), pos = geo.attributes.position;
  for (let i = 0; i < pos.count; i++) { const n = pos.getX(i) + pos.getY(i) * 2.1 + pos.getZ(i) * 3.7, k = 1 + Math.sin(n + e.order * 1.7) * .13 + random() * .08; pos.setXYZ(i, pos.getX(i) * k, pos.getY(i) * (1 + e.duration * .28), pos.getZ(i) * k); }
  geo.computeVertexNormals(); const mesh = new THREE.Mesh(geo, makeMaterial(e)); mesh.position.set(p.x, p.y, p.z); mesh.scale.set(1 + e.attack * .45, 1 + e.duration * .18, 1 + e.energy * .3); mesh.castShadow = true; matter.add(mesh);
}
function addResidue(e, p) {
  const count = Math.min(14, Math.round(2 + e.attack * 10));
  for (let i = 0; i < count; i++) { const s = .018 + random() * .045 * (1 + e.attack), mesh = new THREE.Mesh(new THREE.SphereGeometry(s, 6, 4), makeMaterial(e, .82)), a = random() * Math.PI * 2, d = .18 + random() * (.25 + e.attack * .5); mesh.position.set(p.x + Math.cos(a) * d, p.y + (random() - .5) * d - e.duration * .25, p.z + Math.sin(a) * d); mesh.castShadow = true; residue.add(mesh); }
  if (e.duration > .7) residue.add(tubeBetween(p, { x: p.x, y: p.y - e.duration * .55, z: p.z }, .018 + e.energy * .025, colorFor(e)));
}
function addTreeBud(e, p) {
  const count = Math.min(4, Math.max(1, Math.round(1 + e.attack * 2 + (e.pitch > 66 ? 1 : 0))));
  for (let i = 0; i < count; i++) {
    const angle = stableHash(`${e.order}-bud-${i}`) % 628 / 100;
    const distance = .08 + ((stableHash(`${e.order}-bud-distance-${i}`) % 100) / 100) * (.12 + e.attack * .18);
    const size = .045 + e.energy * .035 + e.attack * .025;
    const bud = new THREE.Mesh(new THREE.ConeGeometry(size, size * (1.7 + e.duration * .5), 6, 1), makeMaterial(e, .86));
    bud.position.set(p.x + Math.cos(angle) * distance, p.y + .08 + i * .025, p.z + Math.sin(angle) * distance);
    bud.rotation.set(Math.sin(angle) * .55, angle, Math.cos(angle) * .35);
    bud.castShadow = true; residue.add(bud);
  }
}
function treeNodeGeometry(e, size) {
  if (e.pitch < 53 || e.energy > .72) {
    const geo = new THREE.IcosahedronGeometry(1, 1), pos = geo.attributes.position;
    for (let i = 0; i < pos.count; i++) {
      const x = pos.getX(i), y = pos.getY(i), z = pos.getZ(i);
      pos.setXYZ(i, x * (1 + Math.sin(i * 2.4 + e.order) * .1), y * (1 + e.duration * .22), z * (1 + Math.cos(i * 1.7 + e.pitch) * .08));
    }
    geo.computeVertexNormals();
    return geo;
  }
  if (e.pitch > 67 || e.attack > .62) return new THREE.ConeGeometry(.82, 1.8 + e.duration * .8, 6, 1);
  return new THREE.CylinderGeometry(.72, 1, 1.45 + e.duration * .65, 7, 1);
}
function organicNodeGeometry(e, size) {
  const geo = new THREE.IcosahedronGeometry(1, 2), pos = geo.attributes.position;
  for (let i = 0; i < pos.count; i++) {
    const x = pos.getX(i), y = pos.getY(i), z = pos.getZ(i);
    const wave = Math.sin((i + 1) * 2.31 + e.order * 1.73) * .12 + Math.sin((i + 3) * .71 + e.pitch * .17) * .06;
    const asymmetry = 1 + wave + (x * .055) - (z * .035);
    pos.setXYZ(i, x * asymmetry, y * (1 + e.duration * .24 + wave * .45), z * asymmetry);
  }
  geo.computeVertexNormals();
  return geo;
}
function addEvent(e, index) {
  const p = derived(e), previous = index ? derived(events[index - 1]) : null;
  if (previous) { if (e.group === events[index - 1].group) connections.add(musicalLine(previous, p, e, "chord")); else if (e.time - events[index - 1].time < 1.1) connections.add(musicalLine(previous, p, e, "melody")); }
  for (let i = index - 1; i >= Math.max(0, index - 12); i--) if (events[i].pitch % 12 === e.pitch % 12 && events[i].group !== e.group && (visualMode !== "tree" || e.order % 4 === 0)) { connections.add(musicalLine(derived(events[i]), p, e, "return")); break; }
  if (e.motifId && e.motifId !== "free") for (let i = index - 1; i >= 0; i--) if (events[i].motifId === e.motifId && events[i].motifPhase === e.motifPhase) { connections.add(curvedFiber(derived(events[i]), p, e, "memory")); break; }
  const rootAngle = e.order * .83 + (e.pitch % 12) * .11;
  const rootRadius = 1.05 + (e.energy * .72) + ((e.order % 5) * .08);
  if (visualMode === "tree") {
    if (e.pitch < 53) {
      const rootEnd = { x: Math.cos(rootAngle) * rootRadius + p.x * .08, y: -3.02 + Math.sin(e.order * .71) * .06, z: Math.sin(rootAngle) * rootRadius + p.z * .08 };
      micelle.add(curvedFiber(rootEnd, p, e, "root"));
    } else if (e.order % 3 === 0) {
      const branchEnd = { x: p.x * .58, y: Math.max(-2.78, p.y - 1.12), z: p.z * .58 };
      micelle.add(curvedFiber(branchEnd, p, e, "branch"));
    }
  } else {
    const rootEnd = { x: p.x * .2 + p.fieldX * 1.7, y: -2.95 + Math.sin(e.order * .71) * .08, z: p.z * .2 + p.fieldZ * 1.7 };
    micelle.add(curvedFiber(rootEnd, p, e, e.pitch < 53 ? "root" : "branch"));
  }
  if (e.duration > .62) micelle.add(curvedFiber(p, { x: p.x + Math.sin(e.order) * .35, y: p.y + e.duration * .55, z: p.z + Math.cos(e.order) * .32 }, e, "branch"));
  const nodeMaterial = makeMaterial(e, visualMode === "tree" ? .86 : .78); if (visualMode !== "tree") nodeMaterial.color.multiplyScalar(.78); const node = new THREE.Mesh(visualMode === "tree" ? treeNodeGeometry(e, p.size) : organicNodeGeometry(e, p.size), nodeMaterial); node.position.set(p.x, p.y, p.z); node.scale.set(p.size * (1 + e.attack * .42), p.size * (1 + e.duration * .2), p.size * (1 + e.energy * .3)); if (visualMode === "tree") { node.rotation.y = rootAngle; node.rotation.z = Math.sin(e.order * .83) * .24; } node.castShadow = true; structure.add(node);
  addMatter(e, p); if (visualMode === "tree") { if (e.attack > .16 || e.pitch > 65) addTreeBud(e, p); } else if (e.attack > .22 || e.duration > .65) addResidue(e, p); noteImpulse(e, p, .7 + e.attack * .8);
  document.querySelector("#lastNote").textContent = noteName(e.pitch); document.querySelector("#timeValue").textContent = timeLabel(e.time); document.querySelector("#progress").style.width = `${Math.min(100, e.time / (audioBuffer?.duration || 1) * 100)}%`;
}
function breathAt(musicTime) { const interval = breathEnvelope.find(item => musicTime >= item.start && musicTime <= item.end); if (!interval) return 0; const edge = Math.min(musicTime - interval.start, interval.end - musicTime); const fade = Math.min(1, edge / .18); return interval.strength * fade; }
function applyBreath(musicTime) { const breath = pianoMode ? (pianoVoices.size ? 0 : Math.min(1, Math.max(0, (musicTime - (pianoLastEvent?.time || 0) - .42) / .8))) : breathAt(musicTime); const inhale = Math.sin(performance.now() / 1000 * 2.15) * .5 + .5; sculptureRoot.scale.setScalar(1 + breath * inhale * .012); grainMaterial.uniforms.uActivity.value = 1 - breath * .72; return breath; }
function clearSculpture() { connections.clear(); micelle.clear(); structure.clear(); matter.clear(); residue.clear(); grainCount = 0; grainGeometry.setDrawRange(0, 0); burstPool.forEach(mesh => { mesh.visible = false; mesh.material.opacity = 0; }); sculptureRoot.scale.setScalar(1); grainMaterial.uniforms.uActivity.value = 1; revealedIndex = 0; impulseIndex = 0; document.querySelector("#lastNote").textContent = "—"; document.querySelector("#timeValue").textContent = "0:00"; document.querySelector("#progress").style.width = "0%"; }
function setVisualMode(mode) {
  if (mode === visualMode) return;
  const wasPlaying = playing;
  visualMode = mode === "tree" ? "tree" : "mycelium";
  if (wasPlaying) { ++playGeneration; source?.stop(); playing = false; play.textContent = "Reproduzir"; }
  clearSculpture();
  if (wasPlaying) play.click();
  else if (audioBuffer) status.textContent = `Forma ${visualMode === "tree" ? "árvore / raízes" : "micélio"} selecionada · pronta para crescer.`;
}
function resetCamera() { controls.reset(); camera.position.set(5.9, 2.8, 8.8); controls.target.set(0, 0, 0); controls.update(); }

function motifSignature(items) {
  if (items.length < 3) return "";
  const origin = items[0];
  return items.map((item, index) => `${Math.round((item.pitch - origin.pitch) / 2)}:${index ? Math.round((item.time - origin.time) / .08) : 0}`).join("/");
}
function annotateMusicalMemory(input, duration) {
  const annotated = input.map((event, index) => ({ ...event, motifId: "free", motifOccurrence: 0, motifPhase: 0, motifStrength: 0, phraseIndex: Math.floor(index / 8), tension: Math.min(1, event.energy * .45 + event.attack * .55) }));
  const windows = [], counts = new Map();
  for (let length = 3; length <= 6; length++) for (let start = 0; start + length <= annotated.length; start++) {
    const window = annotated.slice(start, start + length), span = window.at(-1).time - window[0].time;
    if (span > 3.8) continue;
    const signature = motifSignature(window), key = `${length}:${signature}`;
    windows.push({ start, length, signature, key }); counts.set(key, (counts.get(key) || 0) + 1);
  }
  const recurring = windows.filter(window => (counts.get(window.key) || 0) >= 2).sort((a, b) => b.length - a.length || (counts.get(b.key) - counts.get(a.key)) || a.start - b.start);
  const occupied = new Set(), motifIds = new Map(), matches = [];
  for (const window of recurring) {
    const positions = Array.from({ length: window.length }, (_, offset) => window.start + offset);
    if (positions.some(position => occupied.has(position))) continue;
    positions.forEach(position => occupied.add(position));
    if (!motifIds.has(window.key)) motifIds.set(window.key, `motif-${motifIds.size + 1}`);
    matches.push({ ...window, motifId: motifIds.get(window.key), occurrence: matches.filter(match => match.motifId === motifIds.get(window.key)).length + 1 });
  }
  for (const match of matches) for (let phase = 0; phase < match.length; phase++) {
    const event = annotated[match.start + phase]; event.motifId = match.motifId; event.motifOccurrence = match.occurrence; event.motifPhase = phase; event.motifStrength = Math.min(1, (counts.get(match.key) || 2) / 5); event.phraseIndex = Math.floor(match.start / 8); event.tension = Math.min(1, event.tension + event.motifStrength * .18);
  }
  const breaths = [];
  for (let index = 1; index < annotated.length; index++) {
    const previous = annotated[index - 1], current = annotated[index], start = previous.time + previous.duration * .55, gap = current.time - start;
    if (gap > .52) breaths.push({ start, end: Math.min(duration, current.time), strength: Math.min(1, (gap - .52) / 1.2) });
  }
  return { events: annotated, breaths };
}
function spectralPeaks(data, start, win, sr) {
  const peaks = [];
  for (let k = 2; k < 170; k++) { let re = 0, im = 0; for (let i = 0; i < win; i += 8) { const v = (data[start + i] || 0) * (.5 - .5 * Math.cos(2 * Math.PI * i / win)), a = 2 * Math.PI * k * i / win; re += v * Math.cos(a); im -= v * Math.sin(a); } peaks.push({ k, mag: re * re + im * im }); }
  peaks.sort((a, b) => b.mag - a.mag); const chosen = [];
  for (const peak of peaks) { if (chosen.length >= 5 || (chosen[0] && peak.mag < chosen[0].mag * .12)) break; const harmonic = chosen.some(p => Math.abs(peak.k - p.k) < 3 || Math.abs(peak.k - p.k * 2) < 3 || Math.abs(p.k - peak.k * 2) < 3); if (!harmonic) chosen.push(peak); }
  return chosen.map(p => ({ pitch: Math.max(36, Math.min(84, Math.round(69 + 12 * Math.log2(Math.max(27.5, p.k * sr / win) / 440)))), brightness: Math.min(1, p.k / 170), strength: Math.min(1, p.mag / (chosen[0]?.mag || 1)) }));
}
function analyze(buffer) {
  const data = buffer.getChannelData(0), sr = buffer.sampleRate, frame = 512, win = 1024, candidates = [], envelope = [];
  let previousEnergy = 0, lastOnset = -Infinity;
  for (let start = 0; start + win < data.length; start += frame) {
    let sum = 0; for (let i = 0; i < win; i++) sum += (data[start + i] || 0) ** 2;
    const energy = Math.sqrt(sum / win), onset = Math.max(0, energy - previousEnergy), time = start / sr;
    if (Math.floor(start / frame) % 3 === 0) envelope.push({ time, energy: Math.min(1, energy * 5.8), attack: Math.min(1, onset * 25) });
    if (energy > .01 && time - lastOnset > .11 && (onset > .0028 || time - lastOnset > .42)) {
      const peaks = spectralPeaks(data, start, win, sr), group = Math.floor(time / .55);
      peaks.forEach((peak, index) => candidates.push({ time, pitch: peak.pitch, energy: Math.min(1, energy * 5.8) * (.72 + peak.strength * .28), attack: Math.min(1, onset * 25), duration: .22 + Math.min(1, energy * 3.8), brightness: peak.brightness, group, chordId: `chord-${group}`, voice: index, order: candidates.length }));
      if (peaks.length) lastOnset = time;
    }
    previousEnergy = energy;
  }
  const target = Math.max(80, Math.min(220, Math.round(buffer.duration * 1.05)));
  if (candidates.length <= target) { const memory = annotateMusicalMemory(candidates, buffer.duration); return { events: memory.events, envelope, breaths: memory.breaths }; }
  const groups = [...new Set(candidates.map(e => e.group))]; const wanted = Math.max(1, Math.floor(target / 2.3)); const selectedGroups = groups.filter((_, i) => i % Math.max(1, Math.ceil(groups.length / wanted)) === 0).slice(0, wanted);
  const selected = candidates.filter(e => selectedGroups.includes(e.group)).sort((a, b) => a.time - b.time || a.voice - b.voice).slice(0, target).map((e, i) => ({ ...e, order: i }));
  const memory = annotateMusicalMemory(selected, buffer.duration);
  return { events: memory.events, envelope, breaths: memory.breaths };
}

async function hash(bytes) { const d = await crypto.subtle.digest("SHA-256", bytes); return [...new Uint8Array(d)].map(x => x.toString(16).padStart(2, "0")).join(""); }
async function decodeBytes(bytes) { const ctx = new AudioContext(), decoded = await ctx.decodeAudioData(bytes.slice().buffer), mono = ctx.createBuffer(1, decoded.length, decoded.sampleRate), out = mono.getChannelData(0); for (let c = 0; c < decoded.numberOfChannels; c++) { const ch = decoded.getChannelData(c); for (let i = 0; i < decoded.length; i++) out[i] += ch[i] / decoded.numberOfChannels; } const analysis = analyze(mono); return { bytes, buffer: mono, ...analysis }; }
async function decode(file) { return decodeBytes(new Uint8Array(await file.arrayBuffer())); }
const input = document.querySelector("#fileInput"), play = document.querySelector("#playButton"), status = document.querySelector("#status"), trackNames = { chopin: "Chopin · Nocturne Op. 9 No. 2", beethoven: "Beethoven · Für Elise", bach: "Bach · Prelude No. 2", moonlight: "Beethoven · Moonlight Sonata · I", tetris: "Tetris Theme · Korobeiniki" };
const visualModeSelect = document.createElement("select"); visualModeSelect.id = "visualMode"; visualModeSelect.innerHTML = '<option value="mycelium">Micélio</option><option value="tree">Árvore / raízes</option>'; const visualModeControl = document.createElement("div"); visualModeControl.className = "rotation-control"; visualModeControl.innerHTML = '<label for="visualMode">Forma da matéria</label>'; visualModeControl.append(visualModeSelect); document.querySelector("#rotationMode").closest(".rotation-control").before(visualModeControl); visualModeSelect.addEventListener("change", event => setVisualMode(event.target.value));
buildPiano(); addEventListener("keydown", event => { if (!event.repeat) handlePianoKey(event.key, true); }); addEventListener("keyup", event => handlePianoKey(event.key, false));
async function loadTrack(label, request, key = "") { stopPianoVoices(); status.textContent = `Analisando ${label}…`; try { const r = await request(); audioBuffer = r.buffer; events = r.events; granularEnvelope = r.envelope; breathEnvelope = r.breaths || []; baseSeed = parseInt((await hash(r.bytes)).slice(0, 8), 16); seed = baseSeed; currentTrack = key || "custom"; pianoMode = false; clearSculpture(); document.querySelector("#fileName").textContent = label; document.querySelector("#eventCount").textContent = events.length; play.disabled = !events.length; document.querySelector("#pngButton").disabled = !events.length; document.querySelector("#jsonButton").disabled = !events.length; document.querySelectorAll(".track").forEach(b => b.classList.toggle("primary", b.dataset.track === key)); status.textContent = `${events.length} eventos polifônicos · ${timeLabel(audioBuffer.duration)} · pronta para crescer.`; } catch (error) { console.error(error); status.textContent = `Não foi possível carregar ${label}. Verifique se o arquivo existe em Downloads.`; } }
input.addEventListener("change", () => { const file = input.files[0]; if (file) loadTrack(file.name, () => decode(file)); });
document.querySelectorAll(".track").forEach(button => button.addEventListener("click", () => { const k = button.dataset.track; loadTrack(trackNames[k], async () => { const r = await fetch(`/music/${k}.mp3`); if (!r.ok) throw Error("track unavailable"); return decodeBytes(new Uint8Array(await r.arrayBuffer())); }, k); }));
loadTrack(trackNames.chopin, async () => { const r = await fetch("/music/chopin.mp3"); if (!r.ok) throw Error("default track unavailable"); return decodeBytes(new Uint8Array(await r.arrayBuffer())); }, "chopin");
play.addEventListener("click", async () => { if (!audioBuffer) return; if (!audioContext) audioContext = new AudioContext(); if (audioContext.state === "suspended") await audioContext.resume(); if (playing) { source?.stop(); playing = false; play.textContent = "Reproduzir"; return; } clearSculpture(); seed = baseSeed; const generation = ++playGeneration; source = audioContext.createBufferSource(); source.buffer = audioBuffer; source.connect(audioContext.destination); playStartedAt = audioContext.currentTime; source.start(); playing = true; play.textContent = "Pausar"; status.textContent = "A escultura está se formando…"; source.onended = () => { if (generation !== playGeneration || !playing) return; playing = false; play.textContent = "Reproduzir"; status.textContent = `Obra concluída · ${events.length} eventos · modo contemplação.`; }; });
document.querySelector("#clearButton").addEventListener("click", () => { ++playGeneration; source?.stop(); playing = false; clearSculpture(); if (pianoMode) { events = []; granularEnvelope = []; pianoTime = 0; pianoLastEvent = null; document.querySelector("#eventCount").textContent = "0"; } play.textContent = "Reproduzir"; status.textContent = pianoMode ? "Piano pronto. Toque para recomeçar a escultura." : "Escultura limpa. A mesma música pode ser reconstruída."; });
document.querySelector("#rotateButton").addEventListener("click", e => { const on = e.currentTarget.dataset.on !== "true"; e.currentTarget.dataset.on = String(on); controls.autoRotate = on; e.currentTarget.textContent = on ? "Auto-rotação: ligada" : "Auto-rotação: desligada"; });
document.querySelector("#rotationMode").addEventListener("change", e => { rotationMode = e.currentTarget.value; document.querySelector("#rotationSpeed").disabled = rotationMode !== "user"; });
document.querySelector("#rotationSpeed").addEventListener("input", e => { userRotationSpeed = Number(e.currentTarget.value); document.querySelector("#rotationSpeedValue").textContent = userRotationSpeed.toFixed(2); });
document.querySelector("#resetButton").addEventListener("click", resetCamera);
function downloadBlob(blob, filename) { const a = document.createElement("a"); a.href = URL.createObjectURL(blob); a.download = filename; a.style.display = "none"; document.body.append(a); a.click(); setTimeout(() => { URL.revokeObjectURL(a.href); a.remove(); }, 1000); }
document.querySelector("#pngButton").addEventListener("click", () => renderer.domElement.toBlob(blob => { downloadBlob(blob, "music-sculpture.png"); status.textContent = "PNG exportado · a imagem preserva a vista atual."; }, "image/png"));
document.querySelector("#jsonButton").addEventListener("click", () => { const blob = new Blob([JSON.stringify({ version: "2.1.0", seed: baseSeed, track: currentTrack, visualMode, parameters: { pitch: "height/radius", energy: "thickness/scale", attack: "granular pulse", duration: "filament or branch", brightness: "palette", group: "chord/micelle hub", motif: "persistent distributed memory", breath: "silence and field respiration" }, events, granularEnvelope, breaths: breathEnvelope }, null, 2)], { type: "application/json" }); downloadBlob(blob, "music-sculpture.json"); const memoryCount = events.filter(event => event.motifId && event.motifId !== "free").length; status.textContent = `JSON 2.1.0 exportado · ${events.length} eventos · ${breathEnvelope.length} pausas · ${memoryCount} memórias · ${visualMode === "tree" ? "árvore" : "micélio"}.`; });
function updateRotation(musicTime) { if (rotationMode === "user") { controls.autoRotateSpeed = userRotationSpeed; return; } const recent = pianoMode ? events.filter(e => e.time <= musicTime && e.time > musicTime - 1.35) : granularEnvelope.filter(e => e.time <= musicTime && e.time > musicTime - 1.35); if (!recent.length) { controls.autoRotateSpeed = .16; return; } const energy = recent.reduce((sum, e) => sum + e.energy, 0) / recent.length; const attack = recent.reduce((sum, e) => sum + e.attack, 0) / recent.length; controls.autoRotateSpeed = .12 + Math.min(1, energy * .48 + attack * .9) * .95; }
function animate() { requestAnimationFrame(animate); const now = performance.now() / 1000, dt = Math.min(.1, Math.max(0, now - pianoLastFrame)); pianoLastFrame = now; if (pianoMode) { pianoTime += dt; if (pianoVoices.size && pianoLastEvent && Math.random() < .7) spawnGrains(pianoLastEvent, derived(pianoLastEvent), 1 + pianoVoices.size * 1.5); document.querySelector("#timeValue").textContent = timeLabel(pianoTime); updateRotation(pianoTime); applyBreath(pianoTime); } else if (playing && audioContext) { const musicTime = audioContext.currentTime - playStartedAt; let added = 0; while (revealedIndex < events.length && events[revealedIndex].time <= musicTime && added < 10) { addEvent(events[revealedIndex], revealedIndex++); added++; } while (impulseIndex < granularEnvelope.length && granularEnvelope[impulseIndex].time <= musicTime) { const impulse = granularEnvelope[impulseIndex++]; const current = events[Math.max(0, revealedIndex - 1)]; if (current && (impulse.attack > .035 || impulse.energy > .08)) { spawnGrains({ ...current, energy: impulse.energy, attack: impulse.attack }, derived(current), 1 + impulse.attack * 8); if (impulse.attack > .2) triggerBurst(current, derived(current), .55 + impulse.attack); } } if (musicTime > 0) document.querySelector("#timeValue").textContent = timeLabel(Math.min(musicTime, audioBuffer.duration)); updateRotation(musicTime); applyBreath(musicTime); } else if (rotationMode === "user") controls.autoRotateSpeed = userRotationSpeed; burstPool.forEach(mesh => { if (!mesh.visible) return; const age = now - mesh.userData.born, t = Math.min(1, age / mesh.userData.life), pulse = Math.sin(Math.min(1, t) * Math.PI); const radius = .08 + mesh.userData.radius * pulse; mesh.scale.set(radius * 1.08, radius * mesh.userData.yStretch, radius * mesh.userData.zStretch); mesh.rotation.x += .012; mesh.rotation.z += .008; mesh.material.opacity = Math.max(0, .36 * (1 - t)); if (t >= 1) mesh.visible = false; }); grainMaterial.uniforms.uTime.value = now; controls.update(); renderer.render(scene, camera); }
animate();
