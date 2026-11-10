// Browser-side crypto compatible with the backend (votechain/crypto.py, blind.py, transactions.py).
// Pure JS (noble) + BigInt: works without a secure context (pilot over HTTP on a LAN).
import { ed25519 } from "@noble/curves/ed25519.js";
import { sha256 } from "@noble/hashes/sha2.js";
import { bytesToHex, hexToBytes, utf8ToBytes } from "@noble/hashes/utils.js";

export type Json = null | boolean | number | string | Json[] | { [key: string]: Json };
export type IssuerPublicKey = { n: string; e: number };

export type Tx = {
  type: string;
  payload: { [key: string]: Json };
  sender: string;
  timestamp: number;
  signature: string;
};

/** Canonical JSON: sorted keys, no spaces, Unicode unescaped (same as Python's canonical_bytes). */
export function canonical(value: Json): string {
  if (Array.isArray(value)) return `[${value.map(canonical).join(",")}]`;
  if (value !== null && typeof value === "object") {
    const keys = Object.keys(value).sort();
    return `{${keys.map((k) => `${JSON.stringify(k)}:${canonical(value[k])}`).join(",")}}`;
  }
  if (typeof value === "number" && !Number.isSafeInteger(value)) {
    throw new Error("only safe integers are canonicalizable");
  }
  return JSON.stringify(value);
}

export const sha256Hex = (data: Uint8Array): string => bytesToHex(sha256(data));

export function generateKeypair(): { privateKey: string; publicKey: string } {
  const seed = randomBytes(32);
  return { privateKey: bytesToHex(seed), publicKey: bytesToHex(ed25519.getPublicKey(seed)) };
}

export const publicKeyHex = (privateKey: string): string =>
  bytesToHex(ed25519.getPublicKey(hexToBytes(privateKey)));

export const signHex = (privateKey: string, message: Uint8Array): string =>
  bytesToHex(ed25519.sign(message, hexToBytes(privateKey)));

function randomBytes(n: number): Uint8Array {
  return crypto.getRandomValues(new Uint8Array(n));
}

// --- RSA blind signatures with full-domain hash (blind.py) ---

const bigFromHex = (h: string): bigint => BigInt(`0x${h}`);
const bigToHex = (v: bigint): string => v.toString(16);

function bitLength(v: bigint): number {
  return v === 0n ? 0 : v.toString(2).length;
}

export function modPow(base: bigint, exp: bigint, mod: bigint): bigint {
  let result = 1n;
  let b = base % mod;
  let e = exp;
  while (e > 0n) {
    if (e & 1n) result = (result * b) % mod;
    b = (b * b) % mod;
    e >>= 1n;
  }
  return result;
}

function gcd(a: bigint, b: bigint): bigint {
  while (b) [a, b] = [b, a % b];
  return a;
}

export function modInverse(a: bigint, mod: bigint): bigint {
  let [oldR, r] = [((a % mod) + mod) % mod, mod];
  let [oldS, s] = [1n, 0n];
  while (r) {
    const q = oldR / r;
    [oldR, r] = [r, oldR - q * r];
    [oldS, s] = [s, oldS - q * s];
  }
  if (oldR !== 1n) throw new Error("not invertible");
  return ((oldS % mod) + mod) % mod;
}

/** SHA-256 in counter mode, truncated so the value is < n. */
export function fdh(message: Uint8Array, n: bigint): bigint {
  const length = Math.floor((bitLength(n) - 1) / 8);
  const out = new Uint8Array(Math.ceil(length / 32) * 32);
  for (let counter = 0, offset = 0; offset < length; counter++, offset += 32) {
    const input = new Uint8Array(4 + message.length);
    new DataView(input.buffer).setUint32(0, counter);
    input.set(message, 4);
    out.set(sha256(input), offset);
  }
  return bigFromHex(bytesToHex(out.slice(0, length)) || "0");
}

export function credentialMessage(electionId: string, credentialPublicKey: string): Uint8Array {
  return utf8ToBytes(`votechain-credential-v1:${electionId}:${credentialPublicKey}`);
}

function parsePublic(pub: IssuerPublicKey): { n: bigint; e: bigint } {
  const n = bigFromHex(pub.n);
  if (n < 2n ** 1023n || !Number.isInteger(pub.e) || pub.e < 3 || pub.e % 2 === 0) {
    throw new Error("malformed issuer public key");
  }
  return { n, e: BigInt(pub.e) };
}

/** Returns (blindedHex, factor). `factor` stays secret in the browser. */
export function blind(
  pub: IssuerPublicKey,
  message: Uint8Array,
  factor?: bigint,
): { blinded: string; factor: bigint } {
  const { n, e } = parsePublic(pub);
  let f = factor;
  while (f === undefined) {
    const candidate = (bigFromHex(bytesToHex(randomBytes(bitLength(n) / 8 + 8))) % (n - 2n)) + 2n;
    if (gcd(candidate, n) === 1n) f = candidate;
  }
  return { blinded: bigToHex((fdh(message, n) * modPow(f, e, n)) % n), factor: f };
}

export function unblind(pub: IssuerPublicKey, blindSignatureHex: string, factor: bigint): string {
  const { n } = parsePublic(pub);
  const value = bigFromHex(blindSignatureHex);
  if (!(value > 0n && value < n)) throw new Error("malformed blind signature");
  return bigToHex((value * modInverse(factor, n)) % n);
}

/** Never throws: malformed input yields false. */
export function verifyBlind(pub: IssuerPublicKey, signatureHex: string, message: Uint8Array): boolean {
  try {
    const { n, e } = parsePublic(pub);
    const signature = bigFromHex(signatureHex);
    return signature > 0n && signature < n && modPow(signature, e, n) === fdh(message, n);
  } catch {
    return false;
  }
}

// --- Credential and ballot transactions ---

export type CredentialRequest = {
  privateKey: string;
  publicKey: string;
  blinded: string;
  factor: bigint;
};

export function newCredentialRequest(pub: IssuerPublicKey, electionId: string): CredentialRequest {
  const { privateKey, publicKey } = generateKeypair();
  const { blinded, factor } = blind(pub, credentialMessage(electionId, publicKey));
  return { privateKey, publicKey, blinded, factor };
}

/** Unblind and check; returns the credential signature or null if invalid. */
export function finishCredential(
  pub: IssuerPublicKey,
  electionId: string,
  request: CredentialRequest,
  blindSignatureHex: string,
): string | null {
  try {
    const signature = unblind(pub, blindSignatureHex, request.factor);
    return verifyBlind(pub, signature, credentialMessage(electionId, request.publicKey)) ? signature : null;
  } catch {
    return null;
  }
}

function txBody(tx: Omit<Tx, "signature">): Json {
  return { type: tx.type, payload: tx.payload, sender: tx.sender, timestamp: tx.timestamp };
}

export const txId = (tx: Omit<Tx, "signature">): string =>
  sha256Hex(utf8ToBytes(canonical(txBody(tx))));

export function createTx(
  type: string,
  payload: { [key: string]: Json },
  privateKey: string,
  timestamp: number,
): Tx {
  const unsigned = { type, payload, sender: publicKeyHex(privateKey), timestamp };
  return { ...unsigned, signature: signHex(privateKey, utf8ToBytes(canonical(txBody(unsigned)))) };
}

export function createBallotTx(
  privateKey: string,
  electionId: string,
  category: string,
  picks: string[],
  credentialSig: string,
  timestamp: number,
): Tx {
  return createTx(
    "CAST_BALLOT",
    { election_id: electionId, category, picks, credential_sig: credentialSig },
    privateKey,
    timestamp,
  );
}
