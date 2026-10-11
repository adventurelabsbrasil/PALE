import * as THREE from "./vendor/three.module.min.js";
import { OrbitControls } from "./vendor/OrbitControls.js";

const data = await fetch("experience_data.json").then((response) => response.json());
const playButton = document.querySelector("#play");
const audioStatus = document.querySelector("#audio-status");
const timeline = document.querySelector("#timeline");
const timeLabel = document.querySelector("#time");
const selectedLabel = document.querySelector("#selected");
const acousticLabel = document.querySelector("#acoustic");
const status = document.querySelector("#status");
const motion = document.querySelector("#motion");
const autoCamera = document.querySelector("#auto-camera");
const layer = document.querySelector("#layer");
const audioElement = document.createElement("audio");
audioElement.src = data.audio_url;
timeline.max = Math.max(0, data.points.length - 1);
document.querySelector("#metrics").textContent = `${data.metrics.windows} janelas · gap médio entre mundos ${data.metrics.world_gap_mean.toFixed(5)}`;

const active = {index: 0};
const audioMotion = {amplitude: 0};
let audioContext = null;
let audioBuffer = null;
let sourceNode = null;
let gainNode = null;
let analyser = null;
let frequencyData = null;
let playing = false;
let startedAt = 0;
let pauseOffset = 0;
const worlds = [];

