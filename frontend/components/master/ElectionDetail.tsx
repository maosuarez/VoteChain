"use client";
import { useCallback, useEffect, useState } from "react";
import { ElectionInfo, addCandidate, addCategory, closeElection, countBallots, fetchChainTxs, getElection, loadRoll, openElection, sendCode } from "@/lib/api";
import { parseCandidates, parseEmails, validValues, slugify, type Row } from "@/lib/csv";
import { canConfirmClose, canOpen, openPrerequisites } from "@/lib/master";
import { Banner, Button, Modal, PageTitle, StatusBadge, TextField } from "../ui";
import { useMaster } from "./MasterShell";

const EXPLORER = process.env.NEXT_PUBLIC_EXPLORER_URL ?? "http://127.0.0.1:8000/explorer/";
const TABS = ["Categorías", "Candidatos", "Censo", "Estado"] as const;
type Tab = (typeof TABS)[number];

function Preview<T>({ rows }: { rows: Row<T>[] }) {
  if (rows.length === 0) return null;
  const ok = rows.filter((r) => !r.error).length;
  return (
    <div>
      <p role="status">{ok} válidos, {rows.length - ok} con error.</p>
      <ul>{rows.map((r) => <li key={r.line} className={r.error ? "error" : ""}>Fila {r.line}: {r.raw}{r.error ? ` — ${r.error}` : ""}</li>)}</ul>
    </div>
  );
}

