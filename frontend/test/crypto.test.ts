import { describe, expect, it } from "vitest";
import { readFileSync } from "node:fs";
import path from "node:path";
import { hexToBytes, utf8ToBytes } from "@noble/hashes/utils.js";
import * as c from "@/lib/crypto";

const load = (name: string) =>
  JSON.parse(readFileSync(path.join(__dirname, "../../tests/vectors", name), "utf8"));
const v = load("voter_vectors.json");
const audit = load("audit_vectors.json");

describe("parity with backend vectors", () => {
  it("sha256 and canonical JSON", () => {
    for (const s of audit.sha256) expect(c.sha256Hex(hexToBytes(s.hex))).toBe(s.digest);
    for (const k of audit.canonical) expect(c.canonical(k.input)).toBe(k.output);
  });

  it("ed25519 public key and signatures are byte-identical", () => {
    expect(c.publicKeyHex(v.voter.seed)).toBe(v.voter.public);
    for (const s of v.ed25519) expect(c.signHex(v.voter.seed, hexToBytes(s.message_hex))).toBe(s.signature);
  });

  it("full-domain hash", () => {
    const n = BigInt(`0x${v.issuer.n}`);
    for (const f of v.fdh) expect(c.fdh(hexToBytes(f.message_hex), n).toString(16)).toBe(f.value);
  });

  it("credential message, blinding, unblinding and verification", () => {
    const message = c.credentialMessage(v.election_id, v.voter.public);
    expect(new TextDecoder().decode(message)).toBe(v.credential_message);
    const factor = BigInt(`0x${v.blind.factor}`);
    expect(c.blind(v.issuer, message, factor).blinded).toBe(v.blind.blinded);
    expect(c.unblind(v.issuer, v.blind.blind_signature, factor)).toBe(v.blind.signature);
    expect(c.verifyBlind(v.issuer, v.blind.signature, message)).toBe(true);
    expect(c.verifyBlind(v.issuer, v.blind.signature, utf8ToBytes("other"))).toBe(false);
    expect(c.verifyBlind(v.issuer, "zz", message)).toBe(false);
  });

  it("CAST_BALLOT tx: canonical body, tx_id and signature", () => {
    const d = v.tx.dict;
    const tx = c.createBallotTx(
      v.voter.seed, d.payload.election_id, d.payload.category, d.payload.picks,
      d.payload.credential_sig, d.timestamp,
    );
    expect(tx).toEqual(d);
    expect(c.txId(tx)).toBe(v.tx.tx_id);
    expect(c.canonical({ type: tx.type, payload: tx.payload, sender: tx.sender, timestamp: tx.timestamp }))
      .toBe(v.tx.canonical_body);
  });
});

describe("credential round trip", () => {
  it("blind -> issuer signs (simulated with vector key) -> unblind gives a valid credential", () => {
    const d = BigInt(`0x${v.issuer_d}`);
    const n = BigInt(`0x${v.issuer.n}`);
    const req = c.newCredentialRequest(v.issuer, "e1");
    const blindSig = c.modPow(BigInt(`0x${req.blinded}`), d, n).toString(16);
    const sig = c.finishCredential(v.issuer, "e1", req, blindSig);
    expect(sig).not.toBeNull();
    expect(c.finishCredential(v.issuer, "other", req, blindSig)).toBeNull();
    expect(c.finishCredential(v.issuer, "e1", req, "0")).toBeNull();
  });
});
