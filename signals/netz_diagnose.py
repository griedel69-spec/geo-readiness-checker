"""
Netz-Diagnose: liefert bei fehlgeschlagenen Abrufen (Signal 1-3) den
tatsaechlichen technischen Grund — DNS-Fehler, SSL-Hostname-Mismatch,
HTTP-Statuscode, bekannte Bot-/WAF-Hinweise aus Response-Headern — statt
des bisherigen generischen "nicht abrufbar".

Kernregel wie ueberall in geo-radar (CLAUDE.md, "Null Halluzination"): nur
tatsaechlich beobachtete Fakten, keine Vermutung. Jede Einordnung unten
enthaelt IMMER die rohe Exception-/Status-/Header-Meldung als Beleg —
die Einordnung ersetzt den Beleg nie, sie ergaenzt ihn. Wird eine Ursache
nicht sicher erkannt, bleibt der rohe Text stehen, es wird keine Kategorie
erzwungen.

Nutzung:
    from netz_diagnose import klassifiziere_exception, klassifiziere_http_status

    try:
        r = requests.get(url, ...)
        if r.status_code not in (200,):
            versuche.append(f"{scheme}: {klassifiziere_http_status(r.status_code, r.headers)}")
    except requests.RequestException as exc:
        versuche.append(f"{scheme}: {klassifiziere_exception(exc)}")
"""
from __future__ import annotations

import requests

# Bekannte Bot-Management-/WAF-Cookie-Namen. Nur EXAKT diese beobachteten
# Namen werden benannt — kein Raten bei unbekannten/neuen Anbietern.
_BEKANNTE_BOT_COOKIES = (
    "__cf_bm", "cf_clearance", "__cfduid",  # Cloudflare
    "_abck", "bm_sz", "ak_bmsc",            # Akamai Bot Manager
    "incap_ses_", "visid_incap_",           # Imperva/Incapsula
)

# Response-Header, die — wenn vorhanden — als Rohbeleg mit ausgegeben werden.
_INTERESSANTE_HEADER = ("server", "cf-ray", "x-deny-reason", "x-sucuri-id")

# Header, deren Quelle aus einer einzelnen HTTP-Antwort NICHT zuverlässig
# bestimmbar ist: sie können vom Zielserver selbst stammen (eigene
# WAF/Policy) ODER von einer Zwischenstation auf dem Abrufweg (z. B. einem
# Egress-Proxy des Scan-Systems). Ohne zusätzliche Prüfung (z. B. direkter
# Vergleich mit einem bekannt erreichbaren Host über denselben Pfad) darf
# hieraus NIE "der Zielserver blockt Bots" behauptet werden — das wäre eine
# nicht belegte Zuschreibung. Der Rohwert wird trotzdem ausgegeben, nur mit
# explizitem Hinweis auf die Unsicherheit der Quelle.
_HERKUNFT_MEHRDEUTIGE_HEADER = ("x-deny-reason",)


def _dns_fehler_erkannt(exc_text: str) -> bool:
    marker = (
        "failed to resolve",
        "name or service not known",
        "nodename nor servname",
        "nxdomain",
        "no address associated with hostname",
        "temporary failure in name resolution",
    )
    t = exc_text.lower()
    return any(m in t for m in marker)


def _ssl_hostname_mismatch_erkannt(exc_text: str) -> bool:
    marker = (
        "hostname mismatch",
        "doesn't match",
        "certificate is not valid for",
        "no alternative certificate subject name matches",
    )
    t = exc_text.lower()
    return any(m in t for m in marker)


def klassifiziere_exception(exc: Exception) -> str:
    """
    Ordnet einen einzelnen fehlgeschlagenen Verbindungsversuch ein.
    Gibt IMMER die rohe Exception-Meldung mit zurück — die Einordnung davor
    ist eine Zusatz-Erklärung, kein Ersatz für den Beleg.
    """
    raw = f"{type(exc).__name__}: {exc}"
    if _dns_fehler_erkannt(raw):
        return f"DNS: Domain nicht auflösbar (kein DNS-Eintrag) — {raw}"
    if _ssl_hostname_mismatch_erkannt(raw):
        return f"SSL: Zertifikat passt nicht zum Hostnamen — {raw}"
    if isinstance(exc, requests.exceptions.SSLError):
        return f"SSL-Fehler — {raw}"
    if isinstance(exc, requests.exceptions.ConnectTimeout):
        return f"Verbindungsaufbau-Timeout — {raw}"
    if isinstance(exc, requests.exceptions.ReadTimeout):
        return f"Timeout beim Lesen der Antwort — {raw}"
    if isinstance(exc, requests.exceptions.ConnectionError):
        return f"Verbindung fehlgeschlagen — {raw}"
    return raw


def bot_hinweise_aus_headern(headers) -> list[str]:
    """
    Sucht NUR nach tatsächlich bekannten Bot-Management-Cookie-Namen im
    Set-Cookie-Header. Liefert eine leere Liste, wenn nichts Bekanntes
    gefunden wird — es wird NIE "vermutlich Bot-Sperre" ohne Beleg behauptet.
    """
    hinweise = []
    set_cookie = headers.get("set-cookie", "") or "" if headers else ""
    for name in _BEKANNTE_BOT_COOKIES:
        if name in set_cookie:
            hinweise.append(f"Cookie \"{name}\" gefunden (bekanntes Bot-Management-Merkmal)")
    return hinweise


def klassifiziere_http_status(status: int, headers=None) -> str:
    """
    Ordnet einen ERHALTENEN, aber nicht erfolgreichen HTTP-Status ein.
    Nennt bekannte Bot-Management-Cookies und ausgewählte, tatsächlich
    vorhandene Header als Rohbeleg — nie mehr als das, was beobachtet wurde.
    """
    headers = headers or {}
    teile = [f"HTTP {status}"]
    hinweise = bot_hinweise_aus_headern(headers)
    teile.extend(hinweise)
    mehrdeutig_gefunden = False
    for h in _INTERESSANTE_HEADER:
        wert = headers.get(h)
        if wert:
            teile.append(f'Header "{h}: {wert}"')
            if h in _HERKUNFT_MEHRDEUTIGE_HEADER:
                mehrdeutig_gefunden = True
    if mehrdeutig_gefunden:
        teile.append(
            "Hinweis: Herkunft dieses Headers aus dieser einzelnen Antwort nicht "
            "eindeutig bestimmbar (Zielserver oder Zwischenstation auf dem "
            "Abrufweg, z. B. ein Netzwerk-Proxy des Scan-Systems) — kein Beleg "
            "für eine Bot-Sperre durch den Zielserver"
        )
    return " — ".join(teile) if len(teile) == 1 else f"{teile[0]} — " + "; ".join(teile[1:])
