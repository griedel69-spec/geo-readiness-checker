"""
E-Mail-Versand für den GEO-Readiness-Checker.

Zwei Mails pro Analyse:
  1. Kurz-Befund-PDF an den Betrieb (Adresse aus dem Formular).
  2. Benachrichtigung an Gernot (NOTIFY_EMAIL) bei JEDEM Versand —
     bei GELB/ROT ausdrücklich als Verkaufschance markiert.

Konfiguration über Streamlit-Secrets bzw. Umgebungsvariablen
(auf Render als Environment Variables setzen, start.sh schreibt sie
in .streamlit/secrets.toml):

    SMTP_HOST   z. B. mail.gmx.net oder smtp.office365.com
    SMTP_PORT   587 (STARTTLS, Standard)
    SMTP_USER   Login/Absender-Postfach
    SMTP_PASS   Passwort bzw. App-Passwort
    MAIL_FROM   Absenderadresse (Standard: SMTP_USER)
    NOTIFY_EMAIL  Empfänger der Benachrichtigung
                  (Standard: kontakt@gernot-riedel.com)

Ist SMTP nicht konfiguriert, schlägt der Versand kontrolliert fehl
(ok=False) — die App bietet dann das PDF als Download an.
"""
from __future__ import annotations

import base64
import os
import smtplib
import ssl
from email.message import EmailMessage

import requests

DEFAULT_NOTIFY = "kontakt@gernot-riedel.com"
BREVO_URL = "https://api.brevo.com/v3/smtp/email"
ABSENDER_NAME = "Gernot Riedel Tourism Consulting"


def _conf(secrets, key: str, default: str = "") -> str:
    """
    Liest erst Streamlit-Secrets, dann Umgebungsvariablen.
    Ein LEERER Secrets-Eintrag zaehlt als "nicht gesetzt" — start.sh schreibt
    die Schluessel immer in secrets.toml, auch wenn die Render-Variable fehlt;
    dann steht dort "" und der echte Wert kann noch in os.environ liegen.
    """
    try:
        if secrets is not None and key in secrets and str(secrets[key]).strip():
            return str(secrets[key]).strip()
    except Exception:
        pass
    return os.environ.get(key, "").strip() or default


def smtp_konfiguriert(secrets=None) -> bool:
    return all(_conf(secrets, k) for k in ("SMTP_HOST", "SMTP_USER", "SMTP_PASS"))


def _absender(secrets) -> str:
    return _conf(secrets, "MAIL_FROM") or _conf(secrets, "SMTP_USER")


def transport(secrets=None) -> str:
    """
    Welcher Versandweg ist aktiv?
    'brevo' = Web-API (HTTPS) — funktioniert auch dort, wo die Cloud
              direkte SMTP-Verbindungen blockt (z. B. Render).
    'smtp'  = klassischer SMTP-Versand.
    ''      = nichts konfiguriert.
    """
    if _conf(secrets, "BREVO_API_KEY") and _absender(secrets):
        return "brevo"
    if smtp_konfiguriert(secrets):
        return "smtp"
    return ""


def smtp_status(secrets=None) -> dict:
    """
    Diagnose fuer den Admin-Bereich: welche Einstellungen sieht die App?
    Gibt NIE Werte von Passwoertern/Schluesseln zurueck — nur ob etwas gesetzt ist.
    """
    t = transport(secrets)
    return {
        "Transport": {"brevo": "Brevo (Web-API)", "smtp": "SMTP"}.get(t, "❌ nicht konfiguriert"),
        "BREVO_API_KEY_gesetzt": bool(_conf(secrets, "BREVO_API_KEY")),
        "Absender": _absender(secrets),
        "SMTP_HOST": _conf(secrets, "SMTP_HOST"),          # Hostname ist unkritisch
        "SMTP_PORT": _conf(secrets, "SMTP_PORT", "587"),
        "SMTP_USER": _conf(secrets, "SMTP_USER"),          # Absender-Adresse
        "SMTP_PASS_gesetzt": bool(_conf(secrets, "SMTP_PASS")),
        "NOTIFY_EMAIL": _conf(secrets, "NOTIFY_EMAIL", DEFAULT_NOTIFY),
    }


def _sende_brevo(secrets, empfaenger: str, betreff: str, text: str,
                 anhaenge: list | None = None) -> None:
    """Versand ueber die Brevo-Web-API (HTTPS) — kein SMTP-Port noetig."""
    payload = {
        "sender": {"email": _absender(secrets), "name": ABSENDER_NAME},
        "to": [{"email": empfaenger}],
        "subject": betreff,
        "textContent": text,
    }
    if anhaenge:
        payload["attachment"] = [
            {"name": name, "content": base64.b64encode(daten).decode("ascii")}
            for name, daten in anhaenge
        ]
    r = requests.post(
        BREVO_URL, json=payload, timeout=30,
        headers={"api-key": _conf(secrets, "BREVO_API_KEY"),
                 "accept": "application/json"},
    )
    if r.status_code not in (200, 201, 202):
        raise RuntimeError(f"Brevo-Antwort {r.status_code}: {r.text[:300]}")


def _versende(secrets, empfaenger: str, betreff: str, text: str,
              anhaenge: list | None = None) -> None:
    """Eine Mail über den aktiven Versandweg schicken (wirft bei Fehler)."""
    if transport(secrets) == "brevo":
        _sende_brevo(secrets, empfaenger, betreff, text, anhaenge)
        return
    msg = EmailMessage()
    msg["From"] = _absender(secrets)
    msg["To"] = empfaenger
    msg["Subject"] = betreff
    msg.set_content(text)
    for name, daten in (anhaenge or []):
        msg.add_attachment(daten, maintype="application", subtype="pdf", filename=name)
    _sende(secrets, msg)


