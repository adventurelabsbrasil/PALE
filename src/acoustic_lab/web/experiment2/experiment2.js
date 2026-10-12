import * as THREE from "./vendor/three.module.min.js";
import { OrbitControls } from "./vendor/OrbitControls.js";
import { EffectComposer } from "./vendor/postprocessing/EffectComposer.js";
import { RenderPass } from "./vendor/postprocessing/RenderPass.js";
import { UnrealBloomPass } from "./vendor/postprocessing/UnrealBloomPass.js";
import { appendIntervention, createBranchState, importSession, serializeSession } from "./session_branch.js";
import { LENS_VERSION, VISUAL_LENSES, getVisualLens, renderLens } from "./visual_lenses.js";
import { DIDACTIC_VERSION, explainEvent, provenanceFor } from "./didactic.js";

const manifest = await fetch("manifest.json").then((r) => r.json());
let artifactAnalysis = manifest.analysis_artifact ? await fetch(manifest.analysis_artifact).then((r) => r.json()) : null;
const $ = (id) => document.getElementById(id);
const canvas = $("stage"), status = $("status"), playButton = $("play");
const seek = $("seek"), currentLabel = $("current"), durationLabel = $("duration");
const audioFile = $("audioFile"), fileName = $("fileName"), piano = $("piano");
const branchMode = $("branchMode"), branchStatus = $("branchStatus"), sessionFile = $("sessionFile");
const artifactFile = $("artifactFile"), saveArtifact = $("saveArtifact");
const observatoryPlot = $("observatoryPlot"), observatoryEvent = $("observatoryEvent");
const didacticToggle = $("didacticToggle"), didacticPanel = $("didacticPanel"), didacticStatus = $("didacticStatus");
const lensSelect = $("lensSelect"), lensCompare = $("lensCompare"), lensDescription = $("lensDescription"), lensVersion = $("lensVersion");
const inspector = $("inspector"), panelToggle = $("panelToggle"), panelClose = $("panelClose"), canvasHint = $("canvasHint");
const WINDOW = manifest.analysis.window_samples, HOP = manifest.analysis.hop_samples;
let renderer, composer, bloom, scene, camera, controls, spectrumLine, spectrumPoints, spectrumTrails, spectrumCloud, burstCloud, pulseShell, burstRing, spectralField, semanticWorld, persistentForm, eventDance, relationSignals;
let burstDirections;
let audioContext, audioBuffer, sourceNode, sourceGain, startedAt = 0, offset = 0, playing = false;
let selectedAudioBytes = null, selectedAudioName = "", selectedAudioSha256 = "";
let pianoEnergy = 0, pianoPulse = 0, pianoTime = 0, lastPianoHistory = 0, lastFrameTime = 0;
const pianoBand = new THREE.Vector3(0, 0, 1);
const pianoVoices = new Map();
let analysis = null, activeLensId = VISUAL_LENSES[0].id, currentFeatures = {rms: 0, low: 0, mid: 0, high: 0, centroid: 0, spread: 0, flatness: 0, flux: 0, attack: 0, density: 0, stereo_width: 0, silence: 1, repeat: 0, novelty: 0};
let selectedEventIndex = -1;
let didacticEnabled = false;
const sourceState = Object.freeze({id: "source", interventions: []});
let branchState = createBranchState({sourceId: "branch-001"}), activeWorld = "source";
let interventionSequence = 0;
const history = [], spectrumHistory = [], memoryWidth = 256, spectrumBins = 40, spectrumTrailRows = 14;
let lastSpectrumTime = 0;
let feedbackText = "", feedbackUntil = 0;
const clamp = (v, a = 0, b = 1) => Math.max(a, Math.min(b, v));
const lerp = (a, b, t) => a + (b - a) * t;
const formatTime = (s) => { const n = Math.max(0, Math.floor(s)); return `${String(Math.floor(n / 60)).padStart(2, "0")}:${String(n % 60).padStart(2, "0")}`; };
const safePercent = (value) => Number.isFinite(Number(value)) ? Math.round(Number(value) * 100) : 0;
const semanticColors = {low: "#6d8dff", impact: "#ff9fc9", harmony: "#b99cff", line: "#7de4ff", texture: "#ffc979", space: "#8a93a8"};
function semanticEntities() {
  if (analysis?.entities?.length) return analysis.entities;
  const layers = ["low", "impact", "harmony", "line", "texture", "space"];
  const events = analysis?.events ?? [];
  return layers.map((layer, index) => ({id: `entity-${layer}-fallback`, layer, confidence: "inferred", position: {x: Math.cos(index * Math.PI / 3) * 1.2, y: Math.sin(index * Math.PI / 3) * 1.2, z: 0}, energy: .35, event_ids: events.filter((event) => layer === "impact" ? event.layer === "pulse/impact" : event.frequency_region === layer).map((event) => event.id)}));
}
function rebuildSemanticWorld() {
  if (!scene) return;
  if (semanticWorld) scene.remove(semanticWorld);
  semanticWorld = new THREE.Group(); semanticWorld.name = "persistent-perceptual-entities";
  semanticWorld.userData = {entities: semanticEntities(), relations: analysis?.relations ?? []};
  scene.add(semanticWorld);
}
function createPersistentForm() {
  const count = 72, positions = new Float32Array(count * 3);
  const geometry = new THREE.BufferGeometry(); geometry.setAttribute("position", new THREE.BufferAttribute(positions, 3));
  const material = new THREE.LineBasicMaterial({color: "#a99cff", transparent: true, opacity: .34, blending: THREE.AdditiveBlending});
  const contour = new THREE.LineLoop(geometry, material);
  const core = new THREE.Mesh(new THREE.IcosahedronGeometry(.74, 2), new THREE.MeshBasicMaterial({color: "#655cc4", transparent: true, opacity: .12, wireframe: true, blending: THREE.AdditiveBlending}));
  persistentForm = new THREE.Group(); persistentForm.name = "persistent-form"; persistentForm.add(core, contour); persistentForm.userData = {contour, core, count}; scene.add(persistentForm);
}
function createEventDance() {
  const count = 56, directions = new Float32Array(count * 3), positions = new Float32Array(count * 3);
  for (let i = 0; i < count; i++) { const a = i * 2.39996, z = Math.sin(i * 1.73) * .92, r = Math.sqrt(1 - z * z); directions.set([Math.cos(a) * r, Math.sin(a) * r, z], i * 3); }
  const geometry = new THREE.BufferGeometry(); geometry.setAttribute("position", new THREE.BufferAttribute(positions, 3));
  eventDance = new THREE.Points(geometry, new THREE.PointsMaterial({color: "#ff9fc9", size: .028, transparent: true, opacity: 0, blending: THREE.AdditiveBlending, depthWrite: false})); eventDance.name = "event-dance"; eventDance.userData = {directions}; scene.add(eventDance);
  const relationGeometry = new THREE.BufferGeometry(); relationGeometry.setAttribute("position", new THREE.BufferAttribute(new Float32Array(24 * 3), 3));
  relationSignals = new THREE.LineSegments(relationGeometry, new THREE.LineBasicMaterial({color: "#8e86e8", transparent: true, opacity: 0, blending: THREE.AdditiveBlending})); relationSignals.name = "relation-signals"; scene.add(relationSignals);
}
function updatePersistentForm(seconds, time) {
  if (!semanticWorld || !persistentForm) return;
  const activeIds = new Set((analysis?.events ?? []).filter((event) => event.time <= seconds && seconds <= event.time + event.duration).map((event) => event.id));
  const silence = clamp(currentFeatures.silence), energy = clamp(currentFeatures.rms), attack = clamp(currentFeatures.attack);
  const memory = history.at(-1) ?? currentFeatures, contour = persistentForm.userData.contour.geometry.attributes.position.array;
  for (let i = 0; i < persistentForm.userData.count; i++) {
    const angle = i / persistentForm.userData.count * Math.PI * 2, harmonic = Math.sin(angle * 3 + time * .32) * .055 + Math.sin(angle * 7 - time * .18) * .025;
    const radius = (.69 + energy * .18 + (memory.novelty ?? 0) * .08) * (1 - silence * .42) + harmonic + attack * Math.sin(angle * 2 + time * 2.2) * .045;
    contour[i * 3] = Math.cos(angle) * radius; contour[i * 3 + 1] = Math.sin(angle) * radius * (.82 + currentFeatures.low * .18); contour[i * 3 + 2] = Math.sin(angle * 2 + time * .4) * (.08 + currentFeatures.mid * .1);
  }
  persistentForm.userData.contour.geometry.attributes.position.needsUpdate = true;
  persistentForm.scale.setScalar(.9 + energy * .22 + attack * .06); persistentForm.rotation.y = time * .08; persistentForm.rotation.x = Math.sin(time * .23) * .06;
  persistentForm.userData.contour.material.opacity = (.38 + energy * .18 + attack * .16) * (1 - silence * .68);
  persistentForm.userData.core.material.opacity = (.1 + energy * .07) * (1 - silence * .64);
  updateRelationSignals(activeIds, time);
}
function updateRelationSignals(activeIds, time) {
  if (!relationSignals) return;
  const relations = (semanticWorld?.userData.relations ?? []).filter((relation) => relation.event_ids?.some((id) => activeIds.has(id))).slice(0, 4);
  const positions = relationSignals.geometry.attributes.position.array; const entities = semanticWorld?.userData.entities ?? [];
  relations.forEach((relation, index) => { const source = entities.find((entity) => entity.id === relation.source)?.position ?? {x: -.3, y: 0, z: 0}; const target = entities.find((entity) => entity.id === relation.target)?.position ?? {x: .3, y: 0, z: 0}; const p = index * 6; positions[p] = source.x * .38; positions[p + 1] = source.y * .38; positions[p + 2] = source.z * .18 + .08; positions[p + 3] = target.x * .38; positions[p + 4] = target.y * .38; positions[p + 5] = target.z * .18 + .08; });
  for (let i = relations.length * 6; i < positions.length; i++) positions[i] = 0;
  relationSignals.geometry.attributes.position.needsUpdate = true; relationSignals.material.opacity = relations.length ? (.06 + clamp(currentFeatures.attack) * .08) * (.72 + Math.sin(time * 5) * .18) : 0;
}
function setFeedback(message, duration = 1800) { feedbackText = message; feedbackUntil = duration ? performance.now() + duration : 0; status.textContent = message; }
function renderTransportStatus() {
  if (feedbackText && (!feedbackUntil || performance.now() < feedbackUntil)) { status.textContent = feedbackText; return; }
  feedbackText = "";
  status.textContent = analysis ? (playing ? `Reproduzindo · repetição detectada: ${safePercent(currentFeatures.repeat)}` : "Pausado · arraste o mundo para observar") : artifactAnalysis ? "Análise local pronta · pressione Explorar" : "Pronto para analisar uma faixa";
}
function setPanelSection(section) {
  document.querySelectorAll("[data-panel-section]").forEach((element) => { element.hidden = element.dataset.panelSection !== section; });
  document.querySelectorAll("[data-panel-tab]").forEach((button) => { button.setAttribute("aria-selected", String(button.dataset.panelTab === section)); });
}
function openInspector() { inspector.hidden = false; panelToggle.setAttribute("aria-expanded", "true"); }
function closeInspector() { inspector.hidden = true; panelToggle.setAttribute("aria-expanded", "false"); }
panelToggle.addEventListener("click", () => { if (inspector.hidden) { openInspector(); } else { closeInspector(); } });
panelClose.addEventListener("click", closeInspector);
document.querySelectorAll("[data-panel-tab]").forEach((button) => button.addEventListener("click", () => { setPanelSection(button.dataset.panelTab); }));
setPanelSection("understand");

