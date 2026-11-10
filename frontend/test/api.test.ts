import { afterEach, describe, expect, it, vi } from "vitest";
import { readFileSync } from "node:fs";
import path from "node:path";
import * as api from "@/lib/api";
import { createBallotTx, modPow, txId } from "@/lib/crypto";

const v = JSON.parse(readFileSync(path.join(import.meta.dirname, "../../tests/vectors/voter_vectors.json"), "utf8"));

const res = (status: number, body: unknown = {}) =>
  new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } });

function mockFetch(handler: (url: string, init?: RequestInit) => Response | Promise<Response>) {
  const spy = vi.fn(async (url: string, init?: RequestInit) => handler(url, init));
  vi.stubGlobal("fetch", spy);
  return spy;
}

afterEach(() => vi.unstubAllGlobals());

const tx = createBallotTx(v.voter.seed, "e1", "profesor", ["A", "B", "C"], "ab", 1000);

describe("sendBallot idempotency", () => {
  it("returns the tx_id on 202", async () => {
    mockFetch(() => res(202, { tx_id: "x" }));
    expect(await api.sendBallot(tx)).toBe(txId(tx));
  });

  it("400 with an existing receipt for the local tx_id counts as registered", async () => {
    const spy = mockFetch((url) => (url.startsWith("/api/chain/receipts/") ? res(200) : res(400, { detail: "ballot_rejected" })));
    expect(await api.sendBallot(tx)).toBe(txId(tx));
    expect(spy.mock.calls[1][0]).toBe(`/api/chain/receipts/${txId(tx)}`);
  });

  it("400 without receipt is a rejection", async () => {
    mockFetch((url) => (url.startsWith("/api/chain/receipts/") ? res(404) : res(400)));
    await expect(api.sendBallot(tx)).rejects.toBeInstanceOf(api.BallotRejected);
  });

  it("network failure is recoverable", async () => {
    mockFetch(() => Promise.reject(new TypeError("offline")));
    await expect(api.sendBallot(tx)).rejects.toBeInstanceOf(api.NetworkError);
  });
});

describe("redeemCredential", () => {
  const election = {
    election_id: "e1", status: "open", opens_at: 0, closes_at: 9, issuer_key: v.issuer, categories: {},
  } as api.ElectionInfo;

  it("sends only email, code and blinded value, then verifies the unblinded credential", async () => {
    const d = BigInt(`0x${v.issuer_d}`);
    const n = BigInt(`0x${v.issuer.n}`);
    let sent: Record<string, string> = {};
    mockFetch((_u, init) => {
      sent = JSON.parse(init!.body as string);
      return res(200, { blind_signature: modPow(BigInt(`0x${sent.blinded}`), d, n).toString(16) });
    });
    const cred = await api.redeemCredential(election, "a@x.edu", "ABC123");
    expect(Object.keys(sent).sort()).toEqual(["blinded", "code", "email"]);
    expect(cred.electionId).toBe("e1");
    expect(JSON.stringify(sent)).not.toContain(cred.privateKey);
  });

  it("any 400 is a uniform rejection; a forged blind signature is rejected too", async () => {
    mockFetch(() => res(400, { detail: "invalid_request" }));
    await expect(api.redeemCredential(election, "a@x.edu", "X")).rejects.toBeInstanceOf(api.CredentialRejected);
    mockFetch(() => res(200, { blind_signature: "5" }));
    await expect(api.redeemCredential(election, "a@x.edu", "X")).rejects.toBeInstanceOf(api.CredentialRejected);
  });

  it("normalizes codes", () => {
    expect(api.normalizeCode(" ab c-1 2\n")).toBe("ABC-12");
  });
});

describe("master calls", () => {
  it("token validation: 401 invalid, 409 valid, no side effects (empty roll on unknown election)", async () => {
    const spy = mockFetch((_u, init) => ((init!.headers as Record<string, string>).Authorization === "Bearer good" ? res(409) : res(401)));
    expect(await api.validateMasterToken("good")).toBe(true);
    expect(await api.validateMasterToken("bad")).toBe(false);
    expect(JSON.parse(spy.mock.calls[0][1]!.body as string)).toEqual({ emails: [] });
  });

  it("401 raises Unauthorized, 409 surfaces the reason", async () => {
    mockFetch(() => res(401));
    await expect(api.openElection("t", "e1")).rejects.toBeInstanceOf(api.Unauthorized);
    mockFetch(() => res(409, { detail: "election is not draft" }));
    await expect(api.openElection("t", "e1")).rejects.toMatchObject({ status: 409, message: "election is not draft" });
  });
});

describe("chain helpers", () => {
  const txs = [
    { type: "CREATE_ELECTION", payload: { election_id: "e1" } },
    { type: "CAST_BALLOT", payload: { election_id: "e1" } },
    { type: "CAST_BALLOT", payload: { election_id: "e2" } },
  ] as never;
  it("discovers elections and counts ballots", () => {
    expect(api.electionIds(txs)).toEqual(["e1"]);
    expect(api.countBallots(txs, "e1")).toBe(1);
  });
});
