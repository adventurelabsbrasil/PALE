export const DIDACTIC_VERSION = "pale-didactic-v1";

export const SIGNAL_DOMAINS = Object.freeze([
  {id: "low", label: "Grave", signals: ["low"], description: "energia relativa abaixo de 250 Hz", limit: "não identifica uma nota, fonte ou instrumento específico"},
  {id: "impact", label: "Pulso/impacto", signals: ["attack", "flux", "rms"], description: "mudança de energia e fluxo espectral entre janelas", limit: "não confirma um evento musical ou uma causa física"},
  {id: "harmony", label: "Harmonia", signals: ["low", "mid", "high"], description: "distribuição de energia em regiões de frequência", limit: "não há rastreamento de notas ou acorde; harmonia não é determinada"},
  {id: "line", label: "Melodia/linha", signals: ["centroid", "novelty", "repeat"], description: "variação de brilho, novidade e recorrência ao longo do tempo", limit: "não há pitch tracking; melodia não é determinada"},
  {id: "texture", label: "Textura/ruído", signals: ["flatness", "spread", "high"], description: "espalhamento e planicidade do espectro", limit: "não identifica ruído como instrumento, gênero ou intenção"},
  {id: "space", label: "Silêncio/espaço", signals: ["silence", "rms", "stereo_width"], description: "energia baixa e, quando disponível, diferença entre canais", limit: "silêncio perceptual depende do limiar e não prova ausência de som"},
]);

export function provenanceFor(event) {
  const status = event.confidence === "hypothesis" ? "uncertain" : event.confidence;
  return event.provenance ?? {status, origin: event.origin, basis: event.origin === "synthetic" ? "parâmetros declarados pelo gerador" : "sinais acústicos medidos na janela", limits: ["leitura perceptual, não identificação factual", "instrumento, acorde e intenção não são afirmados sem evidência específica"]};
}

export function explainEvent(event, features = event) {
  return {version: DIDACTIC_VERSION, provenance: provenanceFor(event), signals: SIGNAL_DOMAINS.map((domain) => ({...domain, observations: Object.fromEntries(domain.signals.filter((signal) => signal in features).map((signal) => [signal, Number(features[signal].toFixed?.(4) ?? features[signal])]))})), not_claimed: ["instrumento", "acorde", "melodia", "intenção"]};
}
