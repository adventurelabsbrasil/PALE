import * as THREE from "./vendor/three.module.min.js";
import { OrbitControls } from "./vendor/OrbitControls.js";

const data = await fetch("experience_data.json").then((response) => response.json());
const status = document.querySelector("#status");
const selection = document.querySelector("#selection");
const audioPath = document.querySelector("#audioPath");
const audioButton = document.querySelector("#audioButton");
const toggleButton = document.querySelector("#toggleButton");
const motion = document.querySelector("#motion");
let selected = null;
let audioContext = null;
let audioBuffer = null;
let sourceNode = null;
let gainNode = null;
let pannerNode = null;
let analyserNode = null;
let frequencyData = null;
let timeDomainData = null;
let activeWorld = "world_a";
const audioMotion = {amplitude: 0, low: 0, mid: 0, high: 0};

function makeWorld(canvas, key, color) {
  const scene = new THREE.Scene();
  scene.background = new THREE.Color("#081018");
  const camera = new THREE.PerspectiveCamera(48, 1, .1, 100);
  camera.position.set(0, 0, 4.2);
  let renderer = null;
  let fallbackContext = null;
  try {
    renderer = new THREE.WebGLRenderer({canvas, antialias: true, alpha: false});
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
  } catch (error) {
    fallbackContext = canvas.getContext("2d");
    status.textContent = "WebGL indisponível: usando prévia 2D determinística.";
  }
  const controls = new OrbitControls(camera, canvas);
  controls.enableDamping = true;
  controls.minDistance = 2.1;
  controls.maxDistance = 7;
  const positions = new Float32Array(data.points.length * 3);
  const base = [];
  data.points.forEach((point, index) => {
    const value = point[key];
    base.push(value);
    positions[index * 3] = value[0] * 1.45;
    positions[index * 3 + 1] = value[1] * 1.45;
    positions[index * 3 + 2] = value[2] * 1.45;
  });
  const geometry = new THREE.BufferGeometry();
  geometry.setAttribute("position", new THREE.BufferAttribute(positions, 3));
  const material = new THREE.PointsMaterial({color, size: .055, sizeAttenuation: true, transparent: true, opacity: .88});
  const points = new THREE.Points(geometry, material);
  const baseColor = new THREE.Color(color);
  scene.add(points);
  const ring = new THREE.Mesh(new THREE.RingGeometry(.07, .09, 24), new THREE.MeshBasicMaterial({color, side: THREE.DoubleSide}));
  ring.visible = false;
  scene.add(ring);
  const raycaster = new THREE.Raycaster();
  raycaster.params.Points.threshold = .11;
  canvas.addEventListener("pointerdown", (event) => {
    const rect = canvas.getBoundingClientRect();
    const pointer = new THREE.Vector2((event.clientX - rect.left) / rect.width * 2 - 1, -(event.clientY - rect.top) / rect.height * 2 + 1);
    raycaster.setFromCamera(pointer, camera);
    const hit = raycaster.intersectObject(points)[0];
    if (hit) select(data.points[hit.index], key, ring, base[hit.index]);
  });
  function resize() {
    const rect = canvas.getBoundingClientRect();
    if (renderer) renderer.setSize(rect.width, rect.height, false);
    else { canvas.width = Math.max(1, rect.width * devicePixelRatio); canvas.height = Math.max(1, rect.height * devicePixelRatio); }
    camera.aspect = rect.width / rect.height;
    camera.updateProjectionMatrix();
  }
  function renderFallback(time) {
    if (!fallbackContext) return;
    const width = canvas.width, height = canvas.height;
    fallbackContext.fillStyle = "#081018";
    fallbackContext.fillRect(0, 0, width, height);
    fallbackContext.fillStyle = color;
    base.forEach((value, index) => {
      const x = width * (.5 + value[0] * .42);
      const y = height * (.5 - value[1] * .42 - Math.sin(time * .00035 + index * .17) * .006);
      const radius = selected?.id === data.points[index].id ? 5 : 2.5;
      fallbackContext.beginPath(); fallbackContext.arc(x, y, radius * devicePixelRatio, 0, Math.PI * 2); fallbackContext.fill();
    });
  }
  function reset() { controls.reset(); camera.position.set(0, 0, 4.2); controls.target.set(0, 0, 0); }
  function resetAudioVisuals() {
    points.scale.setScalar(1);
    material.color.copy(baseColor);
    material.opacity = .88;
  }
  return {scene, camera, renderer, controls, positions, base, ring, resize, reset, renderFallback, key, points, material, baseColor, resetAudioVisuals};
}

const worldA = makeWorld(document.querySelector("#worldA"), "world_a", "#52c7ff");
const worldB = makeWorld(document.querySelector("#worldB"), "world_b", "#f5b96b");
const worlds = [worldA, worldB];

function select(point, key, ring, value) {
  selected = point;
  selection.textContent = `${point.id} · split=${point.split} · ${key === "world_a" ? data.representations.world_a : data.representations.world_b}`;
  audioPath.textContent = `WAV local: ${point.audio}`;
  worlds.forEach((world) => { world.ring.visible = false; });
  ring.visible = true;
  ring.position.set(value[0] * 1.45, value[1] * 1.45, value[2] * 1.45);
  status.textContent = `Selecionado ${point.id}. Gesto de áudio necessário para ouvir.`;
  if (audioBuffer) playSelected();
}

