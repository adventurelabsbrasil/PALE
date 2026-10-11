export const LENS_VERSION = "pale-lens-v1";

export const VISUAL_LENSES = Object.freeze([
  Object.freeze({id: "organism", label: "Organismo", description: "Memória contínua, energia e brilho formam um corpo único.", renderer: "organism-core-v1", config: Object.freeze({bloom: 1, height: 1, hue: 0})}),
  Object.freeze({id: "constellation", label: "Constelação", description: "Ataques e camadas se separam em pontos e relações.", renderer: "constellation-field-v1", config: Object.freeze({bloom: 1.45, height: 1.3, hue: 0.19})}),
]);

const clamp = (value) => Math.max(0, Math.min(1, Number.isFinite(value) ? value : 0));

export function getVisualLens(id = VISUAL_LENSES[0].id) {
  return VISUAL_LENSES.find((lens) => lens.id === id) ?? VISUAL_LENSES[0];
}

/** Map one shared timeline frame to lens-specific render parameters. */
export function renderLens(id, features = {}) {
  const lens = getVisualLens(id);
  const energy = clamp(features.rms), attack = clamp(features.attack), brightness = clamp(features.centroid), density = clamp(features.density), silence = clamp(features.silence);
  if (lens.id === "constellation") {
    return {lens: lens.id, radius: 0.55 + energy * 1.2, height: (0.12 + attack * 1.55 + density * 0.35) * lens.config.height, bloom: (0.045 + attack * 0.15 + energy * 0.035) * lens.config.bloom, hue: (brightness * 0.7 + lens.config.hue) % 1, opacity: 0.55 + (1 - silence) * 0.4};
  }
  return {lens: lens.id, radius: 0.7 + energy * 0.8, height: (0.18 + energy * 0.85 + brightness * 0.3) * lens.config.height, bloom: (0.045 + clamp(features.novelty) * 0.08 + energy * 0.025) * lens.config.bloom, hue: (0.62 - brightness * 0.42 + lens.config.hue + 1) % 1, opacity: 0.7 + (1 - silence) * 0.25};
}