function makeWorld(canvas, key, color) {
  const scene = new THREE.Scene(); scene.background = new THREE.Color("#081018");
  const camera = new THREE.PerspectiveCamera(48, 1, .01, 100); camera.position.set(0, 0, 4.2);
  const renderer = new THREE.WebGLRenderer({canvas, antialias: true}); renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
  const controls = new OrbitControls(camera, canvas); controls.enableDamping = true; controls.minDistance = .45; controls.maxDistance = 16; controls.autoRotateSpeed = .45;
  const positions = new Float32Array(data.points.length * 3);
  const acousticOpacity = new Float32Array(data.points.length);
  const pointColors = new Float32Array(data.points.length * 3);
  for (const [i, point] of data.points.entries()) {
    for (let axis = 0; axis < 3; axis++) positions[i * 3 + axis] = point[key][axis] * 1.45;
    const acoustic = point.acoustic ?? {rms: 0, centroid: 0};
    acousticOpacity[i] = .04 + acoustic.rms * .88;
    const pointColor = new THREE.Color().setHSL(key === "world_a" ? .54 + acoustic.centroid * .22 : .04 + acoustic.centroid * .24, .88, .56);
    pointColor.toArray(pointColors, i * 3);
  }
  const geometry = new THREE.BufferGeometry(); geometry.setAttribute("position", new THREE.BufferAttribute(positions, 3));
  geometry.setAttribute("aAcousticOpacity", new THREE.BufferAttribute(acousticOpacity, 1));
  geometry.setAttribute("aColor", new THREE.BufferAttribute(pointColors, 3));
  const material = new THREE.ShaderMaterial({
    uniforms: {uColor: {value: new THREE.Color(color)}, uExploratory: {value: 0}, uSize: {value: .055}},
    vertexShader: `attribute float aAcousticOpacity;attribute vec3 aColor;varying float vAcousticOpacity;varying vec3 vColor;uniform float uSize;void main(){vAcousticOpacity=aAcousticOpacity;vColor=aColor;vec4 mvPosition=modelViewMatrix*vec4(position,1.0);gl_PointSize=uSize*(300.0/-mvPosition.z);gl_Position=projectionMatrix*mvPosition;}`,
    fragmentShader: `uniform vec3 uColor;uniform float uExploratory;varying float vAcousticOpacity;varying vec3 vColor;void main(){vec2 p=gl_PointCoord-vec2(.5);if(dot(p,p)>.25)discard;float alpha=mix(.86,vAcousticOpacity,uExploratory);vec3 color=mix(uColor,vColor,uExploratory);gl_FragColor=vec4(color,alpha);}`,
    transparent: true, depthWrite: false,
  });
  const cloud = new THREE.Points(geometry, material); scene.add(cloud);
  const line = new THREE.Line(new THREE.BufferGeometry(), new THREE.LineBasicMaterial({color, transparent: true, opacity: key === "world_a" ? .7 : .3}));
  line.geometry.setAttribute("position", new THREE.BufferAttribute(new Float32Array(positions), 3)); scene.add(line);
  const ribbon = new THREE.Line(new THREE.BufferGeometry(), new THREE.LineBasicMaterial({color, transparent: true, opacity: key === "world_a" ? .22 : .12})); scene.add(ribbon);
  const marker = new THREE.Mesh(new THREE.SphereGeometry(.09, 18, 12), new THREE.MeshBasicMaterial({color})); scene.add(marker);
  const halo = new THREE.Mesh(new THREE.SphereGeometry(.17, 20, 14), new THREE.MeshBasicMaterial({color, transparent: true, opacity: .15, blending: THREE.AdditiveBlending})); scene.add(halo);
  const burstGeometry = new THREE.BufferGeometry();
  burstGeometry.setAttribute("position", new THREE.BufferAttribute(new Float32Array(24 * 3), 3));
  const burst = new THREE.Points(burstGeometry, new THREE.PointsMaterial({color, size: .075, transparent: true, opacity: 0, blending: THREE.AdditiveBlending, depthWrite: false})); scene.add(burst);
  const trail = new THREE.Line(new THREE.BufferGeometry(), new THREE.LineBasicMaterial({color, transparent: true, opacity: .75})); scene.add(trail);
  const trailGlow = new THREE.Line(new THREE.BufferGeometry(), new THREE.LineBasicMaterial({color, transparent: true, opacity: .16, linewidth: 3})); scene.add(trailGlow);
  const branchPositions = new Float32Array(positions.length * 3);
  for (let i = 0; i < positions.length; i += 3) { branchPositions[i] = positions[i] + Math.sin(i) * .018; branchPositions[i + 1] = positions[i + 1] + Math.cos(i * .7) * .018; branchPositions[i + 2] = positions[i + 2] + Math.sin(i * .37) * .018; }
  const branches = new THREE.Points(new THREE.BufferGeometry(), new THREE.PointsMaterial({color, size: .025, transparent: true, opacity: key === "world_b" ? .46 : .08}));
  branches.geometry.setAttribute("position", new THREE.BufferAttribute(branchPositions, 3)); scene.add(branches);
  function resize() { const rect = canvas.getBoundingClientRect(); if (!rect.width || !rect.height) return; renderer.setSize(rect.width, rect.height, false); camera.aspect = rect.width / rect.height; camera.updateProjectionMatrix(); }
  function reset() { camera.position.set(0, 0, 4.2); controls.target.set(0, 0, 0); controls.reset(); }
  return {key, scene, camera, renderer, controls, cloud, line, ribbon, marker, halo, burst, trail, trailGlow, branches, base: positions.slice(), baseColor: new THREE.Color(color), resize, reset};
}

worlds.push(makeWorld(document.querySelector("#worldA"), "world_a", "#52c7ff"));
worlds.push(makeWorld(document.querySelector("#worldB"), "world_b", "#f5b96b"));

function updateIndex(index) {
  active.index = Math.max(0, Math.min(data.points.length - 1, Number(index) || 0));
  timeline.value = active.index;
  const point = data.points[active.index];
  timeLabel.textContent = `janela ${point.window} · ${point.start_seconds.toFixed(3)} s`;
  selectedLabel.textContent = `janela ${point.window} · A [${point.world_a.map((v) => v.toFixed(4)).join(", ")}] · B [${point.world_b.map((v) => v.toFixed(4)).join(", ")}]`;
  const acoustic = point.acoustic;
  acousticLabel.textContent = acoustic ? `sinais locais · volume ${acoustic.rms.toFixed(3)} · centro ${acoustic.centroid.toFixed(3)} · dispersão ${acoustic.spread.toFixed(3)} · mudança ${acoustic.flux.toFixed(3)} · ataque ${acoustic.attack.toFixed(3)}` : "";
  for (const world of worlds) { const value = point[world.key]; world.marker.position.set(value[0] * 1.45, value[1] * 1.45, value[2] * 1.45); world.burst.position.copy(world.marker.position); }
}

