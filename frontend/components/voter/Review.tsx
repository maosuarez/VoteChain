"use client";
import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { BallotRejected, ElectionInfo, NetworkError, getElection, sendBallot, signBallot } from "@/lib/api";
import { ordinal, points, toPickIds, isComplete, type Picks } from "@/lib/ballot";
import { loadCredential, loadDraft, loadReceipts, saveDraft, saveReceipts } from "@/lib/session";
import { Banner, Button, PageTitle } from "../ui";

export function Review() {
  const router = useRouter();
  const [election, setElection] = useState<ElectionInfo | null>(null);
  const [picks, setPicks] = useState<Record<string, Picks>>({});
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<{ text: string; retry: boolean } | null>(null);
  const guard = useRef(false); // blocks double submit even before re-render

  useEffect(() => {
    const credential = loadCredential();
    if (!credential) { router.replace("/votar"); return; }
    getElection(credential.electionId).then(setElection).catch(() => setError({ text: "No pudimos cargar tu papeleta.", retry: false }));
    setPicks(loadDraft().picks as Record<string, Picks>);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  if (!election) return <main>{error ? <Banner>{error.text}</Banner> : <p role="status">Cargando...</p>}</main>;
  const categories = Object.keys(election.categories);
  const complete = categories.every((c) => isComplete(picks[c] ?? []));

  async function confirm() {
    const credential = loadCredential();
    if (!credential || guard.current || !election) return;
    guard.current = true;
    setSending(true);
    setError(null);
    try {
      const receipts = loadReceipts();
      for (const category of categories) {
        if (receipts[category]) continue; // already registered in a previous attempt
        const draft = loadDraft();
        // Signed once and kept: retries resend the same tx (deterministic signature).
        const tx = draft.signed[category] ?? signBallot(credential, category, toPickIds(picks[category]), Math.floor(Date.now() / 1000));
        saveDraft({ ...draft, signed: { ...draft.signed, [category]: tx } });
        receipts[category] = await sendBallot(tx);
        saveReceipts(receipts);
      }
      router.push("/votar/comprobante");
    } catch (err) {
      setError(
        err instanceof NetworkError
          ? { text: "No pudimos enviar tu voto. Tu selección sigue guardada.", retry: true }
          : err instanceof BallotRejected
            ? { text: "Tu papeleta no fue aceptada: puede que la votación haya cerrado o que ya hayas votado.", retry: false }
            : { text: "Ocurrió un error inesperado. Tu selección sigue guardada.", retry: true },
      );
      guard.current = false;
      setSending(false);
    }
  }

  return (
    <main>
      <PageTitle>Revisa tu papeleta</PageTitle>
      {categories.map((category, index) => (
        <section className="card" key={category} aria-labelledby={`cat-${index}`}>
          <h2 id={`cat-${index}`}>{category}</h2>
          <ol style={{ listStyle: "none", padding: 0 }}>
            {[0, 1, 2].map((slot) => (
              <li key={slot}>{ordinal(slot)} {election.categories[category][picks[category]?.[slot] ?? ""] ?? "—"} · {points(slot)} pts</li>
            ))}
          </ol>
          <Link href={`/votar/papeleta?cat=${index}`}>Editar {category}</Link>
        </section>
      ))}
      <p>Al confirmar, tu papeleta no se puede cambiar.</p>
      {error && (
        <Banner>
          {error.text}{" "}
          {error.retry && <Button onClick={confirm}>Reintentar</Button>}
        </Banner>
      )}
      <div className="row sticky">
        <Button onClick={() => router.push("/votar/papeleta")}>Volver</Button>
        <Button variant="primary" onClick={confirm} disabled={sending || !complete} aria-busy={sending}>
          {sending ? "Enviando tu voto..." : "Confirmar mi voto"}
        </Button>
      </div>
      <p role="status" className="help">{sending ? "No cierres esta página." : ""}</p>
    </main>
  );
}
