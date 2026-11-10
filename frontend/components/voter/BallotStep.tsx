"use client";
import { useEffect, useRef, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { ElectionInfo, getElection } from "@/lib/api";
import { canVoteIn, clearPick, emptyPicks, firstEmptySlot, isComplete, missingMessage, setPick, type Picks } from "@/lib/ballot";
import { loadCredential, loadDraft, saveDraft } from "@/lib/session";
import { Banner, Button, PageTitle } from "../ui";
import { CandidateSelector } from "./CandidateSelector";
import { RankSlot } from "./RankSlot";

export function BallotStep() {
  const router = useRouter();
  const startAt = Number(useSearchParams().get("cat") ?? 0) || 0;
  const [election, setElection] = useState<ElectionInfo | null>(null);
  const [failed, setFailed] = useState(false);
  const [step, setStep] = useState(startAt);
  const [picksBy, setPicksBy] = useState<Record<string, Picks>>({});
  const [openSlot, setOpenSlot] = useState<number | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const slotRefs = useRef<(HTMLButtonElement | null)[]>([]);
  const credential = loadCredential();

  useEffect(() => {
    if (!credential) { router.replace("/votar"); return; }
    getElection(credential.electionId).then(setElection).catch(() => setFailed(true));
    setPicksBy(loadDraft().picks as Record<string, Picks>);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  if (failed) return <main><Banner>No pudimos cargar los candidatos.</Banner><Button onClick={() => location.reload()}>Reintentar</Button></main>;
  if (!election) return <main><p role="status">Cargando papeleta...</p></main>;

  const categories = Object.keys(election.categories);
  const category = categories[step];
  const candidates = election.categories[category] ?? {};
  const picks = picksBy[category] ?? emptyPicks();
  const enough = canVoteIn(Object.keys(candidates).length);

  const update = (next: Picks) => {
    const all = { ...picksBy, [category]: next };
    setPicksBy(all);
    const draft = loadDraft();
    saveDraft({ ...draft, picks: all, signed: {} }); // changed picks invalidate signed txs
    setMessage(null);
  };

  const next = () => {
    if (!isComplete(picks)) {
      setMessage(missingMessage(picks));
      slotRefs.current[firstEmptySlot(picks)]?.focus();
      return;
    }
    if (step + 1 < categories.length) setStep(step + 1);
    else router.push("/votar/revisar");
  };

  return (
    <main>
      <p aria-live="polite" className="help">Categoría {step + 1} de {categories.length}</p>
      <PageTitle>{category}</PageTitle>
      <p>Elige 3, en orden</p>
      {!enough && <Banner>No hay candidatos suficientes en esta categoría. Avisa al administrador.</Banner>}
      {[0, 1, 2].map((slot) => (
        <RankSlot key={slot} slot={slot} name={picks[slot] ? candidates[picks[slot]!] : null}
          ref={(el) => { slotRefs.current[slot] = el; }}
          onOpen={() => setOpenSlot(slot)} onClear={() => update(clearPick(picks, slot))} />
      ))}
      {openSlot !== null && (
        <CandidateSelector candidates={candidates} picks={picks} slot={openSlot}
          onSelect={(id) => { update(setPick(picks, openSlot, id)); setOpenSlot(null); slotRefs.current[openSlot]?.focus(); }}
          onClose={() => setOpenSlot(null)} />
      )}
      {message && <p role="alert" className="error">{message}</p>}
      <div className="row sticky">
        <Button onClick={() => (step > 0 ? setStep(step - 1) : router.push("/votar"))}>Atrás</Button>
        <Button variant="primary" onClick={next} disabled={!enough}>Siguiente</Button>
      </div>
    </main>
  );
}