timeline.addEventListener("input", () => { if (playing) pausePlayback(); pauseOffset = data.points[Number(timeline.value)].start_seconds; updateIndex(timeline.value); });
document.querySelector("#reset").addEventListener("click", () => worlds.forEach((world) => world.reset()));
document.querySelectorAll("[data-view]").forEach((button) => button.addEventListener("click", () => {
  document.body.dataset.view = button.dataset.view;
  document.querySelectorAll("[data-view]").forEach((item) => item.setAttribute("aria-pressed", String(item === button)));
  worlds.forEach((world) => world.resize());
}));
layer.addEventListener("change", () => {
  document.body.dataset.layer = layer.value;
  document.querySelector("#layer-description").style.display = layer.value === "semantic" ? "none" : "inline";
  status.textContent = layer.value === "semantic" ? "Camada exploratória ativa · hipóteses locais" : `${data.points.length} janelas · áudio pronto`;
});

function currentTime() { return playing ? Math.min(audioBuffer.duration, audioContext.currentTime - startedAt) : pauseOffset; }
function pausePlayback() { pauseOffset = currentTime(); sourceNode?.stop(); sourceNode = null; playing = false; playButton.textContent = "Continuar áudio"; audioStatus.textContent = `pausado em ${pauseOffset.toFixed(2)} s`; }
async function togglePlayback() {
  try {
    if (!audioContext) audioContext = new AudioContext();
    if (audioContext.state === "suspended") await audioContext.resume();
    if (!audioBuffer) { status.textContent = "Decodificando áudio local…"; audioBuffer = await audioContext.decodeAudioData(await (await fetch(data.audio_url)).arrayBuffer()); }
    if (playing) { pausePlayback(); return; }
    analyser ??= audioContext.createAnalyser(); analyser.fftSize = 512; frequencyData ??= new Uint8Array(analyser.frequencyBinCount);
    gainNode ??= audioContext.createGain(); gainNode.gain.value = .18;
    sourceNode = audioContext.createBufferSource(); sourceNode.buffer = audioBuffer; sourceNode.connect(analyser).connect(gainNode).connect(audioContext.destination);
    sourceNode.onended = () => { if (playing && currentTime() >= audioBuffer.duration - .02) { pauseOffset = 0; playing = false; playButton.textContent = "Reiniciar áudio"; audioStatus.textContent = "áudio concluído"; } };
    sourceNode.start(0, pauseOffset); startedAt = audioContext.currentTime - pauseOffset; playing = true; playButton.textContent = "Pausar áudio"; audioStatus.textContent = "áudio ativo"; status.textContent = "Áudio ativo · marcador sincronizado com a janela";
  } catch (error) {
    status.textContent = "Não foi possível decodificar o áudio neste navegador.";
    audioStatus.textContent = "erro de reprodução";
    console.error(error);
  }
}
playButton.addEventListener("click", togglePlayback);

