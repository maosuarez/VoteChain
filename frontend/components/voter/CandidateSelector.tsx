"use client";
import { useEffect, useRef, useState } from "react";
import { disabledReason, type Picks } from "@/lib/ballot";

type Props = {
  candidates: Record<string, string>; // id -> name
  picks: Picks;
  slot: number;
  onSelect: (id: string) => void;
  onClose: () => void;
};

/** Listbox with arrows / Enter / Esc; used candidates stay visible, disabled, with the reason. */
export function CandidateSelector({ candidates, picks, slot, onSelect, onClose }: Props) {
  const [query, setQuery] = useState("");
  const [active, setActive] = useState(0);
  const listRef = useRef<HTMLUListElement>(null);
  const entries = Object.entries(candidates).filter(([, name]) => name.toLowerCase().includes(query.toLowerCase()));

  useEffect(() => {
    listRef.current?.querySelectorAll<HTMLElement>('[role="option"]')[active]?.focus();
  }, [active, query]);

  const choose = (id: string) => {
    if (disabledReason(picks, slot, id) === null) onSelect(id);
  };

  const onKey = (e: React.KeyboardEvent) => {
    if (e.key === "Escape") onClose();
    else if (e.key === "ArrowDown") { e.preventDefault(); setActive((a) => Math.min(a + 1, entries.length - 1)); }
    else if (e.key === "ArrowUp") { e.preventDefault(); setActive((a) => Math.max(a - 1, 0)); }
  };

  return (
    <div onKeyDown={onKey}>
      {Object.keys(candidates).length > 8 && (
        <div className="field">
          <label htmlFor="cand-search">Buscar candidato</label>
          <input id="cand-search" value={query} onChange={(e) => { setQuery(e.target.value); setActive(0); }} />
        </div>
      )}
      <ul className="listbox" role="listbox" aria-label="Candidatos" ref={listRef}>
        {entries.map(([id, name], i) => {
          const reason = disabledReason(picks, slot, id);
          return (
            <li
              key={id}
              role="option"
              tabIndex={i === active ? 0 : -1}
              aria-selected={picks[slot] === id}
              aria-disabled={reason !== null}
              onClick={() => choose(id)}
              onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); choose(id); } }}
            >
              {name}{reason && <span className="help"> · {reason}</span>}
            </li>
          );
        })}
        {entries.length === 0 && <li className="help" style={{ padding: 12 }}>Sin resultados.</li>}
      </ul>
      <button type="button" className="btn" onClick={onClose}>Cancelar</button>
    </div>
  );
}