function activeState() { return activeWorld === "source" ? sourceState : branchState; }
function recordIntervention(type, payload = {}) {
  if (activeWorld === "source") { activeWorld = "branch"; branchMode.value = "branch"; }
  interventionSequence += 1;
  branchState = appendIntervention(branchState, type, payload, interventionSequence).branch;
  renderBranchState();
}
function renderBranchState() {
  branchStatus.textContent = `${activeWorld === "source" ? "Fonte" : "Ramificação"} · ${branchState.interventions.length} intervenção${branchState.interventions.length === 1 ? "" : "ões"}`;
  $("solo").setAttribute("aria-pressed", String(branchState.solo));
  $("mute").setAttribute("aria-pressed", String(branchState.muted));
  $("freeze").setAttribute("aria-pressed", String(branchState.frozen));
  $("solo").textContent = branchState.solo ? "Dessolar" : "Solo";
  $("mute").textContent = branchState.muted ? "Desmutar" : "Silenciar";
  $("freeze").textContent = branchState.frozen ? "Descongelar" : "Congelar";
}
function switchWorld(world) { activeWorld = world; branchMode.value = world; renderBranchState(); setFeedback(world === "source" ? "Fonte original · intacta" : "Minha exploração · alterações reversíveis"); }
function setupLenses() {
  for (const lens of VISUAL_LENSES) lensSelect.append(new Option(`${lens.label} · ${lens.renderer}`, lens.id));
  lensSelect.value = activeLensId; lensVersion.textContent = LENS_VERSION;
  lensSelect.addEventListener("change", () => { activeLensId = lensSelect.value; const lens = getVisualLens(activeLensId); lensDescription.textContent = `${lens.label}: ${lens.description}`; setFeedback(`Forma ${lens.label} · mesma linha do tempo`); drawLensComparison(currentTime()); });
  lensDescription.textContent = `${getVisualLens(activeLensId).label}: ${getVisualLens(activeLensId).description}`;
}
function sessionPayload() {
  return serializeSession({origin: {name: selectedAudioName || manifest.source.original_name, sha256: selectedAudioSha256 || manifest.source.sha256}, branch: branchState, visual: {offset, lens: activeLensId, didactic: didacticEnabled, camera: {position: camera?.position?.toArray?.() ?? [0, 0, 5.2], target: controls?.target?.toArray?.() ?? [0, 0, 0]}}, seed: manifest.visual.seed, versions: {experiment: manifest.experiment, contract: manifest.analysis.contract_version ?? "acoustic-v1", lens: LENS_VERSION, didactic: DIDACTIC_VERSION}});
}
function downloadSession() { const blob = new Blob([JSON.stringify(sessionPayload(), null, 2) + "\n"], {type: "application/json"}); const link = document.createElement("a"); link.href = URL.createObjectURL(blob); link.download = "pale-session.json"; link.click(); URL.revokeObjectURL(link.href); setFeedback("Sessão salva · replay determinístico disponível"); }
function artifactPayload() { if (!artifactAnalysis) throw new TypeError("analise local ainda não concluída"); return {artifact: "pale-artifact-v1", privacy: {audio_included: false, processing: "local-only", remote_upload: false}, manifest, analysis: artifactAnalysis, session: sessionPayload()}; }
function downloadArtifact() { const blob = new Blob([JSON.stringify(artifactPayload(), null, 2) + "\n"], {type: "application/json"}); const link = document.createElement("a"); link.href = URL.createObjectURL(blob); link.download = "pale-artifact.json"; link.click(); URL.revokeObjectURL(link.href); setFeedback("Artefato exportado · áudio permaneceu local"); }
async function loadSession(file) { const imported = importSession(JSON.parse(await file.text())); branchState = imported.branch; interventionSequence = branchState.interventions.length; activeWorld = "branch"; branchMode.value = "branch"; offset = imported.session.visual?.offset ?? 0; didacticToggle.checked = Boolean(imported.session.visual?.didactic); didacticEnabled = didacticToggle.checked; renderDidacticState(); if (imported.session.visual?.lens && getVisualLens(imported.session.visual.lens).id === imported.session.visual.lens) { activeLensId = imported.session.visual.lens; lensSelect.value = activeLensId; lensDescription.textContent = `${getVisualLens(activeLensId).label}: ${getVisualLens(activeLensId).description}`; } renderBranchState(); seek.value = offset; drawLensComparison(offset); setFeedback("Sessão aberta · minha exploração foi restaurada"); }
async function loadArtifact(file) { const imported = JSON.parse(await file.text()); if (imported.artifact !== "pale-artifact-v1" || imported.privacy?.remote_upload !== false) throw new TypeError("artefato PALE incompatível ou não local"); if (!imported.analysis?.identity || imported.manifest?.identity !== imported.analysis.identity) throw new TypeError("identidade do artefato inconsistente"); artifactAnalysis = imported.analysis; analysis = artifactAnalysis; seek.max = analysis.duration; durationLabel.textContent = formatTime(analysis.duration); rebuildSemanticWorld(); if (imported.session) await loadSession(new File([JSON.stringify(imported.session)], "pale-session.json", {type: "application/json"})); drawLensComparison(offset); setFeedback("Artefato aberto · linha do tempo reconstruída localmente"); }

