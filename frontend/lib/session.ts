// sessionStorage helpers: per-tab, cleared when the tab closes. Never throws.
import type { IssuerPublicKey, Tx } from "./crypto";

export type Credential = { electionId: string; privateKey: string; signature: string };
export type Draft = { picks: Record<string, (string | null)[]>; signed: Record<string, Tx> };

const KEYS = { credential: "vc.credential", draft: "vc.draft", master: "vc.master" } as const;

function read<T>(key: string): T | null {
  try {
    const raw = sessionStorage.getItem(key);
    return raw === null ? null : (JSON.parse(raw) as T);
  } catch {
    return null;
  }
}

function write(key: string, value: unknown): void {
  try {
    sessionStorage.setItem(key, JSON.stringify(value));
  } catch {
    /* storage unavailable: the flow still works in memory for this page */
  }
}

const remove = (key: string): void => {
  try {
    sessionStorage.removeItem(key);
  } catch {
    /* ignore */
  }
};

export const loadCredential = () => read<Credential>(KEYS.credential);
export const saveCredential = (c: Credential) => write(KEYS.credential, c);
export const loadDraft = (): Draft => read<Draft>(KEYS.draft) ?? { picks: {}, signed: {} };
export const saveDraft = (d: Draft) => write(KEYS.draft, d);

/** Removes credential and draft (picks included) once the receipt is shown. */
export function clearVoterSession(): void {
  remove(KEYS.credential);
  remove(KEYS.draft);
}

export const loadMasterToken = () => read<string>(KEYS.master);
export const saveMasterToken = (t: string) => write(KEYS.master, t);
export const clearMasterToken = () => remove(KEYS.master);

export type { IssuerPublicKey };

// Receipts hold only tx_ids (no picks, no identity).
export const loadReceipts = () => read<Record<string, string>>("vc.receipts") ?? {};
export const saveReceipts = (r: Record<string, string>) => write("vc.receipts", r);
