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
    for k in ("SMTP_HOST", "SMTP_USER", "SMTP_PASS", "BREVO_API_KEY", "MAIL_FROM"):
        monkeypatch.delenv(k, raising=False)
    assert mailer.transport(None) == ""
    ok, info = mailer.sende_kurzbefund(LEAD, _befund(), b"%PDF-fake", secrets=None)
    assert ok is False
    assert "Versand nicht konfiguriert" in info


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


def test_leerer_secrets_eintrag_faellt_auf_umgebung_zurueck(monkeypatch):
    # start.sh schreibt SMTP-Schluessel auch leer in secrets.toml —
    # ein leerer Eintrag darf den echten Wert aus os.environ nicht verdecken.
    monkeypatch.setenv("SMTP_HOST", "smtp.example.com")
    secrets = {"SMTP_HOST": ""}
    assert mailer._conf(secrets, "SMTP_HOST") == "smtp.example.com"


def test_testmail_meldet_fehlende_schluessel(monkeypatch):
    for k in ("SMTP_HOST", "SMTP_USER", "SMTP_PASS", "BREVO_API_KEY", "MAIL_FROM"):
        monkeypatch.delenv(k, raising=False)
    ok, info = mailer.sende_testmail(None)
    assert ok is False
    assert "Versand nicht konfiguriert" in info


def test_brevo_hat_vorrang_und_sendet_beide_mails(monkeypatch):
    posts = []

    class FakeResponse:
        status_code = 201
        text = "ok"

    def fake_post(url, json=None, timeout=None, headers=None):
        posts.append({"url": url, "json": json, "headers": headers})
        return FakeResponse()

    monkeypatch.setattr(mailer.requests, "post", fake_post)
    monkeypatch.setenv("BREVO_API_KEY", "xkeysib-test")
    monkeypatch.setenv("MAIL_FROM", "kontakt@gernot-riedel.com")
    for k in ("SMTP_HOST", "SMTP_USER", "SMTP_PASS"):
        monkeypatch.delenv(k, raising=False)

    assert mailer.transport(None) == "brevo"
    ok, info = mailer.sende_kurzbefund(LEAD, _befund(), b"%PDF-fake", secrets=None)
    assert ok is True and info == ""
    assert len(posts) == 2
    an_betrieb, an_gernot = posts
    assert an_betrieb["json"]["to"] == [{"email": "gast@example.com"}]
    assert an_betrieb["json"]["sender"]["email"] == "kontakt@gernot-riedel.com"
    assert an_betrieb["headers"]["api-key"] == "xkeysib-test"
    # PDF haengt base64-kodiert an
    import base64
    assert base64.b64decode(an_betrieb["json"]["attachment"][0]["content"]) == b"%PDF-fake"
    assert an_gernot["json"]["to"] == [{"email": mailer.DEFAULT_NOTIFY}]
    assert "VERKAUFSCHANCE" in an_gernot["json"]["textContent"]


def test_brevo_fehlerantwort_wird_gemeldet(monkeypatch):
    class FakeResponse:
        status_code = 401
        text = "Key not found"

    monkeypatch.setattr(mailer.requests, "post",
                        lambda *a, **kw: FakeResponse())
    monkeypatch.setenv("BREVO_API_KEY", "falsch")
    monkeypatch.setenv("MAIL_FROM", "kontakt@gernot-riedel.com")
    ok, info = mailer.sende_testmail(None)
    assert ok is False
    assert "401" in info


def test_testmail_erfolgreich(monkeypatch):
    gesendet = []
    monkeypatch.setenv("SMTP_HOST", "smtp.example.com")
    monkeypatch.setenv("SMTP_USER", "checker@example.com")
    monkeypatch.setenv("SMTP_PASS", "geheim")
    monkeypatch.setattr(mailer, "_sende", lambda secrets, msg: gesendet.append(msg))
    ok, info = mailer.sende_testmail(None)
    assert ok is True
    assert gesendet[0]["To"] == mailer.DEFAULT_NOTIFY


def test_port_465_nutzt_ssl_direkt(monkeypatch):
    aufrufe = []

    class FakeSMTP:
        def __init__(self, host, port, timeout=None, context=None):
            aufrufe.append((type(self).__name__, host, port))
        def __enter__(self): return self
        def __exit__(self, *a): return False
        def starttls(self, context=None): aufrufe.append(("starttls",))
        def login(self, u, p): pass
        def send_message(self, m): pass

    class FakeSMTPSSL(FakeSMTP):
        pass

    monkeypatch.setattr(mailer.smtplib, "SMTP", FakeSMTP)
    monkeypatch.setattr(mailer.smtplib, "SMTP_SSL", FakeSMTPSSL)
    monkeypatch.setenv("SMTP_HOST", "mail.gmx.net")
    monkeypatch.setenv("SMTP_USER", "x@gmx.at")
    monkeypatch.setenv("SMTP_PASS", "geheim")

    monkeypatch.setenv("SMTP_PORT", "465")
    ok, _ = mailer.sende_testmail(None)
    assert ok is True
    assert aufrufe[0][0] == "FakeSMTPSSL"
    assert ("starttls",) not in aufrufe

    aufrufe.clear()
    monkeypatch.setenv("SMTP_PORT", "587")
    ok, _ = mailer.sende_testmail(None)
    assert ok is True
    assert aufrufe[0][0] == "FakeSMTP"
    assert ("starttls",) in aufrufe
