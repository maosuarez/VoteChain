import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

const push = vi.fn();
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push, replace: push }),
  useSearchParams: () => new URLSearchParams(),
}));
vi.mock("@/lib/api", async (orig) => ({
  ...(await orig<typeof import("@/lib/api")>()),
  listElections: vi.fn(),
  getElection: vi.fn(),
  redeemCredential: vi.fn(),
  sendBallot: vi.fn(),
}));

import * as api from "@/lib/api";
import { BallotStep } from "@/components/voter/BallotStep";
import { CodeForm } from "@/components/voter/CodeForm";
import { Receipt } from "@/components/voter/Receipt";
import { Review } from "@/components/voter/Review";
import { generateKeypair } from "@/lib/crypto";
import { loadCredential, loadDraft, loadReceipts, saveCredential, saveDraft, saveReceipts } from "@/lib/session";

const election = {
  election_id: "e1", status: "open", opens_at: 0, closes_at: 9, issuer_key: { n: "1", e: 3 },
  categories: { profesor: { a: "Ana", b: "Beto", c: "Carla", d: "Diego" } },
} as unknown as api.ElectionInfo;
const m = vi.mocked(api);

beforeEach(() => {
  vi.clearAllMocks();
  m.getElection.mockResolvedValue(election);
});

describe("CodeForm", () => {
  it("redeems with a normalized code and goes to the ballot", async () => {
    m.listElections.mockResolvedValue([election]);
    m.redeemCredential.mockResolvedValue({ electionId: "e1", privateKey: "k", signature: "s" });
    render(<CodeForm />);
    const user = userEvent.setup();
    await user.type(screen.getByLabelText("Correo institucional"), "A@x.edu");
    await user.type(screen.getByLabelText("Código"), "ab 12");
    await user.click(screen.getByRole("button", { name: "Continuar" }));
    await waitFor(() => expect(push).toHaveBeenCalledWith("/votar/papeleta"));
    expect(m.redeemCredential).toHaveBeenCalledWith(election, "a@x.edu", "AB12");
    expect(loadCredential()?.privateKey).toBe("k");
  });

  it("shows one uniform error and does not advance on rejection", async () => {
    m.listElections.mockResolvedValue([election]);
    m.redeemCredential.mockRejectedValue(new api.CredentialRejected("x"));
    render(<CodeForm />);
    const user = userEvent.setup();
    await user.type(screen.getByLabelText("Correo institucional"), "a@x.edu");
    await user.type(screen.getByLabelText("Código"), "bad");
    await user.click(screen.getByRole("button", { name: "Continuar" }));
    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent("no es válido, ya fue usado o venció");
    expect(screen.getByLabelText("Código")).toHaveAccessibleDescription(/no es válido/);
    expect(push).not.toHaveBeenCalled();
  });

  it("reports a closed election and does not offer to redeem", async () => {
    m.listElections.mockResolvedValue([{ ...election, status: "closed" }]);
    render(<CodeForm />);
    expect(await screen.findByText("La votación no está abierta.")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Continuar" }));
    expect(m.redeemCredential).not.toHaveBeenCalled();
  });
});

describe("BallotStep", () => {
  beforeEach(() => saveCredential({ electionId: "e1", privateKey: "k", signature: "s" }));

  it("disables an already chosen candidate with the reason and blocks incomplete ballots", async () => {
    render(<BallotStep />);
    const user = userEvent.setup();
    await user.click(await screen.findByRole("button", { name: "Elegir 1.º lugar" }));
    await user.click(screen.getByRole("option", { name: "Ana" }));
    await user.click(screen.getByRole("button", { name: "Elegir 2.º lugar" }));
    const ana = screen.getByRole("option", { name: /Ana/ });
    expect(ana).toHaveAttribute("aria-disabled", "true");
    expect(ana).toHaveTextContent("Ya es tu 1.º lugar");
    await user.click(ana);
    expect(screen.getByRole("listbox")).toBeInTheDocument(); // not picked, not moved
    await user.click(screen.getByRole("option", { name: "Beto" }));
    expect(loadDraft().picks.profesor).toEqual(["a", "b", null]);

    await user.click(screen.getByRole("button", { name: "Siguiente" }));
    expect(screen.getByRole("alert")).toHaveTextContent("Falta elegir tu 3.º lugar.");
    expect(screen.getByRole("button", { name: "Elegir 3.º lugar" })).toHaveFocus();
    expect(push).not.toHaveBeenCalled();
  });

  it("shows ordinal and points as text and goes to review when complete", async () => {
    saveDraft({ picks: { profesor: ["a", "b", "c"] }, signed: {} });
    render(<BallotStep />);
    expect(await screen.findByText("1.º lugar · 3 pts")).toBeInTheDocument();
    expect(screen.getByText("2.º lugar · 2 pts")).toBeInTheDocument();
    expect(screen.getByText("3.º lugar · 1 pt")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Siguiente" }));
    expect(push).toHaveBeenCalledWith("/votar/revisar");
  });

  it("blocks a category with fewer than 3 candidates", async () => {
    m.getElection.mockResolvedValue({ ...election, categories: { profesor: { a: "Ana", b: "Beto" } } });
    render(<BallotStep />);
    expect(await screen.findByText(/No hay candidatos suficientes/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Siguiente" })).toBeDisabled();
  });
});

describe("Review", () => {
  beforeEach(() => {
    saveCredential({ electionId: "e1", privateKey: generateKeypair().privateKey, signature: "ab" });
    saveDraft({ picks: { profesor: ["a", "b", "c"] }, signed: {} });
  });

  it("sends once while sending (no double submit) and stores only tx_ids", async () => {
    let release!: (id: string) => void;
    m.sendBallot.mockReturnValue(new Promise((r) => (release = r)));
    render(<Review />);
    const user = userEvent.setup();
    const button = await screen.findByRole("button", { name: "Confirmar mi voto" });
    await user.click(button);
    expect(screen.getByRole("button", { name: "Enviando tu voto..." })).toBeDisabled();
    await user.click(screen.getByRole("button", { name: "Enviando tu voto..." }));
    release("txid1");
    await waitFor(() => expect(push).toHaveBeenCalledWith("/votar/comprobante"));
    expect(m.sendBallot).toHaveBeenCalledTimes(1);
    expect(loadReceipts()).toEqual({ profesor: "txid1" });
  });

  it("keeps the selection on network error and retries the same signed tx", async () => {
    m.sendBallot.mockRejectedValueOnce(new api.NetworkError("x")).mockResolvedValueOnce("txid2");
    render(<Review />);
    const user = userEvent.setup();
    await user.click(await screen.findByRole("button", { name: "Confirmar mi voto" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Tu selección sigue guardada");
    expect(loadDraft().picks.profesor).toEqual(["a", "b", "c"]);
    await user.click(screen.getByRole("button", { name: "Reintentar" }));
    await waitFor(() => expect(push).toHaveBeenCalledWith("/votar/comprobante"));
    const [first, second] = m.sendBallot.mock.calls.map((c) => c[0]);
    expect(second).toEqual(first);
    expect(first.payload).toMatchObject({ category: "profesor", picks: ["a", "b", "c"], credential_sig: "ab" });
  });

  it("does not resend categories that already have a receipt", async () => {
    saveReceipts({ profesor: "old" });
    render(<Review />);
    await userEvent.click(await screen.findByRole("button", { name: "Confirmar mi voto" }));
    await waitFor(() => expect(push).toHaveBeenCalledWith("/votar/comprobante"));
    expect(m.sendBallot).not.toHaveBeenCalled();
  });

  it("explains a terminal rejection without retry", async () => {
    m.sendBallot.mockRejectedValue(new api.BallotRejected("x"));
    render(<Review />);
    await userEvent.click(await screen.findByRole("button", { name: "Confirmar mi voto" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("no fue aceptada");
    expect(screen.queryByRole("button", { name: "Reintentar" })).toBeNull();
  });
});

describe("Receipt", () => {
  it("shows the tx_id without picks and clears credential and draft", async () => {
    const txid = "ab".repeat(32);
    saveCredential({ electionId: "e1", privateKey: "k", signature: "s" });
    saveDraft({ picks: { profesor: ["a", "b", "c"] }, signed: {} });
    saveReceipts({ profesor: txid });
    const { container } = render(<Receipt />);
    expect(await screen.findByRole("heading", { level: 1, name: "Tu voto quedó registrado" })).toBeInTheDocument();
    expect(container).toHaveTextContent(txid.match(/.{4}/g)!.join(" "));
    expect(container).not.toHaveTextContent(/Ana|Beto|Carla/);
    expect(loadCredential()).toBeNull();
    expect(loadDraft()).toEqual({ picks: {}, signed: {} });
    expect(screen.getByRole("link", { name: /Verificar en el explorador/ })).toHaveAttribute("href", expect.stringContaining("/explorer/"));
    expect(screen.queryByText(/votar de nuevo/i)).toBeNull();
  });
});
