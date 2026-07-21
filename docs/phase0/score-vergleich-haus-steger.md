# Score-Vergleich: Regex-Checker vs. GEO-Radar-Signalmodule
**Betrieb:** haus-steger.at · **Datum:** 21.07.2026 · **Status:** Diagnose, keine Code-Änderung

---

## 0. Kosten

**0,00 USD.** Signale 1–3 sind reine HTTP-Prüfungen (requests/BeautifulSoup), der Regex-Checker ebenso. Kein Claude-Aufruf, keine Places-API. Das Cap von 2 USD wurde nicht angetastet.

---

## 1. Wichtige Einschränkung: Live-Abruf aus dieser Umgebung nicht möglich

Die Cloud-Umgebung dieser Session hat eine **Netzwerk-Allowlist** — erlaubt sind nur eingetragene Hosts (GitHub, PyPI usw.). Der Abruf von `haus-steger.at` wurde vom Gateway mit 403 abgelehnt („Host not in allowlist"), ebenso Ausweichquellen (web.archive.org). Der Zapier-Weg wurde von dir abgelehnt.

**Folge:** Der 1:1-Live-Lauf beider Engines gegen die echte Website steht noch aus. Das Vergleichsskript ist fertig und liegt bereit (`vergleich_haus_steger.py` im Scratchpad). Um es scharf laufen zu lassen: in den Einstellungen der Claude-Code-Umgebung unter **Network egress** die Hosts `haus-steger.at` und `www.haus-steger.at` freigeben, dann „Vergleich erneut ausführen" sagen.

Die Kernfrage (Schema-Typ-Bewertung) ließ sich trotzdem **deterministisch** beantworten — siehe Abschnitt 2. Grundlage: die von dir gelieferten Live-Werte des Render-Checkers (30/36, JSON-LD-Typen WebPage, ReadAction, BreadcrumbList, ListItem, WebSite).

---

## 2. Kernbefund: Schema.org/JSON-LD — dein Verdacht bestätigt

Ich habe Signal 2 (`evaluate_html`) mit einem HTML gefüttert, das exakt die vom Live-Checker gemeldeten JSON-LD-Typen enthält (typischer WordPress/Yoast-Graph). Ergebnis:

| | Regex-Checker | Signal 2 (geo-radar) |
|---|---|---|
| Prüfung | „gibt es irgendeinen JSON-LD-Block?" | „gibt es eine **Lodging-Entität** (Hotel/BedAndBreakfast/LodgingBusiness/…) mit Kernfeldern?" |
| Ergebnis | ✅ bestanden (2 Punkte) | **ROT** |
| Begründung | 1+ Block gefunden, Typen werden nur angezeigt, nie bewertet | *„keine Lodging-Entität (Hotel/Resort/BedAndBreakfast/Hostel/LodgingBusiness/Apartment/VacationRental). Gefunden: WebPage, ReadAction, BreadcrumbList, ListItem, WebSite"* |

Dasselbe gilt für den zweiten Checkpunkt „Schema.org Markup": Der Regex-Checker prüft nur, ob die Zeichenkette „schema.org" im HTML vorkommt — die kommt in jedem WordPress-Yoast-Graph vor. Beide Struktur-Checkpunkte sind für haus-steger.at also **falsch-positiv**: Der Betrieb bekommt 4 von 36 Punkten für strukturierte Daten, die einer KI nichts über die Unterkunft sagen.

Zusätzlich prüft Signal 2, was dem Checker komplett fehlt: Kernfelder (Name, Adresse, Geo, Telefon, URL, Bild), **FAQPage** (die Erkennung aus PR #36 sitzt hier: `has_faqpage`), `sameAs`-Verknüpfungen, und kaputtes JSON wird ehrlich als „vorhanden, aber defekt" = UNBEKANNT ausgewiesen statt gewertet.

---

## 3. Nebenbefund (unbeabsichtigt, aber aufschlussreich): Verhalten bei Abruf-Fehler

Beim blockierten Abruf lieferten beide Engines trotzdem ein Ergebnis — und die Differenz ist das beste Argument für die Ampel-Logik:

| Engine | Ergebnis bei nicht erreichbarer Website |
|---|---|
| Regex-Checker | **8/36 Punkte (22 %)** — vier Checkpunkte „bestanden": HTTPS ✅, Indexierbarkeit ✅ (kein noindex im leeren HTML), robots.txt-Bots ✅ („alle erlaubt", weil keine robots.txt lesbar), Alt-Texte ✅ („keine Bilder gefunden" = 100 %) |
| Signal 1–3 | dreimal **UNBEKANNT** mit Klartext-Grund („robots.txt konnte nicht geladen werden" / „HTML konnte nicht geladen werden") |

Der Checker kennt kein „nicht messbar" — was nicht abrufbar ist, wird teils als bestanden, teils als durchgefallen gewertet. Ein Betrieb mit kurzzeitig zickigem Server bekäme einen realen (falschen) Score samt Handlungsempfehlungen.

---

## 4. Gegenüberstellung der 18 Checkpunkte

Legende: **Live** = Wert aus deinem Render-Lauf (nur Gesamtscore und JSON-LD-Detail bekannt); *n. e.* = im Live-Report nicht einzeln überliefert, Klärung im Live-Lauf nach Netzfreigabe.

| # | Checkpunkt (Regex-Checker) | Regex-Ergebnis (Live) | Signalmodul-Pendant | Erwartetes Signal-Ergebnis | Abweichung |
|---|---|---|---|---|---|
| 1 | HTTPS | *n. e.* | — (implizit beim Fetch) | — | nein |
| 2 | Ladezeit < 3 s | *n. e.* | **kein Pendant** in Signal 1–3 | — | — |
| 3 | Viewport-Tag | *n. e.* | kein Pendant | — | — |
| 4 | Indexierbarkeit (Meta Robots) | *n. e.* | kein direktes Pendant | — | — |
| 5 | robots.txt — KI-Bots | *n. e.* | **Signal 1** | GRÜN/GELB/ROT je nach Bot-**Klasse** (13 Bots: 8 sichtbarkeitskritische Klasse A → ROT, 5 Trainings-Bots Klasse B → nur GELB); 401/403 → UNBEKANNT statt „alles erlaubt" | möglich* |
| 6 | sitemap.xml | *n. e.* | kein Pendant in Signal 1–3 | — | — |
| 7 | Canonical | *n. e.* | kein Pendant | — | — |
| 8 | Interne Links ≥ 3 | *n. e.* | kein Pendant | — | — |
| 9 | Meta-Description | *n. e.* | kein Pendant (Produktions-Baustein) | — | — |
| 10 | Page Title | *n. e.* | kein Pendant | — | — |
| 11 | H1 | *n. e.* | kein Pendant (Produktions-Baustein) | — | — |
| 12 | Textinhalt ≥ 300 Wörter | *n. e.* | **Signal 3** (sichtbare Zeichen: < 300 kritisch, < 1000 dünn; plus SPA-Marker; plus hartes Kriterium Adresse+Telefon im Roh-HTML) | offen | möglich* |
| 13 | Schema.org Markup | ✅ bestanden | **Signal 2** | **ROT** (String-Match ≠ Lodging-Entität) | **JA — belegt** |
| 14 | JSON-LD Structured Data | ✅ bestanden (WebPage, ReadAction, BreadcrumbList, ListItem, WebSite) | **Signal 2** | **ROT** (deterministisch nachgestellt, Abschnitt 2) | **JA — belegt** |
| 15 | Open Graph Tags | *n. e.* | kein Pendant | — | — |
| 16 | lang-Attribut | *n. e.* | kein Pendant | — | — |
| 17 | Hreflang | *n. e.* | kein Pendant | — | — |
| 18 | Alt-Texte ≥ 80 % | *n. e.* | kein Pendant („keine Bilder = bestanden"-Logik bleibt ein Checker-Problem) | — | — |

\* „möglich" = die Prüftiefe unterscheidet sich so stark, dass ein anderes Ergebnis plausibel ist; entscheidbar erst im Live-Lauf.

**Prüfpunkte der Signalmodule, die im Regex-Checker komplett fehlen:**

- **FAQPage-Erkennung** (Signal 2, `has_faqpage` — PR #36; ohne FAQPage höchstens GELB)
- Kernfelder der Lodging-Entität: Name, Adresse, Geo-Koordinaten, Telefon, URL, Bild
- `sameAs`-Verknüpfungen (Google Business, Socials — Entitäten-Verankerung)
- Adresse **und** Telefon im rohen HTML (Signal 3, hartes GELB-Kriterium)
- SPA-/JavaScript-Framework-Erkennung („Seite ist für Crawler leer") (Signal 3)
- Bot-Klassen A/B mit Beleg-Zeile aus der robots.txt (Signal 1: 13 Bots statt 5; u. a. fehlen im Checker OAI-SearchBot, ChatGPT-User, Claude-User, Bingbot, CCBot)
- Der Status **UNBEKANNT** als ehrliche vierte Kategorie

---

## 5. Antwort auf Frage 2c und geschätzter Score

**Wie viele der 18 Checkpunkte kippen?**
- **Sicher belegt: 2** (Nr. 13 Schema.org und Nr. 14 JSON-LD: bestanden → ROT/durchgefallen).
- Weitere Kandidaten (Nr. 5 robots.txt-Tiefe, Nr. 12 Text/SPA/Kontakt): erst nach Netzfreigabe entscheidbar.
- Nur 4 der 18 Checkpunkte haben überhaupt ein Signal-Pendant — die übrigen 14 misst der geo-radar bewusst nicht (bzw. erst in der Produktions-Stufe).

**Grobe Neuberechnung (Punktesystem des Checkers beibehalten, nur Signal-Logik eingesetzt):**

| | Score | Anzeige |
|---|---|---|
| Heute (Regex) | **30/36** | 83 % — „Sehr gute GEO- & KI-Basis" 🟢 |
| Mit Signal-Logik, konservativ (nur die 2 belegten Kipper) | **26/36** | 72 % — eine Stufe tiefer |
| Realistisch nach Live-Lauf | eher darunter | offen |

Die Punktzahl unterschätzt den Effekt aber: In der geplanten **Ampel-Logik** wäre Signal 2 für diesen Betrieb schlicht **ROT** — und genau das ist die Verkaufs-Brücke: „Ihre Website hat strukturierte Daten, aber sie beschreiben nur die Navigation, nicht Ihren Betrieb. Eine KI erfährt daraus weder Adresse noch Zimmer noch Kategorie." Der heutige 83-%-Score erzählt einem Beherbergungsbetrieb das Gegenteil und nimmt der Verkaufs-Brücke das Argument.

---

## 6. Nächster Schritt für den vollständigen Live-Vergleich

1. In den Umgebungseinstellungen (Claude Code → Environment → Network egress): `haus-steger.at` und `www.haus-steger.at` freigeben.
2. Kurz Bescheid geben — das fertige Skript läuft dann in <1 Minute und füllt die *n. e.*-Zellen der Tabelle mit echten Werten (weiterhin 0 USD).

*Kein Repo verändert, kein Branch, kein Commit, kein Push. Alle Artefakte liegen im Session-Scratchpad.*
