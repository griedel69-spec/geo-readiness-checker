"""
Signal 1: KI-Crawler-Zugang (robots.txt)

Frage: Sperrt die Website KI-Systeme aus, bevor sie Inhalte lesen können?

Vollständige Bau-Vorgaben stehen in CLAUDE.md, Abschnitt "Signal 1".
Dieses Modul hält sich strikt an die dort definierten Bot-Listen,
Schwellen und die eiserne Regel: "Null Halluzination — UNBEKANNT statt raten".

Nutzung als CLI:
    python src/signal1_robots.py hotel-example.at

Nutzung als Bibliothek:
    from signal1_robots import check_robots
    result = check_robots("hotel-example.at")
    print(result.overall_status)
"""
from __future__ import annotations

import os
import re
import sys
from dataclasses import dataclass, field
from typing import Optional

import requests


# -----------------------------------------------------------------------------
# Bot-Listen — exakt wie in CLAUDE.md Abschnitt "Signal 1" definiert.
# Reihenfolge bewusst so gelassen, wie sie in CLAUDE.md steht (für Reports).
# -----------------------------------------------------------------------------

# Klasse A: sichtbarkeitskritisch (Retrieval/Suche).
# Wenn einer davon geblockt ist -> ROT.
KLASSE_A_BOTS = [
    "OAI-SearchBot",
    "ChatGPT-User",
    "PerplexityBot",
    "Perplexity-User",
    "Claude-User",
    "Claude-SearchBot",
    "Google-Extended",
    "Bingbot",
]

# Klasse B: Trainingsbots (langsame Wirkung).
# Wenn nur Klasse B geblockt ist, aber A frei -> GELB.
KLASSE_B_BOTS = [
    "GPTBot",
    "ClaudeBot",
    "CCBot",
    "Applebot-Extended",
    "Bytespider",
]


# -----------------------------------------------------------------------------
# Konfiguration mit Fallback auf Environment (.env wird von scanner.py geladen)
# -----------------------------------------------------------------------------

DEFAULT_USER_AGENT = os.environ.get(
    "GEO_RADAR_USER_AGENT",
    "GEO-Radar/0.1 (+contact: gernotriedel@gmx.at)",
)
DEFAULT_TIMEOUT = int(os.environ.get("GEO_RADAR_HTTP_TIMEOUT", "15"))


# -----------------------------------------------------------------------------
# Datentypen: strukturierte Ergebnisse mit BELEG (Klartext-Zeile aus robots.txt)
# -----------------------------------------------------------------------------

@dataclass
class BotResult:
    """Pro Bot: erlaubt/blockiert plus die Beleg-Zeile aus robots.txt."""
    name: str
    klasse: str          # "A" oder "B"
    allowed: bool        # True = darf lesen, False = blockiert
    beleg: str           # Klartext-Zeile oder Erklärung
    matched_agent: Optional[str]  # welche User-agent-Zeile hat gematcht ("*" oder Bot-Name)


@dataclass
class RobotsResult:
    """Gesamt-Ergebnis der robots.txt-Prüfung."""
    domain: str
    fetched_url: Optional[str] = None
    fetched_status: Optional[int] = None
    fetch_error: Optional[str] = None
    global_block: bool = False
    global_block_evidence: Optional[str] = None
    bots: list[BotResult] = field(default_factory=list)
    overall_status: str = "UNBEKANNT"  # GRÜN | GELB | ROT | UNBEKANNT
    reason: str = ""                    # Kurzbegruendung für die Ampel


# -----------------------------------------------------------------------------
# 1. robots.txt abrufen (Redirects folgen — https bevorzugt, http als Fallback)
# -----------------------------------------------------------------------------

def _fetch_robots(
    domain: str,
    user_agent: str = DEFAULT_USER_AGENT,
    timeout: int = DEFAULT_TIMEOUT,
) -> tuple[str, str, int] | tuple[None, None, Optional[int]]:
    """
    Holt robots.txt am finalen Host (Redirects folgen).

    Rückgabe bei Erfolg (Status 200):  (final_url, text, 200)
    Rückgabe bei 404 / anderem 4xx:    (final_url, "", status_code)
                                        -> "keine robots.txt" = alles erlaubt
    Rückgabe bei Netzwerk-Fehler/5xx:  (None, None, status_code_or_None)
                                        -> UNBEKANNT
    """
    headers = {"User-Agent": user_agent, "Accept": "text/plain, */*;q=0.1"}
    last_status = None

    # Nur 404 und 410 werden als "robots.txt existiert nicht" ausgelegt
    # (siehe HTTP-Spec: 404 = Not Found, 410 = Gone). Andere 4xx wie 401/403
    # bedeuten "Zugriff verweigert" — das kann alles sein (Bot-Blocker,
    # Rate-Limit, Zwischen-Proxy) — nicht "keine robots.txt". -> UNBEKANNT.
    ABSENT_STATUS = (404, 410)

    for scheme in ("https", "http"):
        url = f"{scheme}://{domain}/robots.txt"
        try:
            r = requests.get(url, headers=headers, timeout=timeout, allow_redirects=True)
            last_status = r.status_code
            if r.status_code == 200:
                return r.url, r.text, 200
            if r.status_code in ABSENT_STATUS:
                # Klarer "existiert nicht" -> nach robots.txt-Spec: alles erlaubt.
                return r.url, "", r.status_code
            # Alles andere (401, 403, sonstiges 4xx, 5xx): unklarer Zugriff.
            # Naechstes Schema probieren, sonst am Ende -> UNBEKANNT.
        except requests.RequestException:
            # Timeout, DNS-Fehler, Connection-Reset -> nächstes Schema probieren
            continue

    return None, None, last_status


