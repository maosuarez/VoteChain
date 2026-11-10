// Pure helpers for the master panel.
import { PICKS } from "./ballot";
import type { ElectionInfo } from "./api";

export type Prerequisite = { label: string; done: boolean };

/** Same rule the backend enforces on open: >=1 category and >=3 candidates in each. */
export function openPrerequisites(election: ElectionInfo): Prerequisite[] {
  const categories = Object.entries(election.categories);
  return [
    { label: "Al menos una categoría", done: categories.length > 0 },
    ...categories.map(([name, cands]) => ({
      label: `${name}: al menos ${PICKS} candidatos`,
      done: Object.keys(cands).length >= PICKS,
    })),
  ];
}

export const canOpen = (election: ElectionInfo): boolean =>
  election.status === "draft" && openPrerequisites(election).every((p) => p.done);

export const canConfirmClose = (typed: string, electionId: string): boolean => typed === electionId;

/** datetime-local value ("2026-03-01T10:00") to UTC seconds; null if invalid. */
export function toEpochSeconds(local: string): number | null {
  const ms = new Date(local).getTime();
  return Number.isNaN(ms) ? null : Math.floor(ms / 1000);
}
