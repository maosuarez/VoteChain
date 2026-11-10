"use client";
import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { ElectionInfo, createElection, listElections } from "@/lib/api";
import { toEpochSeconds } from "@/lib/master";
import { Banner, Button, PageTitle, StatusBadge, TextField } from "../ui";
import { useMaster } from "./MasterShell";

const fmt = (s: number) => new Date(s * 1000).toLocaleString();

export function ElectionsList() {
  const { token, fail } = useMaster();
  const [elections, setElections] = useState<ElectionInfo[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [id, setId] = useState("");
  const [opens, setOpens] = useState("");
  const [closes, setCloses] = useState("");
  const [fieldError, setFieldError] = useState<string | null>(null);

  const load = useCallback(() => {
    listElections().then(setElections).catch((e) => setError(fail(e)));
  }, [fail]);
  useEffect(load, [load]);

  async function create(e: React.FormEvent) {
    e.preventDefault();
    const o = toEpochSeconds(opens), c = toEpochSeconds(closes);
    if (!id.trim()) return setFieldError("Escribe un identificador.");
    if (o === null || c === null || o >= c) return setFieldError("La fecha de cierre debe ser posterior a la de apertura.");
    setFieldError(null);
    try {
      await createElection(token, id.trim(), o, c);
      setId("");
      load();
    } catch (err) {
      setError(fail(err));
    }
  }

  return (
    <main className="wide">
      <PageTitle>Elecciones</PageTitle>
      {error && <Banner>{error} <Button onClick={() => { setError(null); load(); }}>Reintentar</Button></Banner>}
      <section className="card" aria-labelledby="new-election">
        <h2 id="new-election">Nueva elección</h2>
        <form onSubmit={create} noValidate>
          <TextField id="eid" label="Identificador" value={id} onChange={setId} error={fieldError} />
          <TextField id="opens" label="Apertura" type="datetime-local" value={opens} onChange={setOpens} />
          <TextField id="closes" label="Cierre" type="datetime-local" value={closes} onChange={setCloses} />
          <Button type="submit" variant="primary">Crear elección</Button>
        </form>
      </section>
      {elections?.length === 0 && <p>Aún no hay elecciones. Crea la primera.</p>}
      {elections && elections.length > 0 && (
        <table>
          <thead><tr><th>Nombre</th><th>Estado</th><th>Apertura</th><th>Cierre</th></tr></thead>
          <tbody>
            {elections.map((x) => (
              <tr key={x.election_id}>
                <td><Link href={`/master/elecciones/${encodeURIComponent(x.election_id)}`}>{x.election_id}</Link></td>
                <td><StatusBadge status={x.status} /></td>
                <td>{fmt(x.opens_at)}</td>
                <td>{fmt(x.closes_at)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </main>
  );
}