function fft(re, im) {
  for (let i = 1, j = 0; i < re.length; i++) { let bit = re.length >> 1; for (; j & bit; bit >>= 1) j ^= bit; j ^= bit; if (i < j) { [re[i], re[j]] = [re[j], re[i]]; [im[i], im[j]] = [im[j], im[i]]; } }
  for (let len = 2; len <= re.length; len <<= 1) { const angle = -2 * Math.PI / len, wr0 = Math.cos(angle), wi0 = Math.sin(angle); for (let i = 0; i < re.length; i += len) { let wr = 1, wi = 0; for (let j = 0; j < len / 2; j++) { const u = re[i + j], k = i + j + len / 2, v = re[k] * wr - im[k] * wi, vi = re[k] * wi + im[k] * wr; re[i + j] = u + v; im[i + j] += vi; re[k] = u - v; im[k] -= vi; const next = wr * wr0 - wi * wi0; wi = wr * wi0 + wi * wr0; wr = next; } } }
}
function percentile(values, p) { const sorted = [...values].sort((a, b) => a - b); return sorted[Math.min(sorted.length - 1, Math.floor((sorted.length - 1) * p))] ?? 0; }
function robustNormalize(values) { const lo = percentile(values, .05), hi = percentile(values, .95), span = Math.max(hi - lo, 1e-8); return {lo, hi, values: values.map((v) => clamp((v - lo) / span))}; }

async function decodeAndAnalyze(audioBytes = null) {
  const bytes = audioBytes ?? await fetch(manifest.source.copied_path).then((r) => r.arrayBuffer());
  audioContext ??= new AudioContext(); audioBuffer = await audioContext.decodeAudioData(bytes.slice(0));
  const offline = new OfflineAudioContext(audioBuffer.numberOfChannels, audioBuffer.length, audioBuffer.sampleRate);
  const source = offline.createBufferSource(); source.buffer = audioBuffer; source.connect(offline.destination); source.start();
  const rendered = await offline.startRendering(), left = rendered.getChannelData(0), right = rendered.numberOfChannels > 1 ? rendered.getChannelData(1) : left;
  const mono = left.slice(); if (rendered.numberOfChannels > 1) for (let i = 0; i < mono.length; i++) mono[i] = (left[i] + right[i]) * .5;
  const frameCount = Math.max(1, Math.floor((mono.length - WINDOW) / HOP) + 1), raw = {rms: [], low: [], mid: [], high: [], centroid: [], spread: [], flatness: [], flux: [], attack: [], stereo_width: []}, spectra = [];
  const hann = new Float32Array(WINDOW); for (let i = 0; i < WINDOW; i++) hann[i] = .5 - .5 * Math.cos(2 * Math.PI * i / (WINDOW - 1));
  let previousSpectrum = new Float32Array(WINDOW / 2), previousRms = 0;
  for (let frame = 0; frame < frameCount; frame++) {
    if (frame % 24 === 0) { status.textContent = `Analisando áudio… ${Math.round(frame / Math.max(1, frameCount - 1) * 100)}%`; await new Promise((resolve) => requestAnimationFrame(resolve)); }
    const start = frame * HOP, re = new Float32Array(WINDOW), im = new Float32Array(WINDOW); let sum = 0, side = 0;
    for (let i = 0; i < WINDOW; i++) { const index = Math.min(mono.length - 1, start + i), sample = mono[index]; re[i] = sample * hann[i]; sum += sample * sample; side += (left[index] - right[index]) ** 2; }
    fft(re, im); let total = 0, low = 0, mid = 0, high = 0, weighted = 0, spreadSum = 0, logSum = 0, flux = 0; const magnitudes = new Float32Array(WINDOW / 2);
    for (let bin = 1; bin < WINDOW / 2; bin++) { const magnitude = Math.hypot(re[bin], im[bin]), hz = bin * audioBuffer.sampleRate / WINDOW; magnitudes[bin] = magnitude; total += magnitude; weighted += hz * magnitude; if (hz < 250) low += magnitude; else if (hz < 2000) mid += magnitude; else high += magnitude; flux += Math.max(0, magnitude - previousSpectrum[bin]); logSum += Math.log(magnitude + 1e-8); }
    const centroid = weighted / Math.max(total, 1e-8); for (let bin = 1; bin < WINDOW / 2; bin++) { const hz = bin * audioBuffer.sampleRate / WINDOW; spreadSum += (hz - centroid) ** 2 * magnitudes[bin]; }
    const maxMagnitude = Math.max(...magnitudes); const spectrumFrame = new Float32Array(spectrumBins); for (let bin = 0; bin < spectrumBins; bin++) { const sourceBin = 1 + Math.floor(bin / (spectrumBins - 1) * (WINDOW / 2 - 2)); spectrumFrame[bin] = Math.pow(magnitudes[sourceBin] / Math.max(maxMagnitude, 1e-8), .62); } spectra.push(spectrumFrame);
    const rms = Math.sqrt(sum / WINDOW); raw.rms.push(rms); raw.low.push(low / Math.max(total, 1e-8)); raw.mid.push(mid / Math.max(total, 1e-8)); raw.high.push(high / Math.max(total, 1e-8)); raw.centroid.push(centroid / (audioBuffer.sampleRate / 2)); raw.spread.push(Math.sqrt(spreadSum / Math.max(total, 1e-8)) / (audioBuffer.sampleRate / 2)); raw.flatness.push(Math.exp(logSum / Math.max(1, WINDOW / 2 - 1)) / Math.max(total / Math.max(1, WINDOW / 2 - 1), 1e-8)); raw.flux.push(flux / Math.max(total, 1e-8)); raw.attack.push(Math.max(0, rms - previousRms)); raw.stereo_width.push(Math.sqrt(side / WINDOW)); previousSpectrum = magnitudes; previousRms = rms;
  }
  const normalized = {}, ranges = {}; for (const [key, values] of Object.entries(raw)) { const result = robustNormalize(values); normalized[key] = result.values; ranges[key] = {p05: result.lo, p95: result.hi}; }
  const event = normalized.flux.map((v, i) => Math.max(v, normalized.attack[i])); normalized.density = event.map((_, i) => { let sum = 0; for (let j = Math.max(0, i - 21); j <= i; j++) sum += event[j]; return clamp(sum / Math.max(1, Math.min(i + 1, 22))); });
  const silenceFloor = Math.max(percentile(raw.rms, .05) * 1.35, percentile(raw.rms, .95) * .025); normalized.silence = raw.rms.map((v) => v <= silenceFloor ? 1 : 1 - clamp((v - silenceFloor) / Math.max(percentile(raw.rms, .95) - silenceFloor, 1e-8)));
  normalized.repeat = new Array(frameCount).fill(0); normalized.novelty = new Array(frameCount).fill(0);
  const descriptor = (i) => [normalized.rms[i], normalized.low[i], normalized.mid[i], normalized.high[i], normalized.centroid[i], normalized.spread[i], normalized.flatness[i], normalized.density[i]];
  const descriptors = Array.from({length: frameCount}, (_, i) => descriptor(i));
  for (let i = 0; i < frameCount; i++) { let best = 0; for (let j = Math.max(0, i - 300); j <= i - 18; j += 3) { const a = descriptors[i], b = descriptors[j]; let distance = 0; for (let k = 0; k < a.length; k++) distance += (a[k] - b[k]) ** 2; best = Math.max(best, 1 - Math.sqrt(distance / a.length)); } normalized.repeat[i] = clamp(best); normalized.novelty[i] = clamp(.25 + event[i] * .75 - best * .72); if (i % 48 === 0) { status.textContent = `Mapeando recorrências… ${Math.round(i / Math.max(1, frameCount - 1) * 100)}%`; await new Promise((resolve) => requestAnimationFrame(resolve)); } }
  const events = normalized.rms.map((energy, index) => { const bands = [raw.low[index], raw.mid[index], raw.high[index]], frequency_region = ["low", "mid", "high"][bands.indexOf(Math.max(...bands))] ?? "mid"; const timelineEvent = {id: `event-${String(index).padStart(6, "0")}`, time: index * HOP / audioBuffer.sampleRate, duration: Math.min(WINDOW, audioBuffer.length - index * HOP) / audioBuffer.sampleRate, layer: event[index] >= .55 ? "pulse/impact" : `${frequency_region}/energy`, energy, frequency_region, attack: normalized.attack[index], brightness: normalized.centroid[index], density: normalized.density[index], silence: normalized.silence[index], confidence: "inferred", origin: "audio"}; return {...timelineEvent, provenance: provenanceFor(timelineEvent), explanation: explainEvent(timelineEvent)}; });
  return {duration: audioBuffer.duration, sampleRate: audioBuffer.sampleRate, frameCount, raw, normalized, spectra, ranges, silenceFloor, events, didactic: {version: DIDACTIC_VERSION, enabled_by_default: false, not_claimed: ["instrumento", "acorde", "melodia", "intenção"]}};
}