function frame(seconds) {
  if (playing) updateIndex(Math.floor(currentTime() / data.contract.step_seconds));
  if (analyser && frequencyData) { analyser.getByteFrequencyData(frequencyData); const sum = frequencyData.reduce((total, value) => total + value * value, 0) / frequencyData.length; audioMotion.amplitude += (Math.min(1, Math.sqrt(sum) / 180) - audioMotion.amplitude) * .12; }
  const trailStart = Math.max(0, active.index - 42);
  const acoustic = data.points[active.index].acoustic ?? {rms: 0, centroid: 0, spread: 0, flux: 0, attack: 0};
  const exploratory = layer.value === "semantic";
  for (const [worldIndex, world] of worlds.entries()) {
    world.controls.autoRotate = autoCamera.checked;
    world.controls.update();
    const scale = motion.checked ? 1 + audioMotion.amplitude * (.08 + worldIndex * .015) : 1;
    const signalScale = exploratory ? 1 + acoustic.rms * .28 : 1;
    world.cloud.scale.setScalar(scale);
    world.cloud.scale.multiplyScalar(signalScale);
    world.branches.scale.setScalar((motion.checked ? 1 + audioMotion.amplitude * (.16 + worldIndex * .08) : 1) * (exploratory ? 1 + acoustic.flux * .35 : 1));
    world.marker.visible = !exploratory;
    world.halo.visible = !exploratory;
    world.marker.scale.setScalar(1 + audioMotion.amplitude * .8);
    world.halo.scale.setScalar(1 + audioMotion.amplitude * 2.2);
    const hue = worldIndex === 0 ? .54 + acoustic.centroid * .08 : .075 + acoustic.centroid * .08;
    world.cloud.material.uniforms.uColor.value.setHSL(hue, exploratory ? .82 : world.baseColor.getHSL({}).s, .62);
    world.cloud.material.uniforms.uExploratory.value = exploratory ? 1 : 0;
    world.marker.material.color.setHSL(hue, .9, .68);
    world.halo.material.color.setHSL(hue, .9, .65);
    world.cloud.position.z = exploratory ? (acoustic.spread - .5) * .16 : 0;
    world.branches.position.z = exploratory ? (acoustic.spread - .5) * .2 : 0;
    world.branches.material.opacity = exploratory ? .16 + acoustic.flux * .55 : (world.key === "world_b" ? .46 : .08);
    const onset = data.points[active.index].acoustic?.onset;
    const onsetStrength = data.points[active.index].acoustic?.onset_strength ?? 0;
    const pulse = .5 + .5 * Math.sin(seconds * 18);
    world.burst.visible = exploratory && onset;
    world.burst.scale.setScalar(1 + pulse * (1.5 + onsetStrength * 3));
    world.burst.material.opacity = exploratory && onset ? .25 + onsetStrength * .85 : 0;
    world.burst.material.color.setHSL(hue, .95, .7);
    const burstPositions = world.burst.geometry.attributes.position.array;
    for (let i = 0; i < 24; i++) {
      const angle = i * 2.399;
      const radius = .06 + (i % 5) * .018;
      burstPositions[i * 3] = Math.cos(angle) * radius;
      burstPositions[i * 3 + 1] = Math.sin(angle * 1.37) * radius;
      burstPositions[i * 3 + 2] = Math.cos(angle * .71) * radius;
    }
    world.burst.geometry.attributes.position.needsUpdate = true;
    const trailPoints = data.points.slice(trailStart, active.index + 1).map((point) => new THREE.Vector3(...point[world.key].map((v) => v * 1.45)));
    const trailArray = new Float32Array(trailPoints.length * 3);
    trailPoints.forEach((point, i) => point.toArray(trailArray, i * 3));
    world.trail.geometry.setAttribute("position", new THREE.BufferAttribute(trailArray, 3)); world.trail.geometry.computeBoundingSphere();
    world.trailGlow.geometry.setAttribute("position", new THREE.BufferAttribute(trailArray, 3)); world.trailGlow.geometry.computeBoundingSphere();
    world.trail.material.opacity = trailPoints.length ? .14 + (trailPoints.length / 43) * .64 : 0;
    world.trailGlow.material.opacity = trailPoints.length ? .06 + (trailPoints.length / 43) * .14 : 0;
    world.halo.position.copy(world.marker.position);
    if (world.key === "world_b") world.branches.rotation.y = motion.checked ? Math.sin(seconds * .22) * .05 : 0;
    if (motion.checked) world.camera.rotation.z = Math.sin(seconds * .12 + worldIndex) * .002;
    else world.camera.rotation.z = 0;
    world.renderer.render(world.scene, world.camera);
  }
  requestAnimationFrame(frame);
}
status.textContent = `${data.points.length} janelas · áudio pronto`;
updateIndex(0); requestAnimationFrame(frame);