# -----------------------------------------------------------------------------
# 2. robots.txt parsen -> Liste von Gruppen [(user_agents, rules)]
# -----------------------------------------------------------------------------

_DIRECTIVE_RE = re.compile(r"^([A-Za-z][A-Za-z0-9\-]*)\s*:\s*(.*)$")


def _parse_groups(text: str) -> list[tuple[list[str], list[tuple[str, str, str]]]]:
    """
    Zerlegt robots.txt in User-agent-Gruppen.

    Regel (robots.txt-Standard):
    - Aufeinanderfolgende `User-agent:`-Zeilen gehören zur selben Gruppe.
    - Sobald nach `User-agent`(s) mindestens eine Regel (Allow/Disallow) folgte,
      startet der nächste `User-agent` eine neue Gruppe.

    Rückgabe:
        Liste von (agents, rules), wobei
          agents = ["GPTBot", "ChatGPT-User", ...]  (Namen wie in robots.txt)
          rules  = [(directive_lowercase, value, original_line), ...]
    """
    groups: list[tuple[list[str], list[tuple[str, str, str]]]] = []
    current_agents: list[str] = []
    current_rules: list[tuple[str, str, str]] = []
    just_saw_rule = False

    for raw in text.splitlines():
        # Kommentare entfernen (alles ab #), dann trimmen
        line = raw.split("#", 1)[0].strip()
        if not line:
            continue
        m = _DIRECTIVE_RE.match(line)
        if not m:
            # Malformed line — einfach ignorieren
            continue

        directive = m.group(1).strip().lower()
        value = m.group(2).strip()

        if directive == "user-agent":
            # Wenn wir schon Regeln haben, ist das der Start einer neuen Gruppe
            if just_saw_rule and current_agents:
                groups.append((current_agents, current_rules))
                current_agents = []
                current_rules = []
                just_saw_rule = False
            current_agents.append(value)

        elif directive in ("allow", "disallow"):
            # Regel gehoert zur aktuellen User-agent-Gruppe.
            # Regeln ohne vorherige User-agent-Zeile ignorieren wir (fehlerhaft).
            if current_agents:
                current_rules.append((directive, value, raw.strip()))
                just_saw_rule = True
        # Andere Direktiven (Sitemap, Crawl-delay, Host) sind für diese
        # Prüfung irrelevant und werden ignoriert.

    # Letzte Gruppe abschließen
    if current_agents:
        groups.append((current_agents, current_rules))

    return groups


# -----------------------------------------------------------------------------
# 3. Für einen Bot die spezifischste passende Gruppe finden
# -----------------------------------------------------------------------------

def _find_group_for_bot(
    bot_name: str,
    groups: list[tuple[list[str], list[tuple[str, str, str]]]],
) -> tuple[list[str], list[tuple[str, str, str]], str] | None:
    """
    Case-insensitive: sucht eine Gruppe, in der der Bot-Name exakt gelistet ist.
    Rückgabe (agents, rules, matched_agent_line) oder None.

    Gemäß robots.txt-Regel schlägt eine eigene Gruppe die *-Gruppe.
    Wenn ein Bot in mehreren Gruppen vorkommt (selten), nehmen wir die erste —
    das ist im Regelfall dieselbe wie "die spezifischste".
    """
    bot_lower = bot_name.lower()
    for agents, rules in groups:
        for a in agents:
            if a.lower() == bot_lower:
                return agents, rules, a
    return None


# -----------------------------------------------------------------------------
# 4. Aus einer Regelgruppe ableiten, ob die Wurzel `/` erlaubt ist
# -----------------------------------------------------------------------------