function featuresAt(seconds) { if (!analysis) return currentFeatures; const series = analysis.normalized ?? analysis.features; const frameCount = analysis.frameCount ?? analysis.frame_count ?? Math.max(1, ...Object.values(series).filter(Array.isArray).map((values) => values.length)); const index = clamp(seconds / Math.max(analysis.duration, 1e-8) * (frameCount - 1), 0, frameCount - 1), lo = Math.floor(index), hi = Math.min(frameCount - 1, lo + 1), t = index - lo, out = {}; for (const key of Object.keys(series)) { const values = Array.isArray(series[key]) ? series[key] : []; out[key] = lerp(values[lo] ?? 0, values[hi] ?? 0, t); } return out; }
function observatoryValues(key) { return analysis?.features?.[key] ?? analysis?.normalized?.[key] ?? []; }
function renderDidacticState() { didacticStatus.textContent = didacticEnabled ? "ativada" : "desativada"; didacticPanel.hidden = !didacticEnabled; if (didacticEnabled && analysis?.events?.[selectedEventIndex]) renderDidacticEvent(analysis.events[selectedEventIndex]); }
function renderDidacticEvent(event) { const explanation = event.explanation ?? explainEvent(event); const provenance = explanation.provenance ?? provenanceFor(event); didacticPanel.innerHTML = `<span class="provenance">${provenance.status}</span>${provenance.basis}<div class="didactic-list">${explanation.signals.map((signal) => `<div class="didactic-item"><strong>${signal.label}</strong> · ${signal.description}<span class="didactic-limit">Limite: ${signal.limit}</span></div>`).join("")}</div><div class="didactic-limit">Não afirmado: ${explanation.not_claimed.join(", ")}. Esses dados não alteram o universo nem a linha do tempo.</div>`; }
function selectObservatoryEvent(seconds) { if (!analysis?.events?.length) return; const index = Math.max(0, Math.min(analysis.events.length - 1, Math.round(seconds / Math.max(analysis.duration, 1e-8) * (analysis.events.length - 1)))); selectedEventIndex = index; const event = analysis.events[index]; observatoryEvent.textContent = `${event.id} · ${formatTime(event.time)} · ${event.layer} · energia ${Math.round(event.energy * 100)}% · ataque ${Math.round(event.attack * 100)}% · proveniência ${provenanceFor(event).status}`; if (didacticEnabled) renderDidacticEvent(event); }
function drawObservatory(seconds = 0) {
  const context = observatoryPlot.getContext("2d"), width = observatoryPlot.width, height = observatoryPlot.height;
  context.clearRect(0, 0, width, height); context.fillStyle = "#080a12"; context.fillRect(0, 0, width, height);
  if (!analysis) { context.fillStyle = "#727694"; context.font = "11px system-ui"; context.fillText("Aguardando análise local…", 14, 28); return; }
  const rows = [["forma/energia", "rms", "#9d8cff"], ["brilho", "centroid", "#7de4ff"], ["ataque", "attack", "#ff9fc9"], ["densidade", "density", "#d9b3ff"], ["silêncio", "silence", "#727694"]];
  const top = 10, rowHeight = 30, plotLeft = 78, plotWidth = width - plotLeft - 10;
  const waveform = observatoryValues("waveform");
  if (waveform.length) { context.beginPath(); waveform.forEach((value, index) => { const x = plotLeft + index / Math.max(1, waveform.length - 1) * plotWidth, y = top + 15 - value * 10; index ? context.lineTo(x, y) : context.moveTo(x, y); }); context.strokeStyle = "#8b82d4"; context.globalAlpha = .45; context.stroke(); context.globalAlpha = 1; }
  rows.forEach(([label, key, color], row) => { const values = observatoryValues(key); const y0 = top + row * rowHeight + 15; context.fillStyle = "#8f96ad"; context.font = "9px system-ui"; context.fillText(label, 5, y0 + 3); context.strokeStyle = "#20263a"; context.beginPath(); context.moveTo(plotLeft, y0); context.lineTo(width - 10, y0); context.stroke(); if (!values.length) return; context.strokeStyle = color; context.beginPath(); values.forEach((value, index) => { const x = plotLeft + index / Math.max(1, values.length - 1) * plotWidth, y = y0 - clamp(value) * 12; index ? context.lineTo(x, y) : context.moveTo(x, y); }); context.stroke(); });
  const cursor = plotLeft + clamp(seconds / Math.max(analysis.duration, 1e-8)) * plotWidth; context.strokeStyle = "#fff"; context.globalAlpha = .9; context.beginPath(); context.moveTo(cursor, top - 2); context.lineTo(cursor, top + rows.length * rowHeight - 5); context.stroke(); context.globalAlpha = 1; selectObservatoryEvent(seconds);
}
function drawLensComparison(seconds = 0) {
  const context = lensCompare.getContext("2d"), width = lensCompare.width, height = lensCompare.height;
  context.clearRect(0, 0, width, height); context.fillStyle = "#080a12"; context.fillRect(0, 0, width, height);
  const duration = Math.max(analysis?.duration ?? 1, 1e-8), rows = VISUAL_LENSES.map((lens, row) => ({lens, row}));
  rows.forEach(({lens, row}) => { const y = 22 + row * 42; context.fillStyle = "#9da8bd"; context.font = "10px system-ui"; context.fillText(lens.label, 7, y - 8); context.strokeStyle = "#252b3e"; context.beginPath(); context.moveTo(86, y); context.lineTo(width - 8, y); context.stroke(); context.strokeStyle = row ? "#7de4ff" : "#b3a8ff"; context.beginPath(); for (let i = 0; i < 96; i++) { const t = i / 95, frame = featuresAt(t * duration), visual = renderLens(lens.id, frame), x = 86 + t * (width - 94), point = y - visual.height * 12; i ? context.lineTo(x, point) : context.moveTo(x, point); } context.stroke(); });
  const cursor = 86 + clamp(seconds / duration) * (width - 94); context.strokeStyle = "#fff"; context.beginPath(); context.moveTo(cursor, 8); context.lineTo(cursor, height - 7); context.stroke();
}
observatoryPlot.addEventListener("click", (event) => { if (!analysis) return; const rect = observatoryPlot.getBoundingClientRect(), ratio = clamp((event.clientX - rect.left) / rect.width); offset = ratio * analysis.duration; recordIntervention("seek", {seconds: offset}); if (playing) playFrom(offset); drawObservatory(offset); });
lensCompare.addEventListener("click", (event) => { if (!analysis) return; const rect = lensCompare.getBoundingClientRect(), ratio = clamp((event.clientX - rect.left) / rect.width); offset = ratio * analysis.duration; recordIntervention("seek", {seconds: offset}); if (playing) playFrom(offset); drawLensComparison(offset); });
const pianoNotes = [
  ["C4", 261.63, "a", false], ["C#4", 277.18, "w", true], ["D4", 293.66, "s", false], ["D#4", 311.13, "e", true], ["E4", 329.63, "d", false], ["F4", 349.23, "f", false], ["F#4", 369.99, "t", true], ["G4", 392.00, "g", false], ["G#4", 415.30, "y", true], ["A4", 440.00, "h", false], ["A#4", 466.16, "u", true], ["B4", 493.88, "j", false], ["C5", 523.25, "k", false], ["C#5", 554.37, "o", true], ["D5", 587.33, "l", false], ["D#5", 622.25, "p", true], ["E5", 659.25, ";", false]
];
function buildPiano() { for (const [name, frequency, key, black] of pianoNotes) { const button = document.createElement("button"); button.className = `key ${black ? "black" : "white"}`; button.dataset.key = key; button.dataset.note = name; button.setAttribute("aria-label", `${name} tecla ${key}`); button.innerHTML = `<span class="key-label">${key.toUpperCase()}</span>`; button.addEventListener("pointerdown", (event) => { event.preventDefault(); noteOn(name, frequency, button); }); button.addEventListener("pointerup", () => noteOff(name)); button.addEventListener("pointerleave", () => { if (pianoVoices.has(name)) noteOff(name); }); piano.append(button); } }
function noteOn(name, frequency, button) { if (pianoVoices.has(name)) return; audioContext ??= new AudioContext(); audioContext.resume(); const now = audioContext.currentTime, output = audioContext.createGain(), filter = audioContext.createBiquadFilter(); output.gain.setValueAtTime(.0001, now); output.gain.exponentialRampToValueAtTime(.16, now + .008); output.gain.exponentialRampToValueAtTime(.065, now + .22); output.gain.setTargetAtTime(.0001, now + .22, 1.35); filter.type = "lowpass"; filter.frequency.setValueAtTime(Math.min(5200, frequency * 10), now); filter.frequency.exponentialRampToValueAtTime(Math.max(1800, frequency * 4.2), now + .9); filter.Q.value = .55; filter.connect(output).connect(audioContext.destination);
  const oscillators = [], partials = [[1, 1], [2.002, .34], [3.006, .16], [4.014, .085], [5.03, .045], [6.05, .022]]; for (const [ratio, level] of partials) { const oscillator = audioContext.createOscillator(), partialGain = audioContext.createGain(); oscillator.type = "sine"; oscillator.frequency.value = frequency * ratio; partialGain.gain.value = level; oscillator.connect(partialGain).connect(filter); oscillator.start(now); oscillators.push(oscillator); }
  const noise = audioContext.createBufferSource(), noiseBuffer = audioContext.createBuffer(1, Math.floor(audioContext.sampleRate * .035), audioContext.sampleRate), noiseData = noiseBuffer.getChannelData(0); for (let i = 0; i < noiseData.length; i++) noiseData[i] = (Math.random() * 2 - 1) * (1 - i / noiseData.length); noise.buffer = noiseBuffer; const hammer = audioContext.createBiquadFilter(), hammerGain = audioContext.createGain(); hammer.type = "bandpass"; hammer.frequency.value = Math.min(5200, frequency * 5); hammer.Q.value = .8; hammerGain.gain.setValueAtTime(.045, now); hammerGain.gain.exponentialRampToValueAtTime(.0001, now + .035); noise.connect(hammer).connect(hammerGain).connect(output); noise.start(now);
  pianoVoices.set(name, {oscillators, noise, output, button}); button.classList.add("active"); const brightness = clamp((frequency - 220) / 500); pianoBand.set(Math.cos(brightness * Math.PI * 2) * .8, Math.sin(brightness * Math.PI * 2) * .8, .45); pianoPulse = Math.max(pianoPulse, .72); pianoEnergy = Math.max(pianoEnergy, .1); currentFeatures = {...currentFeatures, rms: .1, low: 1 - brightness * .5, mid: .28, high: brightness * .5, centroid: brightness, spread: .35, flatness: .08, flux: .3, attack: .35, density: .22, stereo_width: 0, silence: 0, repeat: .12, novelty: .2}; const liveEvent = {id: `synthetic-${name}-${interventionSequence + 1}`, time: pianoTime, duration: .35, layer: "synthetic/note", energy: .1, frequency_region: brightness < .33 ? "low" : brightness < .66 ? "mid" : "high", attack: .35, brightness, confidence: "confirmed", origin: "synthetic", pitch: Math.round(frequency)}; recordIntervention("create", {event: {...liveEvent, provenance: provenanceFor(liveEvent), explanation: explainEvent(liveEvent)}}); status.textContent = `Piano orgânico · ${name}`; }
