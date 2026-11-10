"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { validateMasterToken } from "@/lib/api";
import { saveMasterToken } from "@/lib/session";
import { Button, PageTitle, TextField } from "../ui";

export function LoginForm() {
  const router = useRouter();
  const [token, setToken] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!token.trim() || busy) return;
    setBusy(true);
    setError(null);
    try {
      if (await validateMasterToken(token.trim())) {
        saveMasterToken(token.trim());
        router.push("/master/elecciones");
        return;
      }
      setError("El token no es válido.");
    } catch {
      setError("No pudimos conectar con el servidor.");
    }
    setBusy(false);
  }

  return (
    <main>
      <PageTitle>Administración</PageTitle>
      <form onSubmit={submit} noValidate>
        <TextField id="token" label="Token de administrador" type="password" autoComplete="off" value={token} onChange={setToken} error={error} />
        <Button type="submit" variant="primary" disabled={busy}>{busy ? "Verificando..." : "Entrar"}</Button>
      </form>
    </main>
  );
}
