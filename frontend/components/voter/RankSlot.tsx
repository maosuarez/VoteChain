"use client";
import { forwardRef } from "react";
import { ordinal, pointsLabel } from "@/lib/ballot";

type Props = { slot: number; name: string | null; onOpen: () => void; onClear: () => void };

/** One ranked position: ordinal and points are always text, never only color. */
export const RankSlot = forwardRef<HTMLButtonElement, Props>(function RankSlot({ slot, name, onOpen, onClear }, ref) {
  return (
    <div className="card slot">
      <div>
        <div className="slot-title">{ordinal(slot)} lugar · {pointsLabel(slot)}</div>
        <div>{name ?? <span className="help">Sin elegir</span>}</div>
      </div>
      <div className="row">
        <button type="button" className="btn" ref={ref} onClick={onOpen}>
          {name ? `Cambiar ${ordinal(slot)} lugar` : `Elegir ${ordinal(slot)} lugar`}
        </button>
        {name && <button type="button" className="btn" onClick={onClear}>Quitar</button>}
      </div>
    </div>
  );
});
