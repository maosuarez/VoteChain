import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { act, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

const push = vi.fn();
vi.mock("next/navigation", () => ({ useRouter: () => ({ push, replace: push }) }));
vi.mock("@/lib/api", async (orig) => ({
  ...(await orig<typeof import("@/lib/api")>()),
  validateMasterToken: vi.fn(),
  getElection: vi.fn(),
  fetchChainTxs: vi.fn(),
  listElections: vi.fn(),
  addCandidate: vi.fn(),
  addCategory: vi.fn(),
  openElection: vi.fn(),
  closeElection: vi.fn(),
  loadRoll: vi.fn(),
  sendCode: vi.fn(),
}));

import * as api from "@/lib/api";
import { ElectionDetail } from "@/components/master/ElectionDetail";
import { LoginForm } from "@/components/master/LoginForm";
import { MasterShell } from "@/components/master/MasterShell";
import { clearMasterToken, loadMasterToken, saveMasterToken } from "@/lib/session";

const m = vi.mocked(api);
const election = (over: Partial<api.ElectionInfo> = {}) =>
  ({
    election_id: "e1", status: "draft", opens_at: 0, closes_at: 9, issuer_key: { n: "1", e: 3 },
    categories: { profesor: { a: "Ana", b: "Beto", c: "Carla" } }, ...over,
  }) as api.ElectionInfo;

async function renderDetail(e: api.ElectionInfo, tab?: string) {
  m.getElection.mockResolvedValue(e);
  m.fetchChainTxs.mockResolvedValue([]);
  saveMasterToken("tok");
  const user = userEvent.setup();
  render(<MasterShell><ElectionDetail id="e1" /></MasterShell>);
  await screen.findByRole("heading", { level: 1, name: "e1" });
  if (tab) await user.click(screen.getByRole("tab", { name: tab }));
  return user;
}

beforeEach(() => vi.clearAllMocks());

describe("LoginForm", () => {
  it("rejects a token answered with 401", async () => {
    m.validateMasterToken.mockResolvedValue(false);
    render(<LoginForm />);
    const user = userEvent.setup();
    await user.type(screen.getByLabelText("Token de administrador"), "bad");
    await user.click(screen.getByRole("button", { name: "Entrar" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("El token no es válido");
    expect(push).not.toHaveBeenCalled();
    expect(loadMasterToken()).toBeNull();
  });

  it("stores a valid token in sessionStorage and enters the panel", async () => {
    m.validateMasterToken.mockResolvedValue(true);
    render(<LoginForm />);
    const user = userEvent.setup();
    await user.type(screen.getByLabelText("Token de administrador"), "good");
    await user.click(screen.getByRole("button", { name: "Entrar" }));
    await waitFor(() => expect(push).toHaveBeenCalledWith("/master/elecciones"));
    expect(loadMasterToken()).toBe("good");
  });
});

describe("ElectionDetail", () => {
  it("disables Abrir with pending prerequisites and lists them", async () => {
    const user = await renderDetail(election({ categories: { profesor: { a: "Ana" } } }), "Estado");
    expect(screen.getByRole("button", { name: "Abrir votación" })).toBeDisabled();
    expect(screen.getByText(/profesor: al menos 3 candidatos \(pendiente\)/)).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Abrir votación" }));
    expect(m.openElection).not.toHaveBeenCalled();
  });

  it("opens through a confirmation modal", async () => {
    m.openElection.mockResolvedValue({});
    const user = await renderDetail(election(), "Estado");
    await user.click(screen.getByRole("button", { name: "Abrir votación" }));
    const dialog = screen.getByRole("dialog");
    expect(dialog).toHaveTextContent("categorías y candidatos quedan bloqueados");
    await user.click(within(dialog).getByRole("button", { name: "Abrir ahora" }));
    expect(m.openElection).toHaveBeenCalledWith("tok", "e1");
  });

  it("closing needs the election name typed; open status shows votes and no ranking", async () => {
    m.closeElection.mockResolvedValue({});
    m.getElection.mockResolvedValue(election({ status: "open" }));
    m.fetchChainTxs.mockResolvedValue([
      { type: "CAST_BALLOT", payload: { election_id: "e1" } },
    ] as never);
    saveMasterToken("tok");
    const user = userEvent.setup();
    render(<MasterShell><ElectionDetail id="e1" /></MasterShell>);
    await user.click(await screen.findByRole("tab", { name: "Estado" }));
    expect(screen.getByText(/Votos emitidos/)).toHaveTextContent("1");
    expect(screen.queryByText(/ranking/i, { selector: "th, h2, td" })).toBeNull();
    await user.click(screen.getByRole("button", { name: "Cerrar votación" }));
    const confirm = screen.getByRole("button", { name: "Cerrar definitivamente" });
    await user.type(screen.getByLabelText("Nombre de la elección"), "otro");
    expect(confirm).toBeDisabled();
    await user.clear(screen.getByLabelText("Nombre de la elección"));
    await user.type(screen.getByLabelText("Nombre de la elección"), "e1");
    expect(confirm).toBeEnabled();
    await user.click(confirm);
    expect(m.closeElection).toHaveBeenCalledWith("tok", "e1");
  });

  it("does not send a duplicate candidate", async () => {
    const user = await renderDetail(election(), "Candidatos");
    await user.type(screen.getByLabelText("Nuevo candidato"), "ana");
    await user.click(screen.getByRole("button", { name: "Añadir candidato" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Candidato repetido");
    expect(m.addCandidate).not.toHaveBeenCalled();
  });

  it("CSV preview marks bad rows and applies only valid ones", async () => {
    m.addCandidate.mockResolvedValue({});
    const user = await renderDetail(election(), "Candidatos");
    await user.click(screen.getByLabelText(/Lista de candidatos/));
    await user.paste("Diego\nCarla\nDiego");
    expect(screen.getByRole("status")).toHaveTextContent("1 válidos, 2 con error");
    await user.click(screen.getByRole("button", { name: "Aplicar filas válidas" }));
    await waitFor(() => expect(m.addCandidate).toHaveBeenCalledTimes(1));
    expect(m.addCandidate).toHaveBeenCalledWith("tok", "e1", "profesor", "diego", "Diego");
  });

  it("hides editing forms when the election is not draft", async () => {
    await renderDetail(election({ status: "open" }), "Candidatos");
    expect(screen.queryByRole("button", { name: "Añadir candidato" })).toBeNull();
    await userEvent.click(screen.getByRole("tab", { name: "Categorías" }));
    expect(screen.queryByRole("button", { name: "Añadir categoría" })).toBeNull();
  });

  it("loads only valid unique emails into the census", async () => {
    m.loadRoll.mockResolvedValue({ submitted: 1 });
    const user = await renderDetail(election(), "Censo");
    await user.click(screen.getByLabelText(/Correos institucionales/));
    await user.paste("a@x.edu\nA@x.edu\nmal");
    await user.click(screen.getByRole("button", { name: "Cargar censo" }));
    await waitFor(() => expect(m.loadRoll).toHaveBeenCalledWith("tok", "e1", ["a@x.edu"]));
    expect(await screen.findByText("1 correos enviados al censo.")).toBeInTheDocument();
  });

  it("resends a code after confirmation", async () => {
    m.sendCode.mockResolvedValue({ sent: true });
    const user = await renderDetail(election(), "Censo");
    await user.type(screen.getByLabelText("Reenviar código a"), "a@x.edu");
    await user.click(screen.getByRole("button", { name: "Reenviar código" }));
    expect(m.sendCode).not.toHaveBeenCalled();
    await user.click(within(screen.getByRole("dialog")).getByRole("button", { name: "Reenviar" }));
    expect(m.sendCode).toHaveBeenCalledWith("tok", "e1", "a@x.edu");
    expect(await screen.findByText("Código reenviado.")).toBeInTheDocument();
  });

  it("shows the domain reason from a 409 in an alert banner", async () => {
    m.addCategory.mockRejectedValue(new api.ApiError(409, "election is not draft"));
    const user = await renderDetail(election());
    await user.type(screen.getByLabelText("Nueva categoría"), "nueva");
    await user.click(screen.getByRole("button", { name: "Añadir categoría" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("election is not draft");
    expect(screen.getByLabelText("Nueva categoría")).toHaveValue("nueva"); // input kept
  });

  it("a 401 ends the session", async () => {
    m.addCategory.mockRejectedValue(new api.Unauthorized("x"));
    const user = await renderDetail(election());
    await user.type(screen.getByLabelText("Nueva categoría"), "nueva");
    await user.click(screen.getByRole("button", { name: "Añadir categoría" }));
    await waitFor(() => expect(push).toHaveBeenCalledWith("/master"));
    expect(loadMasterToken()).toBeNull();
  });
});

describe("MasterShell inactivity", () => {
  beforeEach(() => vi.useFakeTimers());
  afterEach(() => { vi.useRealTimers(); clearMasterToken(); });

  it("warns before the timeout, can be extended, and logs out otherwise", async () => {
    saveMasterToken("tok");
    render(<MasterShell idleMs={10_000} warnMs={3_000}><p>contenido</p></MasterShell>);
    act(() => { vi.advanceTimersByTime(9_000); });
    expect(screen.getByRole("alert")).toHaveTextContent("inactividad");
    act(() => { screen.getByRole("button", { name: "Extender sesión" }).click(); });
    expect(screen.queryByRole("alert")).toBeNull();
    act(() => { vi.advanceTimersByTime(9_000); });
    expect(push).not.toHaveBeenCalledWith("/master");
    act(() => { vi.advanceTimersByTime(2_000); });
    expect(push).toHaveBeenCalledWith("/master");
    expect(loadMasterToken()).toBeNull();
  });
});