async function startAudio() {
  if (!selected) select(data.points[0], "world_a", worldA.ring, worldA.base[0]);
  audioContext ??= new AudioContext();
  if (audioContext.state === "suspended") await audioContext.resume();
  if (!audioBuffer) audioBuffer = await audioContext.decodeAudioData(await fetch(selected.audio).then((response) => response.arrayBuffer()));
  analyserNode ??= audioContext.createAnalyser();
  analyserNode.fftSize = 1024;
  analyserNode.smoothingTimeConstant = .82;
  frequencyData ??= new Uint8Array(analyserNode.frequencyBinCount);
  timeDomainData ??= new Uint8Array(analyserNode.fftSize);
  toggleButton.disabled = false;
  audioButton.textContent = "Reiniciar áudio";
  playSelected();
}

function playSelected() {
  if (!audioContext || !audioBuffer || !selected) return;
  sourceNode?.stop();
  sourceNode = audioContext.createBufferSource();
  sourceNode.buffer = audioBuffer;
  gainNode ??= audioContext.createGain();
  pannerNode ??= audioContext.createStereoPanner();
  analyserNode ??= audioContext.createAnalyser();
  const coordinate = selected[activeWorld][0];
  pannerNode.pan.setTargetAtTime(Math.max(-1, Math.min(1, coordinate)), audioContext.currentTime, .02);
  gainNode.gain.setTargetAtTime(data.max_gain, audioContext.currentTime, .02);
  sourceNode.connect(analyserNode).connect(pannerNode).connect(gainNode).connect(audioContext.destination);
  sourceNode.start();
  status.textContent = `Ouvindo ${activeWorld === "world_a" ? "Mundo A" : "Mundo B"} · panorama ${coordinate.toFixed(2)} · mundos reagindo ao áudio.`;
}

audioButton.addEventListener("click", startAudio);
toggleButton.addEventListener("click", () => { activeWorld = activeWorld === "world_a" ? "world_b" : "world_a"; toggleButton.textContent = activeWorld === "world_a" ? "Ouvir Mundo A" : "Ouvir Mundo B"; playSelected(); });
document.querySelector("#resetButton").addEventListener("click", () => worlds.forEach((world) => world.reset()));

function smooth(previous, next, amount) {
  return previous + (next - previous) * amount;
}

function updateAudioMotion() {
  if (!analyserNode || !frequencyData || !timeDomainData) {
    audioMotion.amplitude = smooth(audioMotion.amplitude, 0, .04);
    audioMotion.low = smooth(audioMotion.low, 0, .04);
    audioMotion.mid = smooth(audioMotion.mid, 0, .04);
    audioMotion.high = smooth(audioMotion.high, 0, .04);
    return;
  }
  analyserNode.getByteFrequencyData(frequencyData);
  analyserNode.getByteTimeDomainData(timeDomainData);
  let sum = 0;
  for (const value of timeDomainData) {
    const centered = (value - 128) / 128;
    sum += centered * centered;
  }
  const bandAverage = (start, end) => {
    let total = 0;
    for (let index = start; index < end; index++) total += frequencyData[index] / 255;
    return total / Math.max(1, end - start);
  };
  const low = bandAverage(1, 12);
  const mid = bandAverage(12, 72);
  const high = bandAverage(72, 220);
  audioMotion.amplitude = smooth(audioMotion.amplitude, Math.min(1, Math.sqrt(sum / timeDomainData.length) * 3.4), .16);
  audioMotion.low = smooth(audioMotion.low, low, .12);
  audioMotion.mid = smooth(audioMotion.mid, mid, .12);
  audioMotion.high = smooth(audioMotion.high, high, .12);
}

function applyAudioVisuals(seconds) {
  updateAudioMotion();
  worlds.forEach((world, worldIndex) => {
    if (!motion.checked) {
      const attribute = world.points.geometry.getAttribute("position");
      for (let index = 0; index < data.points.length; index++) {
        attribute.array[index * 3] = world.base[index][0] * 1.45;
        attribute.array[index * 3 + 1] = world.base[index][1] * 1.45;
        attribute.array[index * 3 + 2] = world.base[index][2] * 1.45;
      }
      attribute.needsUpdate = true;
      world.resetAudioVisuals();
      return;
    }
    const attribute = world.points.geometry.getAttribute("position");
    const pulse = audioMotion.amplitude * (.11 + worldIndex * .018);
    const drift = audioMotion.low * .035;
    for (let index = 0; index < data.points.length; index++) {
      const point = world.base[index];
      const phase = seconds * (.35 + audioMotion.mid * .12) + index * .17;
      attribute.array[index * 3] = point[0] * 1.45 + Math.sin(phase) * drift;
      attribute.array[index * 3 + 1] = point[1] * 1.45 + Math.sin(phase) * (.018 + pulse * .18);
      attribute.array[index * 3 + 2] = point[2] * 1.45 + Math.cos(phase * .83) * audioMotion.high * .025;
    }
    attribute.needsUpdate = true;
    world.points.scale.setScalar(1 + pulse);
    const hueShift = audioMotion.high * .035 - audioMotion.low * .018;
    const hsl = {};
    world.baseColor.getHSL(hsl);
    world.material.color.setHSL((hsl.h + hueShift + 1) % 1, hsl.s, Math.min(.72, hsl.l + audioMotion.mid * .1));
    world.material.opacity = Math.min(.98, .88 + audioMotion.amplitude * .1);
  });
}

function frame(time) {
  const seconds = time / 1000;
  applyAudioVisuals(seconds);
  worlds.forEach((world) => {
    world.controls.update(); world.resize();
    if (world.renderer) world.renderer.render(world.scene, world.camera);
    else world.renderFallback(time);
  });
  requestAnimationFrame(frame);
}
status.textContent = `${data.points.length} pontos carregados · selecione um ponto para começar.`;
requestAnimationFrame(frame);
