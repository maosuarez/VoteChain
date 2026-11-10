from pathlib import Path

DOCS = Path(__file__).resolve().parents[1] / "docs"


def test_pilot_docs_exist() -> None:
    for name in ("guia-master.md", "checklist-seguridad.md", "guia-auditoria.md"):
        assert (DOCS / name).read_text(encoding="utf-8").strip(), name


def test_audit_guide_declares_human_audit_pending() -> None:
    text = (DOCS / "guia-auditoria.md").read_text(encoding="utf-8")
    assert "PENDIENTE" in text and "no sustituye" in text


def test_master_guide_warns_about_dev_mailbox() -> None:
    assert "claro" in (DOCS / "guia-master.md").read_text(encoding="utf-8")
