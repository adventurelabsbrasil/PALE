export const SESSION_VERSION = "pale-session-v1";
export const INTERVENTION_TYPES = new Set(["solo", "mute", "select", "seek", "freeze", "create"]);

const clone = (value) => JSON.parse(JSON.stringify(value));

export function createBranchState(source = {}) {
  return {
    sourceId: "source",
    interventions: [],
    selectedEventId: null,
    muted: false,
    solo: false,
    frozen: false,
    createdEvents: [],
    ...clone(source),
  };
}

export function appendIntervention(branch, type, payload = {}, sequence = branch.interventions.length + 1) {
  if (!INTERVENTION_TYPES.has(type)) throw new TypeError(`unsupported intervention: ${type}`);
  const event = {
    id: `user-${String(sequence).padStart(6, "0")}`,
    sequence,
    type,
    payload: clone(payload),
  };
  const next = clone(branch);
  next.interventions.push(event);
  if (type === "solo") next.solo = Boolean(payload.enabled);
  if (type === "mute") next.muted = Boolean(payload.enabled);
  if (type === "select") next.selectedEventId = payload.eventId ?? null;
  if (type === "freeze") next.frozen = Boolean(payload.enabled);
  if (type === "create") next.createdEvents.push(clone(payload.event));
  return {branch: next, event};
}

export function replayInterventions(interventions = []) {
  let branch = createBranchState();
  const ordered = [...interventions].sort((a, b) => a.sequence - b.sequence);
  for (const item of ordered) {
    const result = appendIntervention(branch, item.type, item.payload, item.sequence);
    branch = result.branch;
  }
  return branch;
}

export function serializeSession({origin, branch, visual, seed, versions}) {
  if (!origin?.sha256 || !origin?.name) throw new TypeError("session origin needs name and sha256");
  return {
    session: SESSION_VERSION,
    origin: clone(origin),
    interventions: clone(branch.interventions),
    branch: {
      id: branch.sourceId === "source" ? "branch-001" : branch.sourceId,
      state: {
        selectedEventId: branch.selectedEventId,
        muted: branch.muted,
        solo: branch.solo,
        frozen: branch.frozen,
        createdEvents: clone(branch.createdEvents),
      },
    },
    visual: clone(visual ?? {}),
    seed,
    versions: clone(versions ?? {}),
  };
}

export function importSession(session) {
  if (!session || session.session !== SESSION_VERSION) throw new TypeError("unsupported PALE session");
  if (!session.origin?.name || !session.origin?.sha256) throw new TypeError("session origin is incomplete");
  const branch = replayInterventions(session.interventions ?? []);
  if (session.branch?.state) Object.assign(branch, clone(session.branch.state));
  return {session: clone(session), branch};
}
