"""Tests für den Mail-Baustein — ohne echten SMTP-Server."""
import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import mailer                                # noqa: E402
from befund import baue_befund               # noqa: E402


def _res(status, reason="Testgrund"):
    return SimpleNamespace(overall_status=status, reason=reason)


def _befund():
    return baue_befund(_res("ROT"), _res("GRÜN"), _res("GRÜN"))


LEAD = {"betrieb": "Hotel Teststern", "ort": "Kitzbühel",
        "email": "gast@example.com", "website": "https://example.com", "typ": "Hotel"}


def test_ohne_konfiguration_kein_versand(monkeypatch):
    for k in ("SMTP_HOST", "SMTP_USER", "SMTP_PASS"):
        monkeypatch.delenv(k, raising=False)
    assert mailer.smtp_konfiguriert(None) is False
    ok, info = mailer.sende_kurzbefund(LEAD, _befund(), b"%PDF-fake", secrets=None)
    assert ok is False
    assert "SMTP nicht konfiguriert" in info


def test_versand_beide_mails(monkeypatch):
    gesendet = []
    monkeypatch.setenv("SMTP_HOST", "smtp.example.com")
    monkeypatch.setenv("SMTP_USER", "checker@example.com")
    monkeypatch.setenv("SMTP_PASS", "geheim")
    monkeypatch.setattr(mailer, "_sende", lambda secrets, msg: gesendet.append(msg))

    ok, info = mailer.sende_kurzbefund(LEAD, _befund(), b"%PDF-fake", secrets=None)
    assert ok is True and info == ""
    assert len(gesendet) == 2
    an_betrieb, an_gernot = gesendet
    assert an_betrieb["To"] == "gast@example.com"
    assert "Ampel ROT" in an_betrieb["Subject"]
    assert an_gernot["To"] == mailer.DEFAULT_NOTIFY
    assert "VERKAUFSCHANCE" in an_gernot.get_body(preferencelist=("plain",)).get_content()
    # PDF haengt an beiden Mails
    assert any(p.get_content_type() == "application/pdf" for p in an_betrieb.iter_attachments())


def test_benachrichtigung_fehlgeschlagen_ist_kein_gesamtfehler(monkeypatch):
    calls = {"n": 0}

    def _fake(secrets, msg):
        calls["n"] += 1
        if calls["n"] == 2:
            raise RuntimeError("Postfach voll")

    monkeypatch.setenv("SMTP_HOST", "smtp.example.com")
    monkeypatch.setenv("SMTP_USER", "checker@example.com")
    monkeypatch.setenv("SMTP_PASS", "geheim")
    monkeypatch.setattr(mailer, "_sende", _fake)

    ok, info = mailer.sende_kurzbefund(LEAD, _befund(), b"%PDF-fake", secrets=None)
    assert ok is True
    assert "Benachrichtigung" in info
