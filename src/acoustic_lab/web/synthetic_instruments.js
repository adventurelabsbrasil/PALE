export const INSTRUMENTS = {
  oscillator: { label: "Oscilador", wave: "sine", filter: 5200, attack: .02, decay: .18, sustain: .55, release: .18, layer: "synthetic/oscillator" },
  bass: { label: "Baixo", wave: "sawtooth", filter: 900, attack: .035, decay: .24, sustain: .58, release: .3, layer: "synthetic/bass" },
  pluck: { label: "Pluck / piano", wave: "triangle", filter: 4200, attack: .008, decay: .32, sustain: .18, release: .45, layer: "synthetic/pluck" },
  percussion: { label: "Percussão", wave: "square", filter: 1800, attack: .003, decay: .12, sustain: .04, release: .12, layer: "synthetic/percussion" },
  texture: { label: "Ruído / textura", wave: "noise", filter: 2400, attack: .08, decay: .5, sustain: .35, release: .6, layer: "synthetic/texture" },
};

export function makeSyntheticEvent({ id, time, duration, pitch, energy, attack, brightness, instrument }) {
  const frequencyRegion = pitch < 53 ? "low" : pitch > 72 ? "high" : "mid";
  return {
    id, time, duration, pitch, layer: INSTRUMENTS[instrument].layer,
    energy: Math.max(0, Math.min(1, energy)), frequency_region: frequencyRegion,
    attack: Math.max(0, Math.min(1, attack)), brightness: Math.max(0, Math.min(1, brightness)),
    confidence: "confirmed", origin: "synthetic", instrument,
  };
}

function noiseBuffer(context) {
  const buffer = context.createBuffer(1, context.sampleRate * 2, context.sampleRate);
  const data = buffer.getChannelData(0);
  for (let i = 0; i < data.length; i++) data[i] = Math.random() * 2 - 1;
  return buffer;
}

export function createVoice(context, instrument, frequency, parameters, now) {
  const preset = INSTRUMENTS[instrument];
  const output = context.createGain(), filter = context.createBiquadFilter(), panner = context.createStereoPanner();
  const level = Math.max(.001, Math.min(.45, parameters.dynamics));
  const attack = Math.max(.003, parameters.attack ?? preset.attack), release = Math.max(.04, parameters.release ?? preset.release);
  filter.type = instrument === "texture" ? "bandpass" : instrument === "percussion" ? "highpass" : "lowpass";
  filter.frequency.value = Math.max(80, Math.min(12000, parameters.filter ?? preset.filter));
  filter.Q.value = instrument === "texture" ? 1.2 : .55;
  panner.pan.value = Math.max(-1, Math.min(1, parameters.pan));
  output.gain.setValueAtTime(.0001, now);
  output.gain.linearRampToValueAtTime(level, now + attack);
  output.gain.exponentialRampToValueAtTime(Math.max(.0001, level * preset.sustain), now + attack + preset.decay);
  filter.connect(panner).connect(output).connect(context.destination);
  const nodes = [];
  if (instrument === "texture" || instrument === "percussion") {
    const source = context.createBufferSource(); source.buffer = noiseBuffer(context); source.connect(filter); source.start(now); nodes.push(source);
  }
  if (instrument !== "texture") {
    const oscillator = context.createOscillator(); oscillator.type = preset.wave; oscillator.frequency.setValueAtTime(frequency, now); oscillator.connect(filter); oscillator.start(now); nodes.push(oscillator);
    if (instrument === "pluck") { const overtone = context.createOscillator(); overtone.type = "sine"; overtone.frequency.value = frequency * 2.01; const gain = context.createGain(); gain.gain.value = .22; overtone.connect(gain).connect(filter); overtone.start(now); nodes.push(overtone); }
  }
  return { output, stop(at = context.currentTime) { output.gain.cancelScheduledValues(at); output.gain.setTargetAtTime(.0001, at, release / 3); nodes.forEach(node => { try { node.stop(at + release); } catch {} }); } };
}
