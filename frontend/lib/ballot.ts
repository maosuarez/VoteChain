// Ballot rules (Balón de Oro): 3 distinct picks per category, ordered; points 3/2/1.
export const PICKS = 3;
export const POINTS = [3, 2, 1] as const;
const ORDINALS = ["1.º", "2.º", "3.º"] as const;

export type Picks = (string | null)[]; // length 3, null = empty slot

export const emptyPicks = (): Picks => [null, null, null];
export const ordinal = (slot: number): string => ORDINALS[slot];
export const points = (slot: number): number => POINTS[slot];
export const pointsLabel = (slot: number): string => `${POINTS[slot]} ${POINTS[slot] === 1 ? "pt" : "pts"}`;

/** Sets a slot. Refuses (returns the same picks) a candidate already used in another slot. */
export function setPick(picks: Picks, slot: number, candidateId: string): Picks {
  if (disabledReason(picks, slot, candidateId) !== null) return picks;
  return picks.map((p, i) => (i === slot ? candidateId : p));
}

export const clearPick = (picks: Picks, slot: number): Picks =>
  picks.map((p, i) => (i === slot ? null : p));

/** Why `candidateId` cannot go in `slot` (e.g. "Ya es tu 1.º lugar"), or null if it can. */
export function disabledReason(picks: Picks, slot: number, candidateId: string): string | null {
  const used = picks.findIndex((p, i) => i !== slot && p === candidateId);
  return used === -1 ? null : `Ya es tu ${ORDINALS[used]} lugar`;
}

export const firstEmptySlot = (picks: Picks): number => picks.findIndex((p) => p === null);

export const isComplete = (picks: Picks): boolean =>
  picks.length === PICKS && picks.every((p) => p !== null) && new Set(picks).size === PICKS;

export const missingMessage = (picks: Picks): string | null => {
  const slot = firstEmptySlot(picks);
  return slot === -1 ? null : `Falta elegir tu ${ORDINALS[slot]} lugar.`;
};

/** Narrows a complete ballot to the payload array; throws if incomplete. */
export function toPickIds(picks: Picks): string[] {
  if (!isComplete(picks)) throw new Error("incomplete ballot");
  return picks as string[];
}

export const canVoteIn = (candidateCount: number): boolean => candidateCount >= PICKS;