export function ElectionDetail({ id }: { id: string }) {
  const { token, fail } = useMaster();
  const [election, setElection] = useState<ElectionInfo | null>(null);
  const [ballots, setBallots] = useState(0);
  const [tab, setTab] = useState<Tab>("Categorías");
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [modal, setModal] = useState<"open" | "close" | "resend" | null>(null);

  const refresh = useCallback(async () => {
    try {
      setElection(await getElection(id));
      setBallots(countBallots(await fetchChainTxs(), id));
    } catch (e) {
      setError(fail(e));
    }
  }, [id, fail]);

  useEffect(() => { void refresh(); }, [refresh]);
  useEffect(() => {
    if (tab !== "Estado") return;
    const t = setInterval(() => void refresh(), 15_000);
    return () => clearInterval(t);
  }, [tab, refresh]);

  const run = async (action: () => Promise<unknown>, okMessage?: string) => {
    setError(null);
    try {
      await action();
      if (okMessage) setNotice(okMessage);
      await refresh();
      return true;
    } catch (e) {
      setError(fail(e));
      return false;
    }
  };

  // --- form state ---
  const [category, setCategory] = useState("");
  const [catError, setCatError] = useState<string | null>(null);
  const [candCategory, setCandCategory] = useState("");
  const [candName, setCandName] = useState("");
  const [candError, setCandError] = useState<string | null>(null);
  const [candCsv, setCandCsv] = useState("");
  const [rollCsv, setRollCsv] = useState("");
  const [resendEmail, setResendEmail] = useState("");
  const [typed, setTyped] = useState("");

  if (!election) return <main className="wide">{error ? <Banner>{error}</Banner> : <p role="status">Cargando...</p>}</main>;

  const draft = election.status === "draft";
  const categories = Object.keys(election.categories);
  const selectedCat = candCategory || categories[0] || "";
  const existing = election.categories[selectedCat] ?? {};
  // Compare against ids and name slugs: candidates created outside this UI may use other ids.
  const existingIds = [...Object.keys(existing), ...Object.values(existing).map(slugify)];
  const candRows = parseCandidates(candCsv, existingIds);
  const rollRows = parseEmails(rollCsv);

  async function submitCategory(e: React.FormEvent) {
    e.preventDefault();
    const name = category.trim();
    if (!name) return setCatError("Escribe el nombre de la categoría.");
    if (categories.includes(name)) return setCatError("Esa categoría ya existe.");
    setCatError(null);
    if (await run(() => addCategory(token, id, name))) setCategory("");
  }

  async function submitCandidate(e: React.FormEvent) {
    e.preventDefault();
    const [row] = parseCandidates(candName, existingIds);
    if (!selectedCat) return setCandError("Primero crea una categoría.");
    if (!row || row.error || !row.value) return setCandError(row?.error ?? "Escribe el nombre del candidato.");
    setCandError(null);
    if (await run(() => addCandidate(token, id, selectedCat, row.value!.id, row.value!.name))) setCandName("");
  }

  async function applyCandidates() {
    const valid = validValues(candRows);
    const ok = await run(async () => {
      for (const c of valid) await addCandidate(token, id, selectedCat, c.id, c.name);
    }, `${valid.length} candidatos añadidos.`);
    if (ok) setCandCsv("");
  }

  async function applyRoll() {
    const emails = validValues(rollRows);
    let submitted = 0;
    const ok = await run(async () => { submitted = (await loadRoll(token, id, emails)).submitted; });
    if (ok) { setNotice(`${submitted} correos enviados al censo.`); setRollCsv(""); }
  }

  async function confirmResend() {
    setModal(null);
    let sent = false;
    const ok = await run(async () => { sent = (await sendCode(token, id, resendEmail.trim())).sent; });
    if (ok) setNotice(sent ? "Código reenviado." : "No se pudo reenviar el código a ese correo.");
  }

  return (
    <main className="wide">
      <PageTitle>{id}</PageTitle>
      <p><StatusBadge status={election.status} /></p>
      {error && <Banner>{error}</Banner>}
      {notice && <Banner kind="info">{notice}</Banner>}
      <div role="tablist" aria-label="Secciones" className="tabs">
        {TABS.map((t) => (
          <button key={t} role="tab" type="button" className="btn" aria-selected={tab === t}
            aria-controls="panel" id={`tab-${t}`} onClick={() => setTab(t)}>{t}</button>
        ))}
      </div>
      <div role="tabpanel" id="panel" aria-labelledby={`tab-${tab}`} className="card">
        {tab === "Categorías" && (
          <>
            {categories.length === 0 ? <p>Aún no hay categorías.</p> : <ul>{categories.map((c) => <li key={c}>{c}</li>)}</ul>}
            {draft && (
              <form onSubmit={submitCategory} noValidate>
                <TextField id="category" label="Nueva categoría" value={category} onChange={setCategory} error={catError} help="Por ejemplo: administrativo, profesor." />
                <Button type="submit" variant="primary">Añadir categoría</Button>
              </form>
            )}
          </>
        )}
        {tab === "Candidatos" && (
          <>
            {categories.length === 0 && <p>Primero crea una categoría.</p>}
            {categories.length > 0 && (
              <div className="field">
                <label htmlFor="cand-cat">Categoría</label>
                <select id="cand-cat" value={selectedCat} onChange={(e) => setCandCategory(e.target.value)}>
                  {categories.map((c) => <option key={c}>{c}</option>)}
                </select>
              </div>
            )}
            <ul>{Object.values(election.categories[selectedCat] ?? {}).map((n) => <li key={n}>{n}</li>)}</ul>
            {draft && selectedCat && (
              <>
                <form onSubmit={submitCandidate} noValidate>
                  <TextField id="cand-name" label="Nuevo candidato" value={candName} onChange={setCandName} error={candError}
                    help={candName && slugify(candName) ? `Identificador: ${slugify(candName)}` : undefined} />
                  <Button type="submit" variant="primary">Añadir candidato</Button>
                </form>
                <TextField id="cand-csv" label="Lista de candidatos (un nombre por línea)" multiline value={candCsv} onChange={setCandCsv} />
                <Preview rows={candRows} />
                <Button onClick={applyCandidates} disabled={validValues(candRows).length === 0}>Aplicar filas válidas</Button>
              </>
            )}
          </>
        )}
        {tab === "Censo" && (
          <>
            <TextField id="roll" label="Correos institucionales (uno por línea)" multiline value={rollCsv} onChange={setRollCsv}
              help="Los correos solo se guardan en el servidor, nunca en la cadena." />
            <Preview rows={rollRows} />
            <Button onClick={applyRoll} disabled={validValues(rollRows).length === 0}>Cargar censo</Button>
            <hr />
            <TextField id="resend" label="Reenviar código a" type="email" value={resendEmail} onChange={setResendEmail} />
            <Button onClick={() => setModal("resend")} disabled={!resendEmail.trim()}>Reenviar código</Button>
          </>
        )}
        {tab === "Estado" && (
          <>
            <p>Votos emitidos (papeletas en la cadena): <strong>{ballots}</strong></p>
            <p className="help">El ranking se publica solo al cerrar la votación.</p>
            <h2>Prerrequisitos para abrir</h2>
            <ul>{openPrerequisites(election).map((p) => <li key={p.label}><span aria-hidden="true">{p.done ? "✓" : "○"}</span> {p.label} ({p.done ? "listo" : "pendiente"})</li>)}</ul>
            {election.status === "draft" && <Button variant="primary" disabled={!canOpen(election)} onClick={() => setModal("open")}>Abrir votación</Button>}
            {election.status === "open" && <Button variant="danger" onClick={() => { setTyped(""); setModal("close"); }}>Cerrar votación</Button>}
            {election.status === "closed" && (
              <p>Resultado definitivo; no se puede reabrir. <a href={EXPLORER} target="_blank" rel="noreferrer">Ver resultados en el explorador público</a></p>
            )}
          </>
        )}
      </div>

      {modal === "open" && (
        <Modal title="Abrir votación" onClose={() => setModal(null)}>
          <p>Al abrir, categorías y candidatos quedan bloqueados. ¿Abrir ahora?</p>
          <div className="row">
            <Button onClick={() => setModal(null)}>Cancelar</Button>
            <Button variant="primary" onClick={() => { setModal(null); void run(() => openElection(token, id)); }}>Abrir ahora</Button>
          </div>
        </Modal>
      )}
      {modal === "close" && (
        <Modal title="Cerrar votación" onClose={() => setModal(null)}>
          <p>Se emitieron {ballots} papeletas. El cierre es definitivo. Escribe <strong>{id}</strong> para confirmar.</p>
          <TextField id="confirm-close" label="Nombre de la elección" value={typed} onChange={setTyped} />
          <div className="row">
            <Button onClick={() => setModal(null)}>Cancelar</Button>
            <Button variant="danger" disabled={!canConfirmClose(typed, id)}
              onClick={() => { setModal(null); void run(() => closeElection(token, id), "La votación se cerró. Resultado definitivo."); }}>
              Cerrar definitivamente
            </Button>
          </div>
        </Modal>
      )}
      {modal === "resend" && (
        <Modal title="Reenviar código" onClose={() => setModal(null)}>
          <p>¿Reenviar un código nuevo a {resendEmail.trim()}?</p>
          <div className="row">
            <Button onClick={() => setModal(null)}>Cancelar</Button>
            <Button variant="primary" onClick={() => void confirmResend()}>Reenviar</Button>
          </div>
        </Modal>
      )}
    </main>
  );
}
