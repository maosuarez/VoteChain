// Run: node tests/js/parity.test.js  (parity of web/verify.js with backend vectors)
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const v = require("../../web/verify.js");

const vec = JSON.parse(fs.readFileSync(path.join(__dirname, "../vectors/audit_vectors.json"), "utf8"));
const fromHex = (h) => Uint8Array.from(h.match(/../g) || [], (x) => parseInt(x, 16));
const clone = (x) => JSON.parse(JSON.stringify(x));

for (const s of vec.sha256) assert.equal(v.sha256Hex(fromHex(s.hex)), s.digest);
for (const c of vec.canonical) assert.equal(v.canonical(c.input), c.output);

for (const m of vec.merkle) {
  assert.equal(v.merkleRoot(m.txs), m.root);
  m.txs.forEach((tx, i) => {
    assert.equal(v.rootFromProof(tx, m.proofs[i]), m.root);
    if (m.proofs[i].length) {
      const bad = clone(m.proofs[i]);
      bad[0].hash = bad[0].hash.replace(/^./, (c) => (c === "0" ? "1" : "0"));
      assert.notEqual(v.rootFromProof(tx, bad), m.root);
    }
  });
}

for (const b of vec.block_hash) assert.equal(v.blockHash(b.block), b.hash);

assert.deepEqual(v.verifyChain(vec.chain), { valid: true, badIndex: null, reason: "" });

const tampered = clone(vec.chain);
const txBlock = tampered.findIndex((b) => b.data.transactions.length);
tampered[txBlock].data.transactions[0].payload.tampered = 1;
const r = v.verifyChain(tampered);
assert.equal(r.valid, false);
assert.equal(r.badIndex, txBlock);

const relinked = clone(vec.chain);
relinked[2].prev_hash = "f".repeat(64);
assert.deepEqual([v.verifyChain(relinked).valid, v.verifyChain(relinked).badIndex], [false, 2]);

const election = v.replayElections(vec.chain)[vec.election_id];
assert.equal(election.status, "closed");
assert.deepEqual(v.tallyElection(election), vec.tally);
assert.ok(Object.values(vec.tally).flat().some((e) => e.tied), "vector must contain a tie");

for (const rc of vec.receipts) {
  const block = vec.chain[rc.block_index];
  assert.ok(v.verifyReceipt(rc, block, rc.tx_id));
  const badProof = clone(rc);
  badProof.proof.length ? (badProof.proof[0].hash = "0".repeat(64)) : (badProof.merkle_root = "0".repeat(64));
  assert.equal(v.verifyReceipt(badProof, block, rc.tx_id), false);
  assert.equal(v.verifyReceipt(rc, block, "0".repeat(64)), false);
}
console.log("parity ok");
