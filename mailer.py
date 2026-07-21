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

import os
import smtplib
import ssl
from email.message import EmailMessage

DEFAULT_NOTIFY = "kontakt@gernot-riedel.com"


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


def smtp_status(secrets=None) -> dict:
    """
    Diagnose fuer den Admin-Bereich: welche Einstellungen sieht die App?
    Gibt NIE Werte von Passwoertern zurueck — nur ob etwas gesetzt ist.
    """
    return {
        "SMTP_HOST": _conf(secrets, "SMTP_HOST"),          # Hostname ist unkritisch
        "SMTP_PORT": _conf(secrets, "SMTP_PORT", "587"),
        "SMTP_USER": _conf(secrets, "SMTP_USER"),          # Absender-Adresse
        "SMTP_PASS_gesetzt": bool(_conf(secrets, "SMTP_PASS")),
        "NOTIFY_EMAIL": _conf(secrets, "NOTIFY_EMAIL", DEFAULT_NOTIFY),
    }


def sende_testmail(secrets=None) -> tuple[bool, str]:
    """Schickt eine kurze Testmail an NOTIFY_EMAIL und meldet den exakten Fehler."""
    if not smtp_konfiguriert(secrets):
        fehlend = [k for k in ("SMTP_HOST", "SMTP_USER", "SMTP_PASS")
                   if not _conf(secrets, k)]
        return False, f"SMTP nicht konfiguriert — fehlend: {', '.join(fehlend)}"
    absender = _conf(secrets, "MAIL_FROM") or _conf(secrets, "SMTP_USER")
    notify = _conf(secrets, "NOTIFY_EMAIL", DEFAULT_NOTIFY)
    msg = EmailMessage()
    msg["From"] = absender
    msg["To"] = notify
    msg["Subject"] = "✅ GEO-Checker Test-Mail — SMTP funktioniert"
    msg.set_content("Diese Test-Mail wurde aus dem Admin-Bereich des "
                    "GEO-Readiness-Checkers verschickt. Der Versand funktioniert.")
    try:
        _sende(secrets, msg)
        return True, f"Test-Mail an {notify} verschickt."
    except Exception as e:
        return False, f"Versand fehlgeschlagen: {type(e).__name__}: {e}"


def _sende(secrets, msg: EmailMessage) -> None:
    host = _conf(secrets, "SMTP_HOST")
    port = int(_conf(secrets, "SMTP_PORT", "587"))
    user = _conf(secrets, "SMTP_USER")
    pw = _conf(secrets, "SMTP_PASS")
    ctx = ssl.create_default_context()
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
    if not smtp_konfiguriert(secrets):
        return False, "SMTP nicht konfiguriert (SMTP_HOST/SMTP_USER/SMTP_PASS fehlen)"

    absender = _conf(secrets, "MAIL_FROM") or _conf(secrets, "SMTP_USER")
    notify = _conf(secrets, "NOTIFY_EMAIL", DEFAULT_NOTIFY)
    betrieb = lead.get("betrieb", "Ihr Betrieb")
    ampel = befund["overall"]
    dateiname = f"GEO-Kurz-Befund_{betrieb.replace(' ', '_')}.pdf"

    # ── Mail 1: an den Betrieb ──
    m1 = EmailMessage()
    m1["From"] = absender
    m1["To"] = lead.get("email", "")
    m1["Subject"] = f"Ihr GEO-Kurz-Befund: Ampel {ampel} — {betrieb}"
    m1.set_content(
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
    m1.add_attachment(pdf_bytes, maintype="application", subtype="pdf",
                      filename=dateiname)

    try:
        _sende(secrets, m1)
    except Exception as e:
        return False, f"Versand an Betrieb fehlgeschlagen: {e}"

    # ── Mail 2: Benachrichtigung an Gernot (bei jedem Versand) ──
    chance = ("💰 VERKAUFSCHANCE (GELB/ROT) — Verkaufs-Brücke ist im PDF enthalten."
              if befund["verkaufsbruecke"] else "Ampel GRÜN — kein akuter Bedarf.")
    signale = "\n".join(
        f"  - {s['name']}: {s['status']} — {s['grund']}" for s in befund["signale"]
    )
    m2 = EmailMessage()
    m2["From"] = absender
    m2["To"] = notify
    m2["Subject"] = f"🔔 GEO-Checker Versand: {betrieb} — Ampel {ampel}"
    m2.set_content(
        f"Der Kurz-Befund wurde soeben automatisch versendet.\n\n"
        f"Betrieb:  {betrieb}\n"
        f"Ort:      {lead.get('ort', '')}\n"
        f"Typ:      {lead.get('typ', '')}\n"
        f"Website:  {lead.get('website', '')}\n"
        f"E-Mail:   {lead.get('email', '')}\n\n"
        f"Gesamt-Ampel: {ampel}\n{signale}\n\n"
        f"{chance}\n"
    )
    m2.add_attachment(pdf_bytes, maintype="application", subtype="pdf",
                      filename=dateiname)

    try:
        _sende(secrets, m2)
    except Exception as e:
        return True, f"Befund versendet, aber Benachrichtigung an {notify} fehlgeschlagen: {e}"

    return True, ""
