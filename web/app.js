// DOM and fetch only; all verification logic lives in verify.js.
(function () {
  "use strict";
  const V = window.VoteChainVerify;
  const $ = (id) => document.getElementById(id);

  // Data comes from the chain (untrusted text): always set as plain text.
  function el(tag, text, cls) {
    const n = document.createElement(tag);
    if (text !== undefined) n.textContent = text;
    if (cls) n.className = cls;
    return n;
  }
  const status = (node, ok, text) => { node.className = ok ? "ok" : "bad"; node.textContent = text; };

  async function getJson(path) {
    const r = await fetch(path);
    if (!r.ok) throw Object.assign(new Error("HTTP " + r.status), { status: r.status });
    return r.json();
  }

  function renderBlocks(blocks) {
    const box = $("blocks");
    blocks.forEach((b) => {
      const d = el("details");
      d.appendChild(el("summary", "#" + b.index + "  " + b.hash.slice(0, 16) + "...  (" + b.data.transactions.length + " tx)"));
      d.appendChild(el("pre", JSON.stringify({ ...b, data: undefined }, null, 1)));
      b.data.transactions.forEach((tx) => {
        const t = el("details");
        t.appendChild(el("summary", tx.type + "  " + V.txId(tx).slice(0, 16) + "..."));
        t.appendChild(el("pre", JSON.stringify(tx, null, 1)));
        d.appendChild(t);
      });
      box.appendChild(d);
    });
  }

  function renderRanking(box, ranking) {
    Object.entries(ranking).forEach(([category, entries]) => {
      box.appendChild(el("h4", category));
      const table = el("table");
      const head = el("tr");
      ["Pos.", "Candidato", "Puntos", "Empate"].forEach((h) => head.appendChild(el("th", h)));
      table.appendChild(head);
      entries.forEach((e) => {
        const row = el("tr");
        [e.rank, e.name, e.points, e.tied ? "sí" : ""].forEach((c) => row.appendChild(el("td", String(c))));
        table.appendChild(row);
      });
      box.appendChild(table);
    });
  }

  async function renderElection(box, id, election) {
    box.appendChild(el("h3", id + " (" + election.status + ")"));
    if (election.status !== "closed") {
      box.appendChild(el("p", "El ranking se publica al cierre de la elección.", "note"));
      return;
    }
    try {
      const published = await getJson("/elections/" + encodeURIComponent(id) + "/tally");
      renderRanking(box, published);
      const same = V.canonical(published) === V.canonical(V.tallyElection(election));
      box.appendChild(el("p", same ? "El conteo recalculado desde la cadena coincide con el publicado." : "DISCREPANCIA: el conteo recalculado no coincide con el publicado.", same ? "ok" : "bad"));
    } catch (e) {
      box.appendChild(el("p", "No se pudo obtener el conteo (" + e.message + ").", "bad"));
    }
  }

  async function verifyReceipt(txId) {
    const out = $("receipt-result");
    out.className = ""; out.textContent = "Verificando...";
    try {
      const receipt = await getJson("/chain/receipts/" + encodeURIComponent(txId));
      const block = await getJson("/chain/blocks/" + receipt.block_index);
      if (V.verifyReceipt(receipt, block, txId)) status(out, true, "Tu papeleta está incluida en el bloque #" + receipt.block_index + ".");
      else status(out, false, "No se pudo comprobar la inclusión (prueba inválida).");
    } catch (e) {
      status(out, false, e.status === 404 ? "No se encontró esa transacción en la cadena." : "Error: " + e.message);
    }
  }

  async function main() {
    const chain = await getJson("/chain");
    const result = V.verifyChain(chain.blocks);
    status($("chain-status"), result.valid, result.valid
      ? "Cadena verificada: " + chain.blocks.length + " bloques consistentes."
      : "Cadena INVÁLIDA en el bloque #" + result.badIndex + " (" + result.reason + ").");
    renderBlocks(chain.blocks);
    const elections = V.replayElections(chain.blocks);
    for (const [id, e] of Object.entries(elections)) await renderElection($("elections"), id, e);
  }

  $("receipt-form").addEventListener("submit", (ev) => {
    ev.preventDefault();
    verifyReceipt($("receipt-tx").value.trim().toLowerCase());
  });
  main().catch((e) => status($("chain-status"), false, "Error al cargar la cadena: " + e.message));
})();
