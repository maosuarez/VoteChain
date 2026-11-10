// Pure verification logic (no DOM). Mirrors the Python backend byte for byte.
// Works as a browser classic script (window.VoteChainVerify) and under Node (require).
(function (root) {
  "use strict";

  // --- SHA-256 (pure JS: crypto.subtle needs a secure context and is async) ---
  const K = new Uint32Array([
    0x428a2f98, 0x71374491, 0xb5c0fbcf, 0xe9b5dba5, 0x3956c25b, 0x59f111f1, 0x923f82a4, 0xab1c5ed5,
    0xd807aa98, 0x12835b01, 0x243185be, 0x550c7dc3, 0x72be5d74, 0x80deb1fe, 0x9bdc06a7, 0xc19bf174,
    0xe49b69c1, 0xefbe4786, 0x0fc19dc6, 0x240ca1cc, 0x2de92c6f, 0x4a7484aa, 0x5cb0a9dc, 0x76f988da,
    0x983e5152, 0xa831c66d, 0xb00327c8, 0xbf597fc7, 0xc6e00bf3, 0xd5a79147, 0x06ca6351, 0x14292967,
    0x27b70a85, 0x2e1b2138, 0x4d2c6dfc, 0x53380d13, 0x650a7354, 0x766a0abb, 0x81c2c92e, 0x92722c85,
    0xa2bfe8a1, 0xa81a664b, 0xc24b8b70, 0xc76c51a3, 0xd192e819, 0xd6990624, 0xf40e3585, 0x106aa070,
    0x19a4c116, 0x1e376c08, 0x2748774c, 0x34b0bcb5, 0x391c0cb3, 0x4ed8aa4a, 0x5b9cca4f, 0x682e6ff3,
    0x748f82ee, 0x78a5636f, 0x84c87814, 0x8cc70208, 0x90befffa, 0xa4506ceb, 0xbef9a3f7, 0xc67178f2,
  ]);

  function sha256(bytes) {
    const h = new Uint32Array([
      0x6a09e667, 0xbb67ae85, 0x3c6ef372, 0xa54ff53a, 0x510e527f, 0x9b05688c, 0x1f83d9ab, 0x5be0cd19,
    ]);
    const padded = new Uint8Array(((bytes.length + 9 + 63) >> 6) << 6);
    padded.set(bytes);
    padded[bytes.length] = 0x80;
    const view = new DataView(padded.buffer);
    view.setUint32(padded.length - 8, Math.floor((bytes.length * 8) / 0x100000000));
    view.setUint32(padded.length - 4, (bytes.length * 8) >>> 0);
    const w = new Uint32Array(64);
    const rotr = (x, n) => (x >>> n) | (x << (32 - n));
    for (let off = 0; off < padded.length; off += 64) {
      for (let i = 0; i < 16; i++) w[i] = view.getUint32(off + i * 4);
      for (let i = 16; i < 64; i++) {
        const s0 = rotr(w[i - 15], 7) ^ rotr(w[i - 15], 18) ^ (w[i - 15] >>> 3);
        const s1 = rotr(w[i - 2], 17) ^ rotr(w[i - 2], 19) ^ (w[i - 2] >>> 10);
        w[i] = (w[i - 16] + s0 + w[i - 7] + s1) >>> 0;
      }
      let [a, b, c, d, e, f, g, hh] = h;
      for (let i = 0; i < 64; i++) {
        const t1 = (hh + (rotr(e, 6) ^ rotr(e, 11) ^ rotr(e, 25)) + ((e & f) ^ (~e & g)) + K[i] + w[i]) >>> 0;
        const t2 = ((rotr(a, 2) ^ rotr(a, 13) ^ rotr(a, 22)) + ((a & b) ^ (a & c) ^ (b & c))) >>> 0;
        hh = g; g = f; f = e; e = (d + t1) >>> 0; d = c; c = b; b = a; a = (t1 + t2) >>> 0;
      }
      h[0] += a; h[1] += b; h[2] += c; h[3] += d; h[4] += e; h[5] += f; h[6] += g; h[7] += hh;
    }
    const out = new Uint8Array(32);
    const ov = new DataView(out.buffer);
    h.forEach((x, i) => ov.setUint32(i * 4, x));
    return out;
  }

  const utf8 = (s) => new TextEncoder().encode(s);
  const toHex = (b) => Array.from(b, (x) => x.toString(16).padStart(2, "0")).join("");
  const fromHex = (s) => Uint8Array.from(s.match(/../g) || [], (x) => parseInt(x, 16));
  const sha256Hex = (bytes) => toHex(sha256(bytes));
  const concat = (...parts) => {
    const out = new Uint8Array(parts.reduce((n, p) => n + p.length, 0));
    let o = 0;
    parts.forEach((p) => { out.set(p, o); o += p.length; });
    return out;
  };

  // --- Canonical JSON: sorted keys, no spaces, UTF-8 (ints/strings/lists/objects only) ---
  function canonical(value) {
    if (Array.isArray(value)) return "[" + value.map(canonical).join(",") + "]";
    if (value !== null && typeof value === "object") {
      return "{" + Object.keys(value).sort().map((k) => JSON.stringify(k) + ":" + canonical(value[k])).join(",") + "}";
    }
    return JSON.stringify(value);
  }
  const canonicalBytes = (value) => utf8(canonical(value));

  // --- Merkle (leaf 0x00, node 0x01, odd node promoted) ---
  const LEAF = Uint8Array.of(0), NODE = Uint8Array.of(1);
  const leafHash = (tx) => sha256(concat(LEAF, canonicalBytes(tx)));

  function merkleRoot(txs) {
    if (txs.length === 0) return sha256Hex(new Uint8Array(0));
    let level = txs.map(leafHash);
    while (level.length > 1) {
      const next = [];
      for (let i = 0; i + 1 < level.length; i += 2) next.push(sha256(concat(NODE, level[i], level[i + 1])));
      if (level.length % 2) next.push(level[level.length - 1]);
      level = next;
    }
    return toHex(level[0]);
  }

  function rootFromProof(tx, proof) {
    let node = leafHash(tx);
    for (const step of proof) {
      if (step.side !== "left" && step.side !== "right") return null;
      const sib = fromHex(step.hash);
      node = sha256(step.side === "left" ? concat(NODE, sib, node) : concat(NODE, node, sib));
    }
    return toHex(node);
  }

  // --- Blocks, transactions, chain ---
  function blockHash(b) {
    return sha256Hex(canonicalBytes({
      index: b.index, timestamp: b.timestamp, prev_hash: b.prev_hash, data: b.data,
      merkle_root: b.merkle_root, nonce: b.nonce, proposer: b.proposer,
    }));
  }

  function txId(tx) {
    return sha256Hex(canonicalBytes({ type: tx.type, payload: tx.payload, sender: tx.sender, timestamp: tx.timestamp }));
  }

  const ZERO_HASH = "0".repeat(64);

  function verifyChain(blocks) {
    const fail = (i, reason) => ({ valid: false, badIndex: i, reason });
    for (let i = 0; i < blocks.length; i++) {
      const b = blocks[i];
      if (b.index !== i) return fail(i, "non-consecutive index");
      if (i === 0) {
        const g = b.data && b.data.transactions;
        if (b.prev_hash !== ZERO_HASH || b.timestamp !== 0 || !Array.isArray(g) || g.length !== 0) {
          return fail(0, "genesis block mismatch");
        }
      } else if (b.prev_hash !== blocks[i - 1].hash) {
        return fail(i, "prev_hash mismatch");
      }
      if (blockHash(b) !== b.hash) return fail(i, "hash mismatch");
      const txs = b.data && b.data.transactions;
      if (!Array.isArray(txs)) return fail(i, "missing transactions");
      if (merkleRoot(txs) !== b.merkle_root) return fail(i, "merkle root mismatch");
    }
    return { valid: blocks.length > 0, badIndex: null, reason: blocks.length ? "" : "empty chain" };
  }

  // Receipt: proof leads from the block's own tx to the block's root; block hash is recomputed.
  function verifyReceipt(receipt, block, txIdWanted) {
    if (blockHash(block) !== block.hash || block.hash !== receipt.block_hash) return false;
    if (block.merkle_root !== receipt.merkle_root) return false;
    const tx = (block.data.transactions || []).find((t) => txId(t) === txIdWanted);
    if (!tx) return false;
    return rootFromProof(tx, receipt.proof) === block.merkle_root;
  }

  // --- Tally replay (no signature checks); mirrors voting.py rules ---
  const POINTS = [3, 2, 1];

  function replayElections(blocks) {
    const elections = {};
    for (const block of blocks) {
      for (const tx of block.data.transactions) {
        const p = tx.payload || {};
        if (tx.type === "CREATE_ELECTION") {
          if (!(p.election_id in elections)) {
            elections[p.election_id] = { admin: tx.sender, opens_at: p.opens_at, closes_at: p.closes_at,
              status: "draft", candidates: {}, ballots: {} };
          }
          continue;
        }
        const e = elections[p.election_id];
        if (!e) continue;
        if (tx.type === "CAST_BALLOT") {
          const picks = p.picks;
          const cands = e.candidates[p.category];
          const key = tx.sender + "\u0000" + p.category;
          if (e.status !== "open" || block.timestamp < e.opens_at || block.timestamp > e.closes_at) continue;
          if (!cands || !Array.isArray(picks) || picks.length !== 3 || new Set(picks).size !== 3) continue;
          if (!picks.every((c) => typeof c === "string" && c in cands) || key in e.ballots) continue;
          e.ballots[key] = { category: p.category, picks };
        } else if (tx.sender === e.admin) {
          if (tx.type === "ADD_CATEGORY" && e.status === "draft" && !(p.category in e.candidates)) e.candidates[p.category] = {};
          else if (tx.type === "ADD_CANDIDATE" && e.status === "draft" && e.candidates[p.category] && !(p.candidate_id in e.candidates[p.category])) e.candidates[p.category][p.candidate_id] = p.name;
          else if (tx.type === "OPEN_ELECTION" && e.status === "draft") e.status = "open";
          else if (tx.type === "CLOSE_ELECTION" && e.status === "open") e.status = "closed";
        }
      }
    }
    return elections;
  }

  function tallyElection(election) {
    const result = {};
    for (const [category, cands] of Object.entries(election.candidates)) {
      const stats = {};
      Object.keys(cands).forEach((id) => { stats[id] = [0, 0, 0]; });
      for (const ballot of Object.values(election.ballots)) {
        if (ballot.category !== category) continue;
        ballot.picks.forEach((id, pos) => {
          stats[id][0] += POINTS[pos];
          if (pos < 2) stats[id][pos + 1] += 1;
        });
      }
      const ordered = Object.entries(stats).sort(([ia, a], [ib, b]) =>
        (b[0] - a[0]) || (b[1] - a[1]) || (b[2] - a[2]) || (ia < ib ? -1 : ia > ib ? 1 : 0));
      const same = (x, y) => x[0] === y[0] && x[1] === y[1] && x[2] === y[2];
      result[category] = ordered.map(([id, s]) => ({
        candidate_id: id, name: cands[id], points: s[0], firsts: s[1], seconds: s[2],
        rank: ordered.findIndex(([, o]) => same(o, s)) + 1,
        tied: ordered.filter(([, o]) => same(o, s)).length > 1,
      }));
    }
    return result;
  }

  const api = { sha256Hex, utf8, canonical, merkleRoot, rootFromProof, blockHash, txId,
    verifyChain, verifyReceipt, replayElections, tallyElection };
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  else root.VoteChainVerify = api;
})(typeof window !== "undefined" ? window : globalThis);