def _is_root_allowed(
    rules: list[tuple[str, str, str]],
) -> tuple[bool, str]:
    """
    Prüft ausschließlich die Wurzel `/`.

    Regel:
      - `Disallow: /` blockiert die ganze Site.
      - `Disallow:` (leerer Wert) = explizites "nichts gesperrt".
      - `Allow: /` in derselben Gruppe hebt ein `Disallow: /` auf.
      - Keine der beiden Zeilen vorhanden -> nicht gesperrt.

    Rückgabe: (allowed, beleg_zeile)
    """
    has_root_disallow = False
    disallow_line = ""
    has_root_allow = False
    allow_line = ""
    empty_disallow_line = ""

    for directive, value, orig in rules:
        if directive == "disallow" and value == "/":
            has_root_disallow = True
            disallow_line = orig
        elif directive == "disallow" and value == "":
            # "Disallow:" leer = ausdrückliche Freigabe
            empty_disallow_line = orig
        elif directive == "allow" and value == "/":
            has_root_allow = True
            allow_line = orig

    if has_root_disallow and has_root_allow:
        return True, f"{allow_line}  (hebt {disallow_line} auf)"
    if has_root_disallow:
        return False, disallow_line
    if empty_disallow_line:
        return True, empty_disallow_line
    if not rules:
        return True, "leere Regelgruppe"
    return True, "kein 'Disallow: /' in dieser Gruppe"


# -----------------------------------------------------------------------------
# 5. Hauptfunktion: eine Domain prüfen
# -----------------------------------------------------------------------------

def evaluate_robots_text(
    text: str,
    http_status: int = 200,
    domain: str = "",
    fetched_url: Optional[str] = None,
) -> RobotsResult:
    """
    Reine Auswertung: nimmt robots.txt-Text (und den HTTP-Status, unter dem er
    geholt wurde) und liefert das RobotsResult. Kein Netzwerk-Zugriff.

    Wird sowohl von check_robots() nach dem Fetch aufgerufen als auch von
    Tests, die vorgefertigte robots.txt-Beispiele durchspielen.
    """
    result = RobotsResult(domain=domain)
    result.fetched_url = fetched_url
    result.fetched_status = http_status

    # 404/410 = robots.txt existiert nicht -> alles erlaubt = GRÜN.
    # Leerer 200-Body = robots.txt vorhanden aber ohne Regeln -> GRÜN.
    # Andere Status (401/403/andere 4xx/5xx) sollten von _fetch_robots gar
    # nicht bis hier durchkommen — falls doch: UNBEKANNT (ehrlicher als GRÜN).
    absent = http_status in (404, 410)
    empty_ok = http_status == 200 and not text.strip()
    if absent or empty_ok:
        if absent:
            beleg = f"robots.txt nicht vorhanden (HTTP {http_status}) — laut Standard alles erlaubt"
        else:
            beleg = "robots.txt vorhanden, aber leer — laut Standard alles erlaubt"
        for name in KLASSE_A_BOTS:
            result.bots.append(BotResult(name, "A", True, beleg, None))
        for name in KLASSE_B_BOTS:
            result.bots.append(BotResult(name, "B", True, beleg, None))
        result.overall_status = "GRÜN"
        result.reason = "keine relevante robots.txt gefunden"
        return result

    if http_status != 200:
        # z. B. 401/403 direkt an evaluate_robots_text übergeben -> ehrlich UNBEKANNT.
        result.overall_status = "UNBEKANNT"
        result.reason = (
            f"robots.txt-Zugriff verweigert (HTTP {http_status}) — "
            "keine sichere Aussage möglich"
        )
        return result

    # Text parsen
    groups = _parse_groups(text)

    # *-Gruppe merken (für Fallback und Global-Block-Prüfung)
    star_group_rules: list[tuple[str, str, str]] | None = None
    for agents, rules in groups:
        if any(a.strip() == "*" for a in agents):
            star_group_rules = rules
            break

    # Global-Block via User-agent: *
    if star_group_rules is not None:
        allowed_root, evidence = _is_root_allowed(star_group_rules)
        if not allowed_root:
            result.global_block = True
            result.global_block_evidence = f"User-agent: * -> {evidence}"

    # Pro Bot prüfen
    def _check_bot(name: str, klasse: str) -> None:
        found = _find_group_for_bot(name, groups)
        if found is not None:
            _, rules, matched = found
            allowed, evidence = _is_root_allowed(rules)
            beleg = f"User-agent: {matched} -> {evidence}"
            result.bots.append(BotResult(name, klasse, allowed, beleg, matched))
            return

        # Kein eigener Eintrag -> *-Gruppe zieht
        if star_group_rules is not None:
            allowed, evidence = _is_root_allowed(star_group_rules)
            beleg = f"kein eigener Eintrag; User-agent: * -> {evidence}"
            result.bots.append(BotResult(name, klasse, allowed, beleg, "*"))
            return

        # Weder eigener Eintrag noch *-Gruppe -> implizit erlaubt
        result.bots.append(
            BotResult(name, klasse, True,
                      "kein eigener Eintrag und kein *-Eintrag — implizit erlaubt",
                      None)
        )

    for name in KLASSE_A_BOTS:
        _check_bot(name, "A")
    for name in KLASSE_B_BOTS:
        _check_bot(name, "B")

    # Ampel gemäß CLAUDE.md-Schwellen
    any_a_blocked = any(not b.allowed for b in result.bots if b.klasse == "A")
    any_b_blocked = any(not b.allowed for b in result.bots if b.klasse == "B")

    if result.global_block or any_a_blocked:
        result.overall_status = "ROT"
        reasons = []
        if result.global_block:
            reasons.append("Global-Block auf *")
        if any_a_blocked:
            blocked_a = [b.name for b in result.bots if b.klasse == "A" and not b.allowed]
            reasons.append("Klasse-A blockiert: " + ", ".join(blocked_a))
        result.reason = " | ".join(reasons)
    elif any_b_blocked:
        result.overall_status = "GELB"
        blocked_b = [b.name for b in result.bots if b.klasse == "B" and not b.allowed]
        result.reason = "Klasse-B blockiert: " + ", ".join(blocked_b)
    else:
        result.overall_status = "GRÜN"
        result.reason = "alle relevanten Bots erlaubt"

    return result