function noteOff(name) { const voice = pianoVoices.get(name); if (!voice) return; const now = audioContext.currentTime; voice.output.gain.cancelScheduledValues(now); voice.output.gain.setTargetAtTime(.0001, now, .16); for (const oscillator of voice.oscillators) oscillator.stop(now + .8); voice.noise.stop(now + .04); voice.button.classList.remove("active"); pianoVoices.delete(name); }
function handlePianoKey(key, pressed) { const note = pianoNotes.find((item) => item[2] === key.toLowerCase()); if (!note) return; const button = piano.querySelector(`[data-key="${CSS.escape(note[2])}"]`); if (pressed) noteOn(note[0], note[1], button); else noteOff(note[0]); }
buildPiano(); addEventListener("keydown", (event) => { if (!event.repeat) handlePianoKey(event.key, true); }); addEventListener("keyup", (event) => handlePianoKey(event.key, false));
function createMemoryTexture() { const data = new Uint8Array(memoryWidth * 4), texture = new THREE.DataTexture(data, memoryWidth, 1, THREE.RGBAFormat); texture.needsUpdate = true; texture.magFilter = THREE.LinearFilter; texture.minFilter = THREE.LinearFilter; return texture; }
function spectrumAt(seconds) { if (!analysis?.spectra?.length) { const f = currentFeatures; return Float32Array.from({length: spectrumBins}, (_, i) => { const x = i / (spectrumBins - 1); return clamp((f.low ?? 0) * Math.exp(-x * 5) + (f.mid ?? 0) * Math.exp(-((x - .35) ** 2) * 18) + (f.high ?? 0) * Math.exp(-((x - .8) ** 2) * 24)); }); } const index = clamp(seconds / analysis.duration * (analysis.spectra.length - 1), 0, analysis.spectra.length - 1), lo = Math.floor(index), hi = Math.min(analysis.spectra.length - 1, lo + 1), t = index - lo, out = new Float32Array(spectrumBins); for (let i = 0; i < spectrumBins; i++) out[i] = lerp(analysis.spectra[lo][i], analysis.spectra[hi][i], t); return out; }
function createSpectrum() {
  const pointMaterial = (size, opacity) => new THREE.ShaderMaterial({vertexShader: "attribute vec3 color; varying vec3 vColor; uniform float uSize; void main(){vColor=color; vec4 mv=modelViewMatrix*vec4(position,1.0); gl_Position=projectionMatrix*mv; gl_PointSize=uSize*(260.0/max(1.0,-mv.z));}", fragmentShader: "varying vec3 vColor; uniform float uOpacity; void main(){float d=length(gl_PointCoord-.5); float alpha=(1.0-smoothstep(.34,.5,d))*uOpacity; gl_FragColor=vec4(vColor,alpha);}", uniforms: {uSize: {value: size}, uOpacity: {value: opacity}}, transparent: true, depthWrite: false});
  const currentPositions = new Float32Array(spectrumBins * 3), colors = new Float32Array(spectrumBins * 3); for (let i = 0; i < spectrumBins; i++) { const color = new THREE.Color().setHSL(.68 - i / spectrumBins * .62, .78, .62); colors.set([color.r, color.g, color.b], i * 3); }
  const lineGeometry = new THREE.BufferGeometry(); lineGeometry.setAttribute("position", new THREE.BufferAttribute(currentPositions, 3)); lineGeometry.setAttribute("color", new THREE.BufferAttribute(colors, 3)); spectrumLine = new THREE.Line(lineGeometry, new THREE.LineBasicMaterial({vertexColors: true, transparent: true, opacity: .9, blending: THREE.AdditiveBlending}));
  const pointGeometry = new THREE.BufferGeometry(); pointGeometry.setAttribute("position", new THREE.BufferAttribute(new Float32Array(spectrumBins * 3), 3)); pointGeometry.setAttribute("color", new THREE.BufferAttribute(colors.slice(), 3)); spectrumPoints = new THREE.Points(pointGeometry, pointMaterial(.075, .95));
  const cloudColors = new Float32Array(spectrumTrailRows * spectrumBins * 3); for (let row = 0; row < spectrumTrailRows; row++) cloudColors.set(colors, row * spectrumBins * 3); const cloudGeometry = new THREE.BufferGeometry(); cloudGeometry.setAttribute("position", new THREE.BufferAttribute(new Float32Array(spectrumTrailRows * spectrumBins * 3), 3)); cloudGeometry.setAttribute("color", new THREE.BufferAttribute(cloudColors, 3)); spectrumCloud = new THREE.Points(cloudGeometry, pointMaterial(.042, .72));
  const trailPositions = new Float32Array(spectrumTrailRows * (spectrumBins - 1) * 2 * 3); const trailGeometry = new THREE.BufferGeometry(); trailGeometry.setAttribute("position", new THREE.BufferAttribute(trailPositions, 3)); spectrumTrails = new THREE.LineSegments(trailGeometry, new THREE.LineBasicMaterial({color: "#817dff", transparent: true, opacity: .34, blending: THREE.AdditiveBlending}));
  spectralField = new THREE.Group(); spectralField.name = "spectral-field"; spectralField.position.set(0, .12, -.45); spectralField.scale.setScalar(1.18); spectralField.rotation.x = -.22; spectralField.add(spectrumTrails, spectrumLine, spectrumCloud, spectrumPoints); scene.add(spectralField);
  const burstCount = 48; burstDirections = new Float32Array(burstCount * 3); const burstPositions = new Float32Array(burstCount * 3); for (let i = 0; i < burstCount; i++) { const a = i * 2.39996, z = Math.sin(i * 1.73) * .92, r = Math.sqrt(1 - z * z); burstDirections.set([Math.cos(a) * r, Math.sin(a) * r, z], i * 3); }
  const burstGeometry = new THREE.BufferGeometry(); burstGeometry.setAttribute("position", new THREE.BufferAttribute(burstPositions, 3)); burstCloud = new THREE.Points(burstGeometry, new THREE.PointsMaterial({color: "#ff9fc9", size: .035, transparent: true, opacity: 0, blending: THREE.AdditiveBlending, depthWrite: false}));
  pulseShell = new THREE.Mesh(new THREE.IcosahedronGeometry(.72, 1), new THREE.MeshBasicMaterial({color: "#9c8cff", wireframe: true, transparent: true, opacity: 0, blending: THREE.AdditiveBlending, depthWrite: false}));
  burstRing = new THREE.Mesh(new THREE.TorusGeometry(.8, .01, 10, 72), new THREE.MeshBasicMaterial({color: "#7de4ff", transparent: true, opacity: 0, blending: THREE.AdditiveBlending, depthWrite: false}));
  scene.add(burstCloud, pulseShell, burstRing);
}
function updateSpectrum(time, seconds) {
  const values = spectrumAt(seconds), energy = clamp(currentFeatures.rms), attack = clamp(currentFeatures.attack), novelty = clamp(currentFeatures.novelty), flux = clamp(currentFeatures.flux); const current = spectrumLine.geometry.attributes.position.array, points = spectrumPoints.geometry.attributes.position.array; for (let i = 0; i < spectrumBins; i++) { const ratio = i / (spectrumBins - 1), x = (ratio - .5) * 4.8, y = values[i] * (2.25 + novelty * .75) - .18, z = Math.sin(time * .8 + ratio * Math.PI * 2) * (.08 + attack * .16); current[i * 3] = x; current[i * 3 + 1] = y; current[i * 3 + 2] = z; points[i * 3] = x; points[i * 3 + 1] = y; points[i * 3 + 2] = z + .025; }
  spectrumLine.geometry.attributes.position.needsUpdate = true; spectrumPoints.geometry.attributes.position.needsUpdate = true; if (time - lastSpectrumTime > .065) { spectrumHistory.unshift(values); if (spectrumHistory.length > spectrumTrailRows) spectrumHistory.pop(); lastSpectrumTime = time; } const trail = spectrumTrails.geometry.attributes.position.array, cloud = spectrumCloud.geometry.attributes.position.array; for (let row = 0; row < spectrumTrailRows; row++) { const frame = spectrumHistory[row] ?? values, z = -.06 - row * (.125 + energy * .025) + Math.sin(time * .3 + row * .31) * .025; for (let i = 0; i < spectrumBins - 1; i++) { const p = (row * (spectrumBins - 1) + i) * 6, x1 = (i / (spectrumBins - 1) - .5) * 4.8, x2 = ((i + 1) / (spectrumBins - 1) - .5) * 4.8; trail[p] = x1; trail[p + 1] = frame[i] * 1.8 - .18; trail[p + 2] = z; trail[p + 3] = x2; trail[p + 4] = frame[i + 1] * 1.8 - .18; trail[p + 5] = z; const cp = (row * spectrumBins + i) * 3; cloud[cp] = x1; cloud[cp + 1] = frame[i] * 2.25 - .18; cloud[cp + 2] = z; } const cp = (row * spectrumBins + spectrumBins - 1) * 3; cloud[cp] = 2.4; cloud[cp + 1] = frame[spectrumBins - 1] * 2.25 - .18; cloud[cp + 2] = z; } spectrumTrails.geometry.attributes.position.needsUpdate = true; spectrumCloud.geometry.attributes.position.needsUpdate = true; const silence = clamp(currentFeatures.silence); spectrumLine.material.opacity = (.055 + attack * .075) * (1 - silence * .78); spectrumTrails.material.opacity = (.012 + novelty * .045) * (1 - silence * .88); spectrumPoints.material.uniforms.uOpacity.value = (.12 + energy * .1) * (1 - silence * .68); spectrumCloud.material.uniforms.uOpacity.value = (.02 + energy * .04) * (1 - silence * .9);
  const rawImpact = clamp(attack * .95 + novelty * .7 + flux * .35), impact = clamp((rawImpact - .24) / .76) * (1 - silence * .8), pulse = .5 + .5 * Math.sin(time * 7), radius = .55 + impact * 1.65 + pulse * impact * .12, burst = burstCloud.geometry.attributes.position.array; for (let i = 0; i < burstDirections.length / 3; i++) { const wobble = 1 + Math.sin(time * 2 + i * .7) * .035; burst[i * 3] = burstDirections[i * 3] * radius * wobble; burst[i * 3 + 1] = burstDirections[i * 3 + 1] * radius * wobble; burst[i * 3 + 2] = burstDirections[i * 3 + 2] * radius * wobble; } burstCloud.geometry.attributes.position.needsUpdate = true; burstCloud.material.opacity = impact * (.015 + pulse * .035); pulseShell.scale.setScalar(.72 + impact * .7 + pulse * impact * .06); pulseShell.rotation.x = time * .22; pulseShell.rotation.y = time * .3; pulseShell.material.opacity = impact * (.012 + pulse * .035); burstRing.scale.setScalar(.72 + impact * .9 + pulse * impact * .08); burstRing.rotation.x = time * .35; burstRing.rotation.y = time * .25; burstRing.material.opacity = impact * (.02 + pulse * .06);
  const dancePositions = eventDance?.geometry.attributes.position.array, directions = eventDance?.userData.directions; if (dancePositions && directions) { const danceRadius = .72 + impact * 1.1 + pulse * impact * .08; for (let i = 0; i < directions.length / 3; i++) { const wobble = 1 + Math.sin(time * 2.4 + i * .7) * .04; dancePositions[i * 3] = directions[i * 3] * danceRadius * wobble; dancePositions[i * 3 + 1] = directions[i * 3 + 1] * danceRadius * wobble; dancePositions[i * 3 + 2] = directions[i * 3 + 2] * danceRadius * wobble; } eventDance.geometry.attributes.position.needsUpdate = true; eventDance.material.opacity = impact * (.04 + pulse * .12); }
}
function setupScene() {
  scene = new THREE.Scene(); scene.fog = new THREE.FogExp2("#050609", .055); camera = new THREE.PerspectiveCamera(45, 1, .1, 100); camera.position.set(0, .12, 4.35);
  renderer = new THREE.WebGLRenderer({canvas, antialias: true, alpha: false}); renderer.setPixelRatio(Math.min(devicePixelRatio, 1.75)); renderer.setClearColor("#050609", 1); renderer.toneMapping = THREE.ACESFilmicToneMapping; renderer.toneMappingExposure = 1.12;
  composer = new EffectComposer(renderer); composer.addPass(new RenderPass(scene, camera)); bloom = new UnrealBloomPass(new THREE.Vector2(1, 1), .28, .72, .52); composer.addPass(bloom); controls = new OrbitControls(camera, canvas); controls.enableDamping = true; controls.autoRotate = true; controls.autoRotateSpeed = .5; controls.minDistance = 2.2; controls.maxDistance = 10;
  createSpectrum(); createPersistentForm(); createEventDance(); rebuildSemanticWorld();
  const key = new THREE.PointLight("#786dff", 5, 8); key.position.set(2, 1, 3); const fill = new THREE.PointLight("#ff7bce", 3, 6); fill.position.set(-2, -1, 2); scene.add(key, fill); resize(); addEventListener("resize", resize);
}
function resize() { if (!renderer) return; const rect = canvas.getBoundingClientRect(); renderer.setSize(rect.width, rect.height, false); composer.setSize(rect.width, rect.height); camera.aspect = rect.width / Math.max(1, rect.height); camera.updateProjectionMatrix(); }
function setVisuals(seconds, time) { currentFeatures = featuresAt(seconds); const visual = renderLens(activeLensId, currentFeatures); bloom.strength = .16 + visual.bloom + clamp(currentFeatures.attack) * .28; spectralField.rotation.z = Math.sin(time * .18) * .06; spectralField.rotation.y = time * (.045 + clamp(currentFeatures.rms) * .08); scene.rotation.y += (visual.hue - scene.rotation.y * .01) * .0004; updatePersistentForm(seconds, time); updateSpectrum(time, seconds); }
function pushHistory(seconds) { const sample = {...featuresAt(seconds)}; if (!history.length || seconds - history.at(-1).seconds > .045) { sample.seconds = seconds; history.push(sample); if (history.length > memoryWidth) history.shift(); } }
async function start() { if (!analysis) { setFeedback(artifactAnalysis ? "Preparando faixa local…" : "Analisando faixa local…", 0); if (artifactAnalysis) { const bytes = selectedAudioBytes ?? await fetch(manifest.source.copied_path).then((r) => r.arrayBuffer()); audioContext ??= new AudioContext(); audioBuffer = await audioContext.decodeAudioData(bytes.slice(0)); analysis = artifactAnalysis; } else { analysis = await decodeAndAnalyze(selectedAudioBytes); } rebuildSemanticWorld(); seek.max = analysis.duration; durationLabel.textContent = formatTime(analysis.duration); setFeedback("Faixa pronta · o mundo vai reagir", 1200); } if (!audioBuffer) { const bytes = selectedAudioBytes ?? await fetch(manifest.source.copied_path).then((r) => r.arrayBuffer()); audioContext ??= new AudioContext(); audioBuffer = await audioContext.decodeAudioData(bytes.slice(0)); } if (audioContext.state === "suspended") await audioContext.resume(); playFrom(offset); }
function stopSource() { if (sourceNode) { try { sourceNode.stop(); } catch {} sourceNode.disconnect(); sourceNode = null; } }
function playFrom(seconds) { stopSource(); offset = clamp(seconds, 0, analysis.duration); sourceNode = audioContext.createBufferSource(); sourceNode.buffer = audioBuffer; sourceGain = audioContext.createGain(); sourceGain.gain.value = branchState.muted ? 0 : .82; sourceNode.connect(sourceGain).connect(audioContext.destination); startedAt = audioContext.currentTime; sourceNode.start(0, offset); playing = true; playButton.textContent = "Pausar"; canvasHint.classList.add("hidden"); sourceNode.onended = () => { if (playing && audioContext.currentTime - startedAt + offset >= analysis.duration - .05) { playing = false; offset = analysis.duration; playButton.textContent = "Explorar"; } }; }
function currentTime() { return playing ? clamp(offset + audioContext.currentTime - startedAt, 0, analysis?.duration ?? 0) : offset; }
function pause() { offset = currentTime(); stopSource(); playing = false; playButton.textContent = "Continuar"; }
function reset() { pause(); offset = 0; history.length = 0; spectrumHistory.length = 0; }
audioFile.addEventListener("change", async () => { const file = audioFile.files?.[0]; if (!file) return; try { pause(); selectedAudioBytes = await file.arrayBuffer(); selectedAudioName = file.name; selectedAudioSha256 = Array.from(new Uint8Array(await crypto.subtle.digest("SHA-256", selectedAudioBytes)), (byte) => byte.toString(16).padStart(2, "0")).join(""); artifactAnalysis = null; fileName.textContent = `${file.name} · lendo localmente…`; analysis = null; audioBuffer = null; offset = 0; seek.value = 0; durationLabel.textContent = "00:00"; history.length = 0; await decodeAndAnalyze(selectedAudioBytes); rebuildSemanticWorld(); seek.max = analysis.duration; durationLabel.textContent = formatTime(analysis.duration); fileName.textContent = `${file.name} · pronto localmente`; setFeedback("Faixa pronta · pressione Explorar", 0); } catch (error) { fileName.textContent = "Não foi possível ler essa faixa"; setFeedback(`Falha na faixa: ${error.message}`, 0); } });
playButton.addEventListener("click", async () => { try { if (!analysis || !playing) await start(); else pause(); } catch (error) { setFeedback(`Falha na faixa: ${error.message}`, 0); } });
$("restart").addEventListener("click", async () => { reset(); if (analysis) await start(); }); seek.addEventListener("input", () => { offset = Number(seek.value); recordIntervention("seek", {seconds: offset}); if (playing) playFrom(offset); }); $("resetCamera").addEventListener("click", () => { controls.reset(); camera.position.set(0, 0, 5.2); controls.target.set(0, 0, 0); setFeedback("Mundo centralizado"); });
branchMode.addEventListener("change", () => switchWorld(branchMode.value));
$("solo").addEventListener("click", () => recordIntervention("solo", {enabled: !branchState.solo}));
$("mute").addEventListener("click", () => { recordIntervention("mute", {enabled: !branchState.muted}); if (sourceGain) sourceGain.gain.setTargetAtTime(branchState.muted ? 0 : .82, audioContext.currentTime, .015); });
$("freeze").addEventListener("click", () => { recordIntervention("freeze", {enabled: !branchState.frozen}); if (branchState.frozen) pause(); });
$("createEvent").addEventListener("click", () => { const userEvent = {id: `user-event-${interventionSequence + 1}`, time: currentTime(), duration: .5, layer: "user/intervention", energy: currentFeatures.rms ?? 0, frequency_region: "mid", attack: currentFeatures.attack ?? 0, brightness: currentFeatures.centroid ?? 0, confidence: "hypothesis", origin: "synthetic"}; recordIntervention("create", {event: {...userEvent, provenance: provenanceFor(userEvent), explanation: explainEvent(userEvent)}}); });
$("saveSession").addEventListener("click", downloadSession);
saveArtifact.addEventListener("click", () => { try { downloadArtifact(); } catch (error) { status.textContent = `Falha ao exportar artefato: ${error.message}`; } });
sessionFile.addEventListener("change", async () => { if (!sessionFile.files?.[0]) return; try { await loadSession(sessionFile.files[0]); } catch (error) { status.textContent = `Falha ao reimportar sessão: ${error.message}`; } });
artifactFile.addEventListener("change", async () => { if (!artifactFile.files?.[0]) return; try { await loadArtifact(artifactFile.files[0]); } catch (error) { status.textContent = `Falha ao reimportar artefato: ${error.message}`; } });
didacticToggle.addEventListener("change", () => { didacticEnabled = didacticToggle.checked; renderDidacticState(); setFeedback(didacticEnabled ? "Explicações ativadas · universo intacto" : "Explicações desativadas · universo intacto"); });
setupScene();
function frame(now) { const seconds = currentTime(), dt = Math.min(.1, Math.max(0, now / 1000 - lastFrameTime)); lastFrameTime = now / 1000; pianoTime += dt; pianoPulse *= Math.pow(.015, dt); if (pianoVoices.size) pianoEnergy = Math.min(.18, pianoEnergy + dt * .12); else pianoEnergy *= Math.pow(.035, dt); if (analysis) { setVisuals(seconds, now / 1000); if (playing) pushHistory(seconds); seek.value = seconds; currentLabel.textContent = formatTime(seconds); renderTransportStatus(); } else if (pianoEnergy > .008) { currentFeatures = {...currentFeatures, rms: pianoEnergy, flux: pianoEnergy * .45, attack: pianoEnergy * .35, density: pianoEnergy * .22, silence: 1 - pianoEnergy * 2, novelty: Math.min(.3, pianoEnergy * 1.4), repeat: .12}; setVisuals(0, now / 1000); if (pianoTime - lastPianoHistory > .045) { history.push({...currentFeatures, seconds: pianoTime}); if (history.length > memoryWidth) history.shift(); lastPianoHistory = pianoTime; } if (!feedbackText) status.textContent = `Piano · ${pianoVoices.size} tecla${pianoVoices.size === 1 ? "" : "s"}`; } else { setVisuals(0, now / 1000); renderTransportStatus(); } drawObservatory(seconds); controls.update(); composer.render(); requestAnimationFrame(frame); }
setupLenses(); fileName.textContent = artifactAnalysis ? `${manifest.source.original_name} · processado localmente` : "Nenhuma faixa carregada"; if (artifactAnalysis?.duration) { seek.max = artifactAnalysis.duration; durationLabel.textContent = formatTime(artifactAnalysis.duration); } status.textContent = artifactAnalysis ? "Análise local pronta · pressione Explorar" : "Pronto para analisar uma faixa"; renderBranchState(); drawLensComparison(0); requestAnimationFrame(frame);
