// Client for the VoteChain API through the Next.js /api rewrite.
import { createBallotTx, finishCredential, newCredentialRequest, txId, type IssuerPublicKey, type Tx } from "./crypto";
import type { Credential } from "./session";

const BASE = "/api";

export type ElectionInfo = {
  election_id: string;
  status: "draft" | "open" | "closed";
  opens_at: number;
  closes_at: number;
  issuer_key: IssuerPublicKey;
  categories: Record<string, Record<string, string>>; // category -> candidate id -> name
};

type Block = { data: { transactions: Tx[] } };

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
  }
}
/** The request did not reach the API (or the answer was lost); safe to retry the same call. */
export class NetworkError extends Error {}

async function call(path: string, init?: RequestInit): Promise<Response> {
  try {
    return await fetch(`${BASE}${path}`, init);
  } catch {
    throw new NetworkError("No pudimos conectar con el servidor.");
  }
}

async function detail(res: Response): Promise<string> {
  try {
    const body = await res.json();
    return typeof body.detail === "string" ? body.detail : `Error ${res.status}`;
  } catch {
    return `Error ${res.status}`;
  }
}

async function getJson<T>(path: string): Promise<T> {
  const res = await call(path);
  if (!res.ok) throw new ApiError(res.status, await detail(res));
  return res.json() as Promise<T>;
}

// --- public reads ---

export async function fetchChainTxs(): Promise<Tx[]> {
  const { blocks } = await getJson<{ blocks: Block[] }>("/chain");
  return blocks.flatMap((b) => b.data.transactions);
}

export const electionIds = (txs: Tx[]): string[] =>
  txs.filter((t) => t.type === "CREATE_ELECTION").map((t) => t.payload.election_id as string);

/** CAST_BALLOT txs of an election present in the chain (one per credential and category). */
export const countBallots = (txs: Tx[], id: string): number =>
  txs.filter((t) => t.type === "CAST_BALLOT" && t.payload.election_id === id).length;

export const getElection = (id: string) => getJson<ElectionInfo>(`/elections/${encodeURIComponent(id)}`);

export async function listElections(): Promise<ElectionInfo[]> {
  const ids = electionIds(await fetchChainTxs());
  return Promise.all(ids.map(getElection));
}

// --- voter ---

export class CredentialRejected extends Error {}

/** Blind in the browser, redeem, unblind and verify against the election's issuer key. */
export async function redeemCredential(election: ElectionInfo, email: string, code: string): Promise<Credential> {
  const request = newCredentialRequest(election.issuer_key, election.election_id);
  const res = await call(`/elections/${encodeURIComponent(election.election_id)}/credentials`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, code, blinded: request.blinded }),
  });
  if (!res.ok) throw new CredentialRejected("rejected");
  const { blind_signature } = (await res.json()) as { blind_signature: string };
  const signature = finishCredential(election.issuer_key, election.election_id, request, blind_signature);
  if (signature === null) throw new CredentialRejected("invalid signature");
  return { electionId: election.election_id, privateKey: request.privateKey, signature };
}

export const normalizeCode = (raw: string): string => raw.replace(/\s+/g, "").toUpperCase();

export function signBallot(cred: Credential, category: string, picks: string[], timestamp: number): Tx {
  return createBallotTx(cred.privateKey, cred.electionId, category, picks, cred.signature, timestamp);
}

export class BallotRejected extends Error {}

/**
 * Idempotent send: resending the same signed tx is harmless. A 400 means rejected unless the
 * locally computed tx_id is already in the chain (the earlier answer was lost) -> registered.
 */
export async function sendBallot(tx: Tx): Promise<string> {
  const id = txId(tx);
  const res = await call("/ballots", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ tx }),
  });
  if (res.ok) return id;
  const receipt = await call(`/chain/receipts/${id}`);
  if (receipt.ok) return id;
  throw new BallotRejected("rejected");
}

// --- master ---

export class Unauthorized extends Error {}

async function admin<T>(token: string, path: string, body?: unknown): Promise<T> {
  const res = await call(`/admin${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
    body: JSON.stringify(body ?? {}),
  });
  if (res.status === 401) throw new Unauthorized("unauthorized");
  if (!res.ok) throw new ApiError(res.status, await detail(res));
  return res.json() as Promise<T>;
}

/** Side-effect-free token check: 401 = invalid; 409 (unknown election) = authorized. */
export async function validateMasterToken(token: string): Promise<boolean> {
  const res = await call("/admin/elections/__probe__/voters", {
    method: "POST",
    headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
    body: JSON.stringify({ emails: [] }),
  });
  if (res.status === 401) return false;
  if (res.status === 409) return true;
  throw new ApiError(res.status, await detail(res));
}

const enc = encodeURIComponent;
export const createElection = (t: string, election_id: string, opens_at: number, closes_at: number) =>
  admin(t, "/elections", { election_id, opens_at, closes_at });
export const addCategory = (t: string, id: string, category: string) =>
  admin(t, `/elections/${enc(id)}/categories`, { category });
export const addCandidate = (t: string, id: string, category: string, candidate_id: string, name: string) =>
  admin(t, `/elections/${enc(id)}/candidates`, { category, candidate_id, name });
export const openElection = (t: string, id: string) => admin(t, `/elections/${enc(id)}/open`);
export const closeElection = (t: string, id: string) => admin(t, `/elections/${enc(id)}/close`);
export const loadRoll = (t: string, id: string, emails: string[]) =>
  admin<{ submitted: number }>(t, `/elections/${enc(id)}/voters`, { emails });
export const sendCode = (t: string, id: string, email: string) =>
  admin<{ sent: boolean }>(t, `/elections/${enc(id)}/codes`, { email });