def check_robots(
    domain: str,
    user_agent: str = DEFAULT_USER_AGENT,
    timeout: int = DEFAULT_TIMEOUT,
) -> RobotsResult:
    """
    Prüft eine Domain gegen die in CLAUDE.md definierten Klasse-A- und -B-Bots.
    Holt robots.txt übers Netz und delegiert die Auswertung an
    evaluate_robots_text(). Interpretiert nichts — nur Fakten.
    """
    # Domain saeubern: Schema und trailing slash weg
    dom = domain.strip()
    if dom.startswith("https://"):
        dom = dom[8:]
    elif dom.startswith("http://"):
        dom = dom[7:]
    dom = dom.strip("/")

    final_url, text, status = _fetch_robots(dom, user_agent=user_agent, timeout=timeout)

    # Netzwerk-Fehler oder 5xx -> UNBEKANNT (Grundregel Nr. 1)
    if final_url is None:
        result = RobotsResult(domain=dom)
        result.fetch_error = (
            "robots.txt nicht abrufbar (Timeout/DNS/Connection-Fehler"
            + (f", letzter Status {status}" if status else "")
            + ")"
        )
        result.overall_status = "UNBEKANNT"
        result.reason = "robots.txt konnte nicht geladen werden"
        return result

    return evaluate_robots_text(text or "", status or 200, dom, final_url)


# -----------------------------------------------------------------------------
# 6. Menschenlesbarer Ausdruck (für CLI und Tiefenaudit-Report)
# -----------------------------------------------------------------------------

def format_report(res: RobotsResult) -> str:
    """Gibt ein RobotsResult als lesbaren Text-Block zurück."""
    lines: list[str] = []
    lines.append(f"Domain: {res.domain}")
    if res.fetched_url:
        lines.append(f"robots.txt: {res.fetched_url}  (HTTP {res.fetched_status})")
    if res.fetch_error:
        lines.append(f"Fehler: {res.fetch_error}")
    lines.append(f"Ampel: {res.overall_status}  —  {res.reason}")
    if res.global_block:
        lines.append(f"! Global-Block: {res.global_block_evidence}")
    lines.append("")
    lines.append("Klasse A (sichtbarkeitskritisch für KI-Suche):")
    for b in res.bots:
        if b.klasse == "A":
            mark = "OK   " if b.allowed else "BLOCK"
            lines.append(f"  [{mark}] {b.name}: {b.beleg}")
    lines.append("")
    lines.append("Klasse B (Trainingsbots):")
    for b in res.bots:
        if b.klasse == "B":
            mark = "OK   " if b.allowed else "BLOCK"
            lines.append(f"  [{mark}] {b.name}: {b.beleg}")
    return "\n".join(lines)


# -----------------------------------------------------------------------------
# CLI
# -----------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    argv = argv if argv is not None else sys.argv[1:]
    if not argv:
        print("Nutzung: python src/signal1_robots.py <domain>")
        print("Beispiel: python src/signal1_robots.py hotel-example.at")
        return 2
    domain = argv[0]
    res = check_robots(domain)
    print(format_report(res))
    return 0


if __name__ == "__main__":
    sys.exit(main())
