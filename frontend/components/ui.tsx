"use client";
import { useEffect, useRef, useState, type ButtonHTMLAttributes, type ReactNode } from "react";

/** h1 that receives focus on mount (focus management on step changes). */
export function PageTitle({ children }: { children: ReactNode }) {
  const ref = useRef<HTMLHeadingElement>(null);
  useEffect(() => ref.current?.focus(), []);
  return <h1 ref={ref} tabIndex={-1}>{children}</h1>;
}

type BtnProps = ButtonHTMLAttributes<HTMLButtonElement> & { variant?: "primary" | "secondary" | "danger" };

export function Button({ variant = "secondary", className = "", ...rest }: BtnProps) {
  const cls = `btn ${variant === "primary" ? "primary" : ""} ${variant === "danger" ? "danger" : ""} ${className}`;
  return <button type="button" {...rest} className={cls.trim()} />;
}

type FieldProps = {
  id: string; label: string; value: string; onChange: (v: string) => void;
  error?: string | null; help?: string; type?: string; multiline?: boolean;
  autoComplete?: string; inputMode?: "text" | "email" | "numeric";
};

export function TextField({ id, label, value, onChange, error, help, type = "text", multiline, autoComplete, inputMode }: FieldProps) {
  const describedBy = [help ? `${id}-help` : "", error ? `${id}-error` : ""].filter(Boolean).join(" ") || undefined;
  const common = { id, value, "aria-describedby": describedBy, "aria-invalid": error ? true : undefined };
  return (
    <div className="field">
      <label htmlFor={id}>{label}</label>
      {multiline ? (
        <textarea {...common} rows={6} onChange={(e) => onChange(e.target.value)} />
      ) : (
        <input {...common} type={type} autoComplete={autoComplete} inputMode={inputMode} onChange={(e) => onChange(e.target.value)} />
      )}
      {help && <div id={`${id}-help`} className="help">{help}</div>}
      {error && <div id={`${id}-error`} role="alert" className="error">{error}</div>}
    </div>
  );
}

export function Banner({ children, kind = "error" }: { children: ReactNode; kind?: "error" | "info" }) {
  return kind === "error"
    ? <div role="alert" className="banner">{children}</div>
    : <div role="status" className="banner info">{children}</div>;
}

const STATUS_TEXT = { draft: "Borrador", open: "Abierta", closed: "Cerrada" } as const;
const STATUS_ICON = { draft: "✎", open: "●", closed: "■" } as const;

export function StatusBadge({ status }: { status: keyof typeof STATUS_TEXT }) {
  return <span className={`badge ${status}`}><span aria-hidden="true">{STATUS_ICON[status]} </span>{STATUS_TEXT[status]}</span>;
}

/** Confirmation dialog: focus moves in, Tab is trapped, Esc closes, focus returns to the opener. */
export function Modal({ title, onClose, children }: { title: string; onClose: () => void; children: ReactNode }) {
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const opener = document.activeElement as HTMLElement | null;
    const focusables = () => Array.from(ref.current?.querySelectorAll<HTMLElement>("button, input, [href]") ?? []);
    focusables()[0]?.focus();
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
      if (e.key !== "Tab") return;
      const items = focusables();
      const first = items[0], last = items[items.length - 1];
      if (e.shiftKey && document.activeElement === first) { e.preventDefault(); last?.focus(); }
      else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first?.focus(); }
    };
    document.addEventListener("keydown", onKey);
    return () => { document.removeEventListener("keydown", onKey); opener?.focus(); };
  }, [onClose]);
  return (
    <div className="modal-bg">
      <div className="modal" role="dialog" aria-modal="true" aria-labelledby="modal-title" ref={ref}>
        <h2 id="modal-title">{title}</h2>
        {children}
      </div>
    </div>
  );
}

export function CopyField({ label, value }: { label: string; value: string }) {
  const [copied, setCopied] = useCopied();
  const spaced = value.match(/.{1,4}/g)?.join(" ") ?? value;
  return (
    <div className="field">
      <div className="slot-title">{label}</div>
      <div className="mono">{spaced}</div>
      <Button onClick={() => { void navigator.clipboard?.writeText(value); setCopied(); }}>Copiar</Button>
      <span role="status" className="help"> {copied ? "Copiado" : ""}</span>
    </div>
  );
}

function useCopied(): [boolean, () => void] {
  const [copied, setCopied] = useState(false);
  return [copied, () => { setCopied(true); setTimeout(() => setCopied(false), 2000); }];
}
