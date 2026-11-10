"""`votechain` operations CLI: bootstrap, status, diagnosis, election admin, audit, servers."""
import argparse
import csv
import os
import re
import secrets
import sys
import time
from pathlib import Path
from typing import Any, Callable

import httpx
from rich.console import Console
from rich.table import Table

from votechain.audit import audit_chains
from votechain.crypto import generate_keypair
from votechain.p2p_http import parse_peers, parse_validators

console = Console()
err = Console(stderr=True, style="red")

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
MIN_VALIDATORS, MAX_VALIDATORS, BASE_VALIDATORS = 3, 5, 3
VALIDATOR_PORT = 9000
API_PORT = 8000
TIMEOUT = 15.0


class CliError(Exception):
    """User-facing failure: printed in red, exit code 1."""


# --- env file ---


def load_env_file(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, _, value = line.partition("=")
            values[key.strip()] = value.strip()
    return values


def setting(args: argparse.Namespace, option: str, env_name: str, default: str | None = None) -> str:
    value = getattr(args, option, None) or os.environ.get(env_name) or default
    if not value:
        raise CliError(f"falta {env_name} (o la opción --{option.replace('_', '-')})")
    return value


# --- init ---


def cmd_init(args: argparse.Namespace) -> int:
    n = args.validators
    if not MIN_VALIDATORS <= n <= MAX_VALIDATORS:
        raise CliError(f"--validators debe estar entre {MIN_VALIDATORS} y {MAX_VALIDATORS}")
    path = Path(args.env_file)
    if path.exists() and not args.force:
        raise CliError(f"{path} ya existe; usa --force para sobrescribirlo")
    validators = [generate_keypair() for _ in range(n)]
    master_key, _ = generate_keypair()
    ids = [f"v{i + 1}" for i in range(n)]
    peers = [f"{i}=http://{i}:{VALIDATOR_PORT}" for i in ids] + [f"api=http://api:{API_PORT}"]
    lines = [
        "# Generado por `votechain init`. Contiene secretos: no lo versiones ni lo compartas.",
        f"VOTECHAIN_MASTER_TOKEN={secrets.token_urlsafe(32)}",
        f"VOTECHAIN_MASTER_KEY={master_key}",
        f"VOTECHAIN_VALIDATORS={','.join(pub for _, pub in validators)}",
        f"VOTECHAIN_PEERS={','.join(peers)}",
        *[f"VOTECHAIN_NODE_KEY_{i.upper()}={priv}" for i, (priv, _) in zip(ids, validators)],
        f"COMPOSE_PROFILES={'extended' if n > BASE_VALIDATORS else ''}",
        "# SMTP (vacío = buzón de desarrollo en archivo, que guarda códigos en claro)",
        "VOTECHAIN_SMTP_HOST=",
        "VOTECHAIN_SMTP_PORT=587",
        "VOTECHAIN_SMTP_USER=",
        "VOTECHAIN_SMTP_PASSWORD=",
        "VOTECHAIN_SMTP_FROM=votechain@localhost",
        "VOTECHAIN_SMTP_STARTTLS=1",
    ]
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    os.chmod(path, 0o600)
    console.print(f"[green]Escrito {path}[/green] con {n} validadores (permisos 600). Secretos no mostrados.")
    return 0


# --- nodes: status / check ---


def node_urls(args: argparse.Namespace) -> dict[str, str]:
    raw = getattr(args, "nodes", None) or os.environ.get("VOTECHAIN_NODES") or os.environ.get("VOTECHAIN_PEERS")
    if not raw:
        raise CliError("faltan nodos: usa --nodes id=url,... o VOTECHAIN_NODES/VOTECHAIN_PEERS")
    return parse_peers(raw)


def get_json(url: str) -> Any | None:
    try:
        response = httpx.get(url, timeout=TIMEOUT)
        response.raise_for_status()
        return response.json()
    except (httpx.HTTPError, ValueError):
        return None


def fetch_statuses(nodes: dict[str, str]) -> dict[str, dict[str, Any] | None]:
    return {node_id: get_json(f"{url.rstrip('/')}/p2p/status") for node_id, url in nodes.items()}


def status_table(statuses: dict[str, dict[str, Any] | None]) -> Table:
    table = Table(title="Estado de la red")
    for column in ("nodo", "estado", "altura", "punta", "pendientes", "rol"):
        table.add_column(column)
    for node_id, st in statuses.items():
        if st is None:
            table.add_row(node_id, "[red]caído[/red]", "-", "-", "-", "-")
        else:
            role = "validador" if st["is_validator"] else "observador"
            table.add_row(node_id, "[green]ok[/green]", str(st["height"]), st["tip"][:12],
                          str(st["mempool"]), role)
    return table


def cmd_status(args: argparse.Namespace) -> int:
    statuses = fetch_statuses(node_urls(args))
    console.print(status_table(statuses))
    return 0 if all(statuses.values()) else 1


def trusted_validators(args: argparse.Namespace):
    return parse_validators(setting(args, "validators", "VOTECHAIN_VALIDATORS"))


def cmd_check(args: argparse.Namespace) -> int:
    nodes = node_urls(args)
    trusted = trusted_validators(args)
    statuses = fetch_statuses(nodes)
    console.print(status_table(statuses))
    problems = [f"{node_id}: no responde" for node_id, st in statuses.items() if st is None]
    chains = {
        node_id: blocks
        for node_id, url in nodes.items()
        if statuses[node_id] is not None
        and isinstance(blocks := get_json(f"{url.rstrip('/')}/p2p/chain"), list)
    }
    if chains:
        problems += audit_chains(chains, trusted).findings
    if problems:
        for p in problems:
            err.print(f"PROBLEMA: {p}")
        return 1
    console.print("[green]OK[/green]: todos los nodos responden con la misma cadena válida.")
    return 0


# --- election administration (master) ---


def admin_call(args: argparse.Namespace, method: str, path: str, body: dict[str, Any] | None = None) -> Any:
    base = setting(args, "api", "VOTECHAIN_API_URL", "http://127.0.0.1:8000").rstrip("/")
    token = setting(args, "token", "VOTECHAIN_MASTER_TOKEN")
    try:
        response = httpx.request(
            method, f"{base}{path}", json=body, headers={"Authorization": f"Bearer {token}"}, timeout=TIMEOUT
        )
    except httpx.HTTPError as e:
        raise CliError(f"API no alcanzable en {base} ({type(e).__name__})") from e
    if response.status_code == 401:
        raise CliError("token de master inválido (401)")
    if response.status_code == 503:
        raise CliError("la red no confirmó la acción (503): posible validador caído; ejecuta `votechain check`")
    if response.status_code >= 400:
        detail = response.json().get("detail") if response.headers.get("content-type", "").startswith("application/json") else ""
        raise CliError(f"rechazado ({response.status_code}): {detail}")
    return response.json()


def read_roll(path: Path) -> list[str]:
    """First column of a CSV (header `email` optional). Whole file rejected on any bad row."""
    emails: list[str] = []
    with path.open(newline="", encoding="utf-8") as f:
        for number, row in enumerate(csv.reader(f), start=1):
            if not row or not row[0].strip():
                continue
            value = row[0].strip().lower()
            if number == 1 and value == "email":
                continue
            if not EMAIL_RE.match(value):
                raise CliError(f"{path}: fila {number} no es un correo válido")
            emails.append(value)
    if not emails:
        raise CliError(f"{path}: no contiene correos")
    return emails


def cmd_election(args: argparse.Namespace) -> int:
    eid, action = args.election_id, args.action
    if action == "create":
        opens = args.opens_at if args.opens_at is not None else int(time.time())
        closes = args.closes_at if args.closes_at is not None else opens + 7 * 86400
        admin_call(args, "POST", "/admin/elections", {"election_id": eid, "opens_at": opens, "closes_at": closes})
        console.print(f"[green]Elección {eid} creada[/green] (borrador).")
    elif action == "category":
        admin_call(args, "POST", f"/admin/elections/{eid}/categories", {"category": args.name})
        console.print(f"[green]Categoría {args.name} agregada.[/green]")
    elif action == "candidate":
        admin_call(args, "POST", f"/admin/elections/{eid}/candidates",
                   {"category": args.category, "candidate_id": args.candidate_id, "name": args.name})
        console.print(f"[green]Candidato {args.candidate_id} agregado a {args.category}.[/green]")
    elif action == "voters":
        emails = read_roll(Path(args.csv))  # validated fully before anything is sent
        result = admin_call(args, "POST", f"/admin/elections/{eid}/voters", {"emails": emails})
        console.print(f"[green]Censo cargado:[/green] {result['submitted']} correos.")
    elif action == "code":
        result = admin_call(args, "POST", f"/admin/elections/{eid}/codes", {"email": args.email})
        if not result["sent"]:
            raise CliError("no se envió el código (no habilitado, ya canjeó, límite de reenvíos o fallo de correo)")
        console.print("[green]Código enviado.[/green]")
    elif action in ("open", "close"):
        admin_call(args, "POST", f"/admin/elections/{eid}/{action}")
        console.print(f"[green]Elección {eid}: {'abierta' if action == 'open' else 'cerrada'}.[/green]")
    elif action == "tally":
        print_tally(admin_call(args, "GET", f"/elections/{eid}/tally"))
    return 0


def print_tally(tally: dict[str, list[dict[str, Any]]], title: str = "Conteo") -> None:
    for category, entries in tally.items():
        table = Table(title=f"{title}: {category}")
        for column in ("#", "candidato", "puntos", "1ros", "2dos", "empate"):
            table.add_column(column)
        for e in entries:
            table.add_row(str(e["rank"]), e["name"], str(e["points"]), str(e["firsts"]),
                          str(e["seconds"]), "sí" if e["tied"] else "")
        console.print(table)


# --- audit ---


def cmd_audit(args: argparse.Namespace) -> int:
    nodes = node_urls(args)
    trusted = trusted_validators(args)
    chains: dict[str, Any] = {}
    for node_id, url in nodes.items():
        blocks = get_json(f"{url.rstrip('/')}/p2p/chain")
        if isinstance(blocks, list):
            chains[node_id] = blocks
        else:
            err.print(f"PROBLEMA: {node_id}: no se pudo descargar la cadena")
    published = None
    api = os.environ.get("VOTECHAIN_API_URL") if not getattr(args, "api", None) else args.api
    if api:
        published = get_json(f"{api.rstrip('/')}/elections/{args.election}/tally")
    report = audit_chains(chains, trusted, args.election, published, use_explorer=args.explorer)
    unreachable = len(chains) < len(nodes)
    if report.tally is not None:
        print_tally(report.tally, "Conteo recalculado desde la cadena")
    console.print(f"Altura {report.height}, punta {(report.tip or '-')[:12]}; "
                  f"verificador del explorador: {report.explorer}; "
                  f"conteo publicado: {'comparado' if published else 'no disponible (¿elección abierta?)'}")
    for finding in report.findings:
        err.print(f"PROBLEMA: {finding}")
    if report.ok and not unreachable:
        console.print("[green]AUDITORÍA OK[/green]: cadenas válidas e idénticas, conteo recalculado.")
        return 0
    return 1


# --- servers (container entrypoints) ---


def cmd_serve_node(args: argparse.Namespace) -> int:
    import uvicorn

    from votechain.p2p_http import build_node_app, runner_from_env

    uvicorn.run(build_node_app(runner_from_env(require_key=True)), host=args.host, port=args.port)
    return 0


def cmd_serve_api(args: argparse.Namespace) -> int:
    import uvicorn

    from votechain.api.app import create_api_from_env

    uvicorn.run(create_api_from_env(), host=args.host, port=args.port)
    return 0


# --- parser ---


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="votechain", description="Operación del piloto VoteChain.")
    parser.add_argument("--env", dest="global_env", help="carga VOTECHAIN_* desde este archivo .env")
    sub = parser.add_subparsers(dest="command", required=True)

    def add(name: str, func: Callable[[argparse.Namespace], int], help: str) -> argparse.ArgumentParser:
        p = sub.add_parser(name, help=help)
        p.set_defaults(func=func)
        return p

    p = add("init", cmd_init, "genera secretos y .env para compose")
    p.add_argument("--validators", type=int, default=3, help="3 a 5")
    p.add_argument("--env-file", default=".env")
    p.add_argument("--force", action="store_true")

    for name, func, help_ in (("status", cmd_status, "altura/punta de cada nodo"),
                              ("check", cmd_check, "diagnostica caídos, forks y cadenas inválidas")):
        p = add(name, func, help_)
        p.add_argument("--nodes", help="id=url,... (def. VOTECHAIN_NODES o VOTECHAIN_PEERS)")
        if name == "check":
            p.add_argument("--validators", help="claves públicas de confianza (def. VOTECHAIN_VALIDATORS)")

    p = add("audit", cmd_audit, "verifica cadenas y recalcula el conteo de forma independiente")
    p.add_argument("election", help="id de la elección")
    p.add_argument("--nodes")
    p.add_argument("--validators", help="validadores de confianza del auditor (def. VOTECHAIN_VALIDATORS)")
    p.add_argument("--api", help="API para comparar el conteo publicado")
    p.add_argument("--explorer", action=argparse.BooleanOptionalAction, default=True,
                   help="comprobar también con el verificador del explorador (Node)")

    p = add("election", cmd_election, "administración de la elección (master)")
    p.add_argument("--api", help="URL de la API (def. VOTECHAIN_API_URL)")
    p.add_argument("--token", help="token del master (def. VOTECHAIN_MASTER_TOKEN)")
    actions = p.add_subparsers(dest="action", required=True)
    specs: dict[str, list[tuple[str, dict[str, Any]]]] = {
        "create": [("--opens-at", {"type": int}), ("--closes-at", {"type": int})],
        "category": [("name", {})],
        "candidate": [("category", {}), ("candidate_id", {}), ("name", {})],
        "voters": [("csv", {})],
        "code": [("email", {})],
        "open": [], "close": [], "tally": [],
    }
    for action, arguments in specs.items():
        ap = actions.add_parser(action)
        ap.add_argument("election_id")
        for flag, kw in arguments:
            ap.add_argument(flag, **kw)

    for name, func in (("serve-node", cmd_serve_node), ("serve-api", cmd_serve_api)):
        p = add(name, func, "proceso del contenedor (configuración por VOTECHAIN_*)")
        p.add_argument("--host", default="0.0.0.0")
        p.add_argument("--port", type=int, default=VALIDATOR_PORT if name == "serve-node" else API_PORT)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.global_env:
            for key, value in load_env_file(Path(args.global_env)).items():
                os.environ.setdefault(key, value)
        return args.func(args)
    except CliError as e:
        err.print(f"ERROR: {e}")
        return 1
    except (OSError, ValueError) as e:
        err.print(f"ERROR: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
