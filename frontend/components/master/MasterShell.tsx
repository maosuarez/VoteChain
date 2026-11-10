"use client";
import { createContext, useCallback, useContext, useEffect, useRef, useState, type ReactNode } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { ApiError, NetworkError, Unauthorized } from "@/lib/api";
import { clearMasterToken, loadMasterToken } from "@/lib/session";
import { Button } from "../ui";

const IDLE_MS = 15 * 60_000;
const WARN_MS = 60_000;

type Ctx = { token: string; logout: () => void; fail: (err: unknown) => string };
const MasterContext = createContext<Ctx | null>(null);
export const useMaster = (): Ctx => {
  const ctx = useContext(MasterContext);
  if (!ctx) throw new Error("outside MasterShell");
  return ctx;
};

/** Warns WARN_MS before the idle timeout; `extend` restarts the clock. */
export function useIdle(onTimeout: () => void, idleMs = IDLE_MS, warnMs = WARN_MS) {
  const [warning, setWarning] = useState(false);
  const timers = useRef<ReturnType<typeof setTimeout>[]>([]);
  const cb = useRef(onTimeout);
  cb.current = onTimeout;

  const extend = useCallback(() => {
    timers.current.forEach(clearTimeout);
    setWarning(false);
    timers.current = [
      setTimeout(() => setWarning(true), Math.max(idleMs - warnMs, 0)),
      setTimeout(() => cb.current(), idleMs),
    ];
  }, [idleMs, warnMs]);

  useEffect(() => {
    extend();
    return () => timers.current.forEach(clearTimeout);
  }, [extend]);
  return { warning, extend };
}

export function MasterShell({ children, idleMs, warnMs }: { children: ReactNode; idleMs?: number; warnMs?: number }) {
  const router = useRouter();
  const [token, setToken] = useState<string | null>(null);

  const logout = useCallback(() => {
    clearMasterToken();
    router.push("/master");
  }, [router]);

  useEffect(() => {
    const t = loadMasterToken();
    if (t) setToken(t);
    else router.replace("/master");
  }, [router]);

  const { warning, extend } = useIdle(logout, idleMs, warnMs);

  /** Turns an API error into a banner message; a 401 ends the session. */
  const fail = useCallback((err: unknown): string => {
    if (err instanceof Unauthorized) { logout(); return "Sesión rechazada."; }
    if (err instanceof ApiError || err instanceof NetworkError) return err.message;
    return "Ocurrió un error inesperado.";
  }, [logout]);

  if (!token) return null;
  return (
    <MasterContext.Provider value={{ token, logout, fail }}>
      <header className="card row" style={{ justifyContent: "space-between" }}>
        <nav aria-label="Principal" className="row">
          <strong>VoteChain</strong>
          <Link href="/master/elecciones">Elecciones</Link>
        </nav>
        <Button onClick={logout}>Salir</Button>
      </header>
      {warning && (
        <div role="alert" className="banner">
          Tu sesión se cerrará pronto por inactividad. <Button onClick={extend}>Extender sesión</Button>
        </div>
      )}
      <div onPointerDown={() => !warning && extend()} onKeyDown={() => !warning && extend()}>{children}</div>
    </MasterContext.Provider>
  );
}

