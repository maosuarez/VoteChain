"use client";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { CredentialRejected, ElectionInfo, listElections, normalizeCode, redeemCredential } from "@/lib/api";
import { saveCredential } from "@/lib/session";
import { Banner, Button, PageTitle, TextField } from "../ui";

export function CodeForm() {
  const router = useRouter();
  const [elections, setElections] = useState<ElectionInfo[] | null>(null);
  const [selected, setSelected] = useState("");
  const [email, setEmail] = useState("");
  const [code, setCode] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [loadError, setLoadError] = useState(false);

  useEffect(() => {
    listElections()
      .then((all) => {
        setElections(all);
        const open = all.filter((e) => e.status === "open");
        if (open.length === 1) setSelected(open[0].election_id);
      })
      .catch(() => setLoadError(true));
  }, []);

  const open = (elections ?? []).filter((e) => e.status === "open");
  const ready = selected !== "" && email.trim() !== "" && normalizeCode(code) !== "";

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!ready || busy) return;
    const election = open.find((x) => x.election_id === selected);
    if (!election) return;
    setBusy(true);
    setError(null);
    try {
      saveCredential(await redeemCredential(election, email.trim().toLowerCase(), normalizeCode(code)));
      router.push("/votar/papeleta");
    } catch (err) {
      setError(
        err instanceof CredentialRejected
          ? "Este código no es válido, ya fue usado o venció. Solo hay un voto por persona; si crees que es un error, pide ayuda al administrador."
          : "No pudimos conectar con el servidor. Intenta de nuevo.",
      );
      setBusy(false);
    }
  }

  return (
    <main>
      <PageTitle>Ingresa tu código</PageTitle>
      {loadError && <Banner>No pudimos cargar las elecciones. Recarga la página.</Banner>}
      {elections !== null && open.length === 0 && <Banner>La votación no está abierta.</Banner>}
      <form onSubmit={submit} noValidate>
        {open.length > 1 && (
          <div className="field">
            <label htmlFor="election">Elección</label>
            <select id="election" value={selected} onChange={(e) => setSelected(e.target.value)}>
              <option value="">Elige una elección</option>
              {open.map((x) => <option key={x.election_id} value={x.election_id}>{x.election_id}</option>)}
            </select>
          </div>
        )}
        <TextField id="email" label="Correo institucional" type="email" autoComplete="email" inputMode="email" value={email} onChange={setEmail} />
        <TextField id="code" label="Código" autoComplete="one-time-code" value={code} onChange={setCode}
          help="Pégalo tal como llegó a tu correo; los espacios se ignoran." error={error} />
        <Button type="submit" variant="primary" aria-disabled={!ready || busy} disabled={busy}>
          {busy ? "Verificando..." : "Continuar"}
        </Button>
        <p className="help">Tu voto no queda ligado a tu nombre.</p>
      </form>
    </main>
  );
}