def sende_testmail(secrets=None) -> tuple[bool, str]:
    """Schickt eine kurze Testmail an NOTIFY_EMAIL und meldet den exakten Fehler."""
    t = transport(secrets)
    if not t:
        return False, ("Versand nicht konfiguriert — es fehlt entweder "
                       "BREVO_API_KEY (+ MAIL_FROM) oder SMTP_HOST/SMTP_USER/SMTP_PASS")
    notify = _conf(secrets, "NOTIFY_EMAIL", DEFAULT_NOTIFY)
    try:
        _versende(secrets, notify,
                  "✅ GEO-Checker Test-Mail — Versand funktioniert",
                  "Diese Test-Mail wurde aus dem Admin-Bereich des "
                  "GEO-Readiness-Checkers verschickt. "
                  f"Aktiver Versandweg: {t}.")
        return True, f"Test-Mail an {notify} verschickt (Weg: {t})."
    except Exception as e:
        return False, f"Versand fehlgeschlagen: {type(e).__name__}: {e}"


def _sende(secrets, msg: EmailMessage) -> None:
    host = _conf(secrets, "SMTP_HOST")
    port = int(_conf(secrets, "SMTP_PORT", "587"))
    user = _conf(secrets, "SMTP_USER")
    pw = _conf(secrets, "SMTP_PASS")
    ctx = ssl.create_default_context()
    # Port 465 = direkte SSL-Verbindung (SMTPS), alles andere = STARTTLS.
    # Manche Anbieter (z. B. GMX) nehmen Verbindungen von Cloud-Servern
    # auf 587 nicht an — dann in Render einfach SMTP_PORT=465 setzen.
    if port == 465:
        with smtplib.SMTP_SSL(host, port, timeout=20, context=ctx) as s:
            s.login(user, pw)
            s.send_message(msg)
    else:
        with smtplib.SMTP(host, port, timeout=20) as s:
            s.starttls(context=ctx)
            s.login(user, pw)
            s.send_message(msg)


def sende_kurzbefund(lead: dict, befund: dict, pdf_bytes: bytes,
                     secrets=None) -> tuple[bool, str]:
    """
    Verschickt Kurz-Befund an den Betrieb UND Benachrichtigung an Gernot.
    Rückgabe: (ok, fehlertext). ok ist nur True, wenn die Betriebs-Mail
    raus ist; scheitert nur die Benachrichtigung, wird das im Text vermerkt.
    """
    if not transport(secrets):
        return False, ("Versand nicht konfiguriert — es fehlt entweder "
                       "BREVO_API_KEY (+ MAIL_FROM) oder SMTP_HOST/SMTP_USER/SMTP_PASS")

    notify = _conf(secrets, "NOTIFY_EMAIL", DEFAULT_NOTIFY)
    betrieb = lead.get("betrieb", "Ihr Betrieb")
    ampel = befund["overall"]
    dateiname = f"GEO-Kurz-Befund_{betrieb.replace(' ', '_')}.pdf"
    anhaenge = [(dateiname, pdf_bytes)]

    # ── Mail 1: an den Betrieb ──
    text_betrieb = (
        f"Guten Tag,\n\n"
        f"vielen Dank für Ihre kostenlose GEO-Analyse von {lead.get('website', '')}.\n\n"
        f"Ihr Ergebnis: Gesamt-Ampel {ampel}.\n"
        f"{befund['klartext']}\n\n"
        f"Den vollständigen Kurz-Befund mit den drei Prüfbereichen und den "
        f"nächsten Schritten finden Sie im angehängten PDF.\n\n"
        f"Bei Fragen antworten Sie einfach auf diese E-Mail.\n\n"
        f"Freundliche Grüße\n"
        f"Gernot Riedel\n"
        f"Gernot Riedel Tourism Consulting · TÜV-zertifizierter KI-Trainer\n"
        f"kontakt@gernot-riedel.com · +43 676 7237811 · gernot-riedel.com\n"
    )
    try:
        _versende(secrets, lead.get("email", ""),
                  f"Ihr GEO-Kurz-Befund: Ampel {ampel} — {betrieb}",
                  text_betrieb, anhaenge)
    except Exception as e:
        return False, f"Versand an Betrieb fehlgeschlagen: {e}"

    # ── Mail 2: Benachrichtigung an Gernot (bei jedem Versand) ──
    chance = ("💰 VERKAUFSCHANCE (GELB/ROT) — Verkaufs-Brücke ist im PDF enthalten."
              if befund["verkaufsbruecke"] else "Ampel GRÜN — kein akuter Bedarf.")
    signale = "\n".join(
        f"  - {s['name']}: {s['status']} — {s['grund']}" for s in befund["signale"]
    )
    text_gernot = (
        f"Der Kurz-Befund wurde soeben automatisch versendet.\n\n"
        f"Betrieb:  {betrieb}\n"
        f"Ort:      {lead.get('ort', '')}\n"
        f"Typ:      {lead.get('typ', '')}\n"
        f"Website:  {lead.get('website', '')}\n"
        f"E-Mail:   {lead.get('email', '')}\n\n"
        f"Gesamt-Ampel: {ampel}\n{signale}\n\n"
        f"{chance}\n"
    )
    try:
        _versende(secrets, notify,
                  f"🔔 GEO-Checker Versand: {betrieb} — Ampel {ampel}",
                  text_gernot, anhaenge)
    except Exception as e:
        return True, f"Befund versendet, aber Benachrichtigung an {notify} fehlgeschlagen: {e}"

    return True, ""
