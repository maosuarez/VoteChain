"use client";
import { useEffect, useState } from "react";
import { clearVoterSession, loadReceipts } from "@/lib/session";
import { CopyField, PageTitle } from "../ui";

const EXPLORER = process.env.NEXT_PUBLIC_EXPLORER_URL ?? "http://127.0.0.1:8000/explorer/";

export function Receipt() {
  const [receipts, setReceipts] = useState<Record<string, string> | null>(null);

  useEffect(() => {
    setReceipts(loadReceipts());
    clearVoterSession(); // credential and draft (picks) are gone once the receipt is shown
  }, []);

  if (receipts === null) return <main><p role="status">Cargando...</p></main>;
  const entries = Object.entries(receipts);
  const text = entries.map(([category, id]) => `${category}: ${id}`).join("\n");
  const href = `data:text/plain;charset=utf-8,${encodeURIComponent(`Comprobante VoteChain\n${text}\n`)}`;

  return (
    <main>
      <div aria-live="polite">
        <PageTitle>{entries.length ? "Tu voto quedó registrado" : "No hay comprobante"}</PageTitle>
      </div>
      {entries.map(([category, id]) => <CopyField key={category} label={`Comprobante de ${category}`} value={id} />)}
      <p>Guarda este número. Sirve para comprobar que tu voto está en la cadena. No revela por quién votaste.</p>
      <p className="row">
        {entries.length > 0 && <a className="btn" href={href} download="comprobante-votechain.txt">Descargar .txt</a>}
        <a className="btn" href={EXPLORER} target="_blank" rel="noreferrer">Verificar en el explorador público</a>
      </p>
    </main>
  );
}
