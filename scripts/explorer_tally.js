// Independent verifier: reads a chain (JSON array of blocks) on stdin and runs the public
// explorer's logic (web/verify.js, a separate implementation from the Python backend).
// Usage: node scripts/explorer_tally.js <election_id> < chain.json
// Output: {"valid": bool, "bad_index": int|null, "reason": str, "tally": {...}|null}
const fs = require("node:fs");
const path = require("node:path");
const v = require(path.join(__dirname, "..", "web", "verify.js"));

const electionId = process.argv[2];
const blocks = JSON.parse(fs.readFileSync(0, "utf8"));
const chain = v.verifyChain(blocks);
let tally = null;
if (chain.valid) {
  const election = v.replayElections(blocks)[electionId];
  if (election) tally = v.tallyElection(election);
}
process.stdout.write(JSON.stringify({
  valid: chain.valid, bad_index: chain.badIndex, reason: chain.reason, tally,
}));
