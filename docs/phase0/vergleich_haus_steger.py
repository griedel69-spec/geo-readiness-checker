"""
Diagnose-Skript (Phase 0.5): Regex-Checker vs. GEO-Radar-Signale 1-3.

Vergleicht die 18 Regex-Checkpunkte aus geo_checker_app.py mit den
Signal-Modulen 1-3 aus dem geo-radar-Repo — gegen dieselbe Live-Domain.
Reine Diagnose: veraendert nichts, kostet nichts (keine Claude/Places-API).

Voraussetzungen auf dem Notebook:
    pip install requests beautifulsoup4 lxml
    # geo-radar liegt als Schwester-Ordner neben geo-readiness-checker,
    # sonst Pfad per --radar oder Umgebungsvariable GEO_RADAR_SRC angeben.

Nutzung:
    python docs/phase0/vergleich_haus_steger.py                       # haus-steger.at
    python docs/phase0/vergleich_haus_steger.py --domain hotel-x.at
    python docs/phase0/vergleich_haus_steger.py --radar C:/pfad/zu/geo-radar/src

Die Funktionen check_website/build_checks werden per AST aus
geo_checker_app.py extrahiert — Streamlit wird dafuer NICHT gestartet.
"""
import argparse
import ast
import json
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve()
CHECKER_ROOT = HERE.parents[2]          # .../geo-readiness-checker
CHECKER_APP = CHECKER_ROOT / "geo_checker_app.py"
DEFAULT_RADAR_SRC = CHECKER_ROOT.parent / "geo-radar" / "src"


def lade_regex_checker():
    """Extrahiert check_website + build_checks ohne Streamlit-Import."""
    tree = ast.parse(CHECKER_APP.read_text(encoding="utf-8"))
    wanted = {"check_website", "build_checks"}
    nodes = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name in wanted]
    assert {n.name for n in nodes} == wanted, "Funktionen in geo_checker_app.py nicht gefunden"
    ns = {}
    exec("import re, time, urllib.request\nfrom urllib.parse import urlparse\nMAX_SCORE = 36", ns)
    for n in nodes:
        exec(ast.unparse(n), ns)
    return ns["check_website"], ns["build_checks"]


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--domain", default="haus-steger.at")
    p.add_argument("--url", default=None, help="Start-URL fuer den Regex-Checker (Standard: https://www.<domain>)")
    p.add_argument("--radar", default=os.environ.get("GEO_RADAR_SRC", str(DEFAULT_RADAR_SRC)),
                   help="Pfad zum geo-radar src-Ordner")
    args = p.parse_args()

    radar_src = Path(args.radar)
    if not (radar_src / "signal1_robots.py").exists():
        print(f"FEHLER: geo-radar nicht gefunden unter {radar_src} — Pfad per --radar angeben.", file=sys.stderr)
        return 1

    url = args.url or f"https://www.{args.domain}"

    # ── 1. Regex-Checker ──
    check_website, build_checks = lade_regex_checker()
    facts = check_website(url)
    checks = build_checks(facts)
    regex_result = {
        "url": url,
        "score": sum(2 for c in checks if c["ok"]),
        "max": 36,
        "checks": [
            {"name": c["name"], "ok": c["ok"], "detail": c["detail"], "category": c["category"]}
            for c in checks
        ],
        "facts_auszug": {
            "jsonld_types": facts.get("jsonld_types"),
            "blocked_bots": [b["bot"] for b in facts.get("blocked_bots", [])],
            "word_count": facts.get("word_count"),
            "load_time": facts.get("load_time"),
        },
    }

    # ── 2. GEO-Radar Signale 1-3 ──
    sys.path.insert(0, str(radar_src))
    from signal1_robots import check_robots
    from signal2_schema import check_schema
    from signal3_rendering import check_rendering

    s1 = check_robots(args.domain)
    s2 = check_schema(args.domain)
    s3 = check_rendering(args.domain)

    radar_result = {
        "signal1": {
            "status": s1.overall_status,
            "reason": s1.reason,
            "global_block": s1.global_block,
            "bots": [
                {"name": b.name, "klasse": b.klasse, "allowed": b.allowed, "beleg": b.beleg}
                for b in s1.bots
            ],
        },
        "signal2": {
            "status": s2.overall_status,
            "reason": s2.reason,
            "n_blocks": s2.n_blocks,
            "n_parsed": s2.n_parsed,
            "n_invalid": s2.n_invalid,
            "all_types": s2.all_types,
            "has_faqpage": s2.has_faqpage,
            "lodging": (
                {
                    "type": s2.lodging.type_name,
                    "fields": [
                        {"name": f.name, "present": f.present, "evidence": f.evidence}
                        for f in s2.lodging.fields
                    ],
                    "empfohlen": [
                        {"name": f.name, "present": f.present} for f in s2.lodging.empfohlen
                    ],
                    "sameAs_count": s2.lodging.sameAs_count,
                }
                if s2.lodging
                else None
            ),
        },
        "signal3": {
            "status": s3.overall_status,
            "reason": s3.reason,
            "visible_text_length": s3.visible_text_length,
            "is_spa_suspect": s3.is_spa_suspect,
            "spa_markers": s3.spa_markers_found,
            "has_address": s3.has_address,
            "address_evidence": s3.address_evidence,
            "has_phone": s3.has_phone,
            "phone_evidence": s3.phone_evidence,
        },
    }

    print(json.dumps({"regex_checker": regex_result, "geo_radar": radar_result},
                     ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
