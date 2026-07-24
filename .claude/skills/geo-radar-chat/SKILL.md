---
name: geo-radar-chat
description: GEO-Radar Sichtbarkeitsprüfung direkt im Claude.ai-Chat, ohne CLI/Python — für Gernot Riedel Tourism Consulting. Zwei Einsatzfälle — Einzelbetrieb-Diagnose (Ampel GRÜN/GELB/ROT/UNBEKANNT für ein Hotel/eine Pension) inkl. optionaler bezahlter Produktionsstufe (8 fertige GEO-Bausteine), und Regionsanalyse/Destinations-Türöffner für TVBs/DMOs (alle Mitgliedsbetriebe einer Kategorie in einem Lauf, Destinations-Ranking + Zusammenfassung). Benutze diesen Skill, wenn im Chat ein Hotel/Betrieb auf GEO-Sichtbarkeit geprüft werden soll, wenn ein GEO-Optimierungspaket für einen Betrieb erzeugt werden soll, oder wenn eine ganze Destination/ein TVB-Mitgliederverzeichnis gescreent werden soll.
---

# GEO-Radar — Chat-Skill (Einzelbetrieb + Regionsanalyse)

## 0. Was dieser Skill ist — und was nicht

Dies ist der **Nachbau der geo-radar-CLI-Logik für den reinen Claude.ai-Chat** (kein Python, kein Terminal, keine lokale Installation). Er existiert, weil die eigentliche Betriebsanalyse heute im geo-radar-Ordner per "Neuer Kunde"-Button läuft und dort exakt bleibt — dieser Skill ist für die Fälle gedacht, in denen Gernot **nur den Chat** zur Hand hat: unterwegs, bei einem TVB-Gespräch, ohne Rechner mit der geo-radar-Installation.

**Quelle und Stand:** Jede Regel unten (Bot-Listen, Schwellenwerte, Entscheidungsbäume, Baustein-Prompts, Kostenkonstanten) ist wortgetreu aus dem geo-radar-Quellcode übernommen, Repo `griedel69-spec/geo-radar`, Commit `c6546a3839829776ccbfc3b24d384057e4ad1817`, Module `src/signal1_robots.py`, `src/signal2_schema.py`, `src/signal3_rendering.py`, `src/scanner.py`, `src/report.py`, `src/production.py`. Nichts davon ist aus dem Gedächtnis oder angenähert formuliert. Wenn geo-radar sich weiterentwickelt, kann dieser Skill veralten — im Zweifel gilt der Code im geo-radar-Repo, nicht dieser Text.

**Zwei eingebaute Grenzen, ehrlich benannt:**

1. **Kein echtes Browser-Rendering.** Weder geo-radar's Batch-Scanner noch dieser Skill führen JavaScript aus — beide lesen nur das rohe HTML per HTTP-Abruf. Das ist also **kein** Nachteil gegenüber der Batch-Nutzung (`scanner.py`), aber ein bewusster Unterschied zur separaten, noch nicht gebauten Playwright-Tiefenaudit-Variante von geo-radar. Signal 3 unten ist entsprechend die HTTP-Batch-Logik, nicht mehr und nicht weniger.
2. **Web-Zugriff im Chat.** Dieser Skill braucht die Fähigkeit, robots.txt und die Startseite einer Domain per HTTP abzurufen. Wenn diese Fähigkeit in der aktuellen Chat-Umgebung fehlt oder ein Abruf fehlschlägt: **UNBEKANNT melden, nicht raten.** Kein Ausweichen auf Trainingswissen über die Domain — das wäre exakt die Halluzination, die dieses ganze System verhindern soll.

**Kernregel, die über allem steht (Null Halluzination):** Jede Aussage über einen Betrieb muss aus tatsächlich abgerufenem Text stammen. Ist etwas nicht belegbar: `UNBEKANNT` (bei einer Ampel) oder der Marker `[bitte prüfen und ergänzen]` bzw. `[<konkret> bitte prüfen und ergänzen]` (in einem Baustein-Text) — niemals eine plausibel klingende Lücke selbst füllen, auch nicht mit Wissen über ähnliche oder namensgleiche Betriebe.

---

## 1. Einzelbetrieb — kostenlose Diagnose (Stufe 1: Befund)

Ablauf für **einen** Betrieb (Domain, z. B. `hotel-example.at`):

### Schritt A — Signal 1: KI-Crawler-Zugang (robots.txt)

**Frage:** Sperrt die Website KI-Systeme aus, bevor sie Inhalte lesen können?

1. `https://<domain>/robots.txt` abrufen (Redirects folgen). Schlägt https fehl, `http://` versuchen.
2. **Fetch-Ergebnis einordnen — exakt diese Regeln:**
   - HTTP 200 mit Inhalt → weiter zu Schritt 3.
   - HTTP 404 oder 410 → "robots.txt nicht vorhanden — laut Standard alles erlaubt" → **GRÜN**, fertig.
   - HTTP 200 mit leerem Body → "vorhanden, aber leer — laut Standard alles erlaubt" → **GRÜN**, fertig.
   - Jeder andere Status (401, 403, sonstige 4xx, 5xx) oder Netzwerkfehler/Timeout → **UNBEKANNT** ("robots.txt-Zugriff verweigert" bzw. "nicht abrufbar"), fertig. *(Wichtig: 401/403 heißt NICHT "gesperrt" — das wäre schon eine Interpretation ohne sicheren Beleg.)*
3. **robots.txt in User-agent-Gruppen zerlegen** (robots.txt-Standard): aufeinanderfolgende `User-agent:`-Zeilen gehören zusammen; sobald nach den Agents mindestens eine `Allow:`/`Disallow:`-Regel folgte, startet der nächste `User-agent:` eine neue Gruppe. Kommentare (ab `#`) ignorieren.
4. **Bot-Listen — exakt diese, in dieser Reihenfolge:**

   Klasse A (sichtbarkeitskritisch, Retrieval/Suche):
   `OAI-SearchBot, ChatGPT-User, PerplexityBot, Perplexity-User, Claude-User, Claude-SearchBot, Google-Extended, Bingbot`

   Klasse B (Trainingsbots, langsamere Wirkung):
   `GPTBot, ClaudeBot, CCBot, Applebot-Extended, Bytespider`

5. **Pro Bot prüfen, ob `/` erlaubt ist** (case-insensitiver Namensabgleich der Gruppen):
   - Eigene Gruppe für den Bot gefunden → deren Regeln gelten.
   - Keine eigene Gruppe, aber eine `User-agent: *`-Gruppe vorhanden → deren Regeln gelten.
   - Weder eigene noch `*`-Gruppe → implizit erlaubt.
   - Innerhalb einer Gruppe für die Wurzel `/`: `Disallow: /` sperrt; ein `Allow: /` in derselben Gruppe hebt das wieder auf; `Disallow:` (leerer Wert) heißt ausdrücklich "nichts gesperrt"; ohne diese Zeilen gilt: nicht gesperrt.
   - Zusätzlich: Wenn die `*`-Gruppe selbst `/` sperrt → **globaler Block**, das zieht unabhängig vom Einzel-Bot-Status.
6. **Ampel:**
   - **ROT**, wenn globaler Block vorliegt ODER mindestens ein Klasse-A-Bot gesperrt ist.
   - **GELB**, wenn (kein ROT-Grund, aber) mindestens ein Klasse-B-Bot gesperrt ist.
   - **GRÜN**, wenn alle relevanten Bots erlaubt sind.
   - Beleg immer als Klartext mitliefern (z. B. `User-agent: GPTBot -> Disallow: /` oder "kein eigener Eintrag; User-agent: * -> kein 'Disallow: /' in dieser Gruppe").

### Schritt B — Signal 2: Strukturierte Daten (Schema.org JSON-LD)

**Frage:** Kann eine KI die Fakten des Hauses als strukturierte Entität lesen?

1. Startseite (`https://<domain>/`, Redirects folgen, http-Fallback) abrufen. Nicht-2xx oder Fehler → **UNBEKANNT**.
2. Alle `<script type="application/ld+json">`-Blöcke extrahieren und einzeln als JSON parsen (auch verschachtelt: `@graph`-Arrays, eingebettete Entitäten in Properties wie `WebPage.mainEntity`).
3. **Entscheidungsbaum, in dieser Reihenfolge:**
   - **0 JSON-LD-Blöcke gefunden** → **ROT**, "kein JSON-LD-Markup auf der Seite gefunden".
   - **Blöcke vorhanden, aber alle unparsbar** (kaputtes JSON) → **UNBEKANNT**, "vorhanden, aber technisch defekt" (Ehrlichkeitsregel: nicht als ROT werten, es könnte ja korrekt gemeint sein).
   - Sonst: alle `@type`-Werte sammeln. Gültige Lodging-Typen (**exakt diese Menge**): `Hotel, Resort, BedAndBreakfast, Hostel, LodgingBusiness, Apartment, VacationRental`. Findet sich **keine** Entität mit einem dieser Typen → **ROT**, "keine Lodging-Entität … Gefunden: <tatsächlich gefundene Typen>" (z. B. nur `WebSite`, `Organization`, `LocalBusiness` zählen nicht als Lodging).
   - Lodging-Entität gefunden (bei mehreren: die mit den meisten belegten Kernfeldern) → Kernfelder prüfen: **`name, address, geo, telephone, url, image`**. Details:
     - `address` zählt nur, wenn strukturiert als `PostalAddress` mit mindestens Straße, PLZ oder Ort — Fließtext-Adresse zählt nicht.
     - `geo` zählt nur mit numerisch gültigem `latitude` UND `longitude`.
     - `image` zählt als String, Liste von Strings/ImageObjects oder einzelnes ImageObject mit `url`/`contentUrl`.
   - Zusätzlich prüfen: **FAQPage** irgendwo im JSON-LD vorhanden? **sameAs** (Social-Media-Links) auf der Lodging-Entität vorhanden?
   - **GRÜN**, nur wenn: alle 6 Kernfelder vorhanden UND FAQPage vorhanden UND sameAs vorhanden.
   - Sonst **GELB**, mit genauer Lückenliste ("Kernfelder fehlen: …", "keine FAQPage", "kein sameAs").
   - Empfohlene, aber nicht blockierende Zusatzfelder (nur informativ, kein Einfluss auf die Ampel): `priceRange, amenityFeature, checkinTime, checkoutTime`.

### Schritt C — Signal 3: Maschinenlesbarkeit / Rendering (HTTP-Batch-Variante)

**Frage:** Stehen Zimmer, Lage, Preise, Kontakt im ausgelieferten HTML oder erst nach JavaScript?

1. Gleiche Startseite wie Schritt B verwenden (kein zweiter Abruf nötig). Nicht-2xx/Fehler → **UNBEKANNT**.
2. **Sichtbaren Text extrahieren**: `<script>`, `<style>`, `<noscript>`, `<template>` und HTML-Kommentare entfernen — **`<nav>`, `<header>`, `<footer>` bleiben** (dort steht oft der Kontakt). Textlänge zählen.
3. **Framework-Marker suchen** (Indiz für SPA, kein Alleinkriterium): `id="root"` (React/Vite), `id="app"` (Vue/Nuxt), `id="__next"` (Next.js), `id="__nuxt"` (Nuxt), `data-reactroot`, `ng-version=` (Angular), `ng-app=` (AngularJS), `data-v-` -Attribute (Vue).
4. **Kontakt im rohen HTML suchen:**
   - Telefon: internationales Muster (`+43 …` / `0043 …`) oder inländische Vorwahl (`0512 …`).
   - Adresse: entweder Straße+Hausnummer-Muster (endet auf straße/strasse/str./weg/gasse/platz/allee/ring/ufer + Zahl) oder PLZ+Ort-Muster (4-5-stellige Zahl, gefolgt von großgeschriebenem Ortsnamen).
5. **Schwellenwerte (exakt):** `TEXT_MIN_SUBSTANZ = 1000` Zeichen, `TEXT_KRITISCH = 300` Zeichen, `SPA_MARKER_TEXT_LIMIT = 1000` Zeichen. SPA-Verdacht = Framework-Marker gefunden UND sichtbarer Text < 1000 Zeichen.
6. **Entscheidungsbaum, in dieser Reihenfolge (erste zutreffende Regel gewinnt):**
   1. SPA-Verdacht UND Text < 300 Zeichen UND weder Adresse noch Telefon gefunden → **ROT**.
   2. **Hartes Kriterium:** Adresse ODER Telefon fehlt im rohen HTML → **GELB** (unabhängig von der Textlänge).
   3. SPA-Verdacht (Marker + <1000 Zeichen), aber Kontakt vorhanden → **GELB**, "Tiefenaudit mit Render-Vergleich empfohlen".
   4. Text < 300 Zeichen (auch ohne Marker) → **GELB**.
   5. Text < 1000 Zeichen → **GELB**, "dünner Body".
   6. Sonst (≥1000 sichtbare Zeichen, Adresse und Telefon vorhanden, kein SPA-Verdacht) → **GRÜN**.

### Schritt D — Gesamt-Ampel für den Betrieb

Exakte Regel (`compute_overall`):
- **ROT**, wenn mindestens eines der drei Signale ROT ist.
- Sonst **GELB**, wenn mindestens eines GELB **oder** UNBEKANNT ist. *(UNBEKANNT zählt NICHT als GRÜN — "wir wissen es nicht" ist kein Freibrief.)*
- **GRÜN**, nur wenn alle drei Signale GRÜN sind.

### Ausgabeformat Kurzbefund (Einzelbetrieb)

```
GEO-Radar Kurzbefund — <Hausname>, <Ort>
Domain: <domain>
Datum: <Datum>

GESAMT-AMPEL: <GRÜN/GELB/ROT/UNBEKANNT>

Signal 1 — KI-Crawler-Zugang (robots.txt): <Ampel>
  Beleg: <Kurzbegründung>

Signal 2 — Strukturierte Daten (Schema.org): <Ampel>
  Beleg: <Kurzbegründung>

Signal 3 — Maschinenlesbarkeit (Rendering): <Ampel>
  Beleg: <Kurzbegründung>

Top-Handlungsempfehlungen:
1. ...
2. ...
3. ...
```

Handlungsempfehlungen leiten sich direkt aus den ROT/GELB-Belegen ab (z. B. "robots.txt für OAI-SearchBot öffnen", "JSON-LD als Hotel-Entität ergänzen"). Keine Empfehlung ohne zugehörigen Befund.

---

## 2. Einzelbetrieb — Produktionsstufe (Stufe 2: 8 fertige Bausteine, bezahlt)

**Auftrags-Gate (analog zu `production.py --auftrag`):** Diese Stufe nur nach ausdrücklichem Auftrag starten — entweder weil der Betrieb bezahlt hat, oder weil Gernot im Chat explizit sagt "Bausteine erzeugen" / "Produktionsstufe" / nennt eine Auftragsnummer. Ohne diesen Trigger nur die kostenlose Diagnose aus Abschnitt 1 liefern und auf die kostenpflichtige Stufe hinweisen.

**Kostenrahmen, chat-adaptiert:** Im echten `production.py` gilt hart `MAX_KOSTEN_PRO_LAUF_USD = 10.00` und `MAX_KOSTEN_PRO_HAUS_USD = 2.00` (API-Kosten pro Claude-Aufruf, unabhängig geprüft vor jedem Aufruf). Im Chat gibt es keine vergleichbare Token-Abrechnung pro Haus — das technische Limit entfällt. Der **Geist** der Regel bleibt: vor einem Lauf mit mehreren Häusern kurz den Umfang nennen ("X Häuser × 8 Bausteine, das wird ein langer Lauf") und bei sehr großen Stückzahlen (Richtwert: mehr als ~5 Häuser in einem Chat-Lauf) empfehlen, stattdessen die geo-radar-CLI (`production.py --from-csv … --all`) zu nutzen, die für Batches gebaut ist und die echten Kostenlimits technisch durchsetzt.

### 2.1 Website-Fakten sammeln

Startseite plus themenrelevante Unterseiten abrufen (analog `CRAWL_PFADE`, Richtwert 8-12 Seiten, je nachdem was tatsächlich existiert):

`/`, Kontakt/Anreise (`/kontakt`, `/anreise`, `/anfahrt`, `/contact`), Über uns/Team (`/über-uns`, `/about`, `/team`), Zimmer (`/zimmer`, `/rooms`, `/suiten`, `/apartments`), Info/FAQ (`/info`, `/hausinformation`, `/faq`, `/haeufige-fragen`), Buchung/AGB/Preise (`/buchen`, `/agb`, `/preise`, `/angebote`), Kulinarik/WLAN (`/fruehstueck`, `/restaurant`, `/wlan`), Wellness (`/wellness`, `/spa`), Impressum (`/impressum`).

Zusätzlich: Links auf der Startseite mit Ankertext/href, der eines dieser Schlagworte enthält, ebenfalls aufnehmen: `info, faq, häufige fragen, agb, storno, buchen, reservier, zimmer, suite, apartment, kontakt, anreise, anfahrt, fruehstueck, kulinarik, wlan, wellness, spa, check-in, check-out, haustier, familie, kinder, über uns, preis, angebote, pauschale`.

### 2.2 Fakten extrahieren — mit Anker-Pflicht

Aus den gecrawlten Seiten ein Fakten-Objekt ziehen (Name, Adresse, Telefon, E-Mail, Betriebstyp, Sterne, Zimmerzahl, Zimmertypen, Ausstattung, USPs, Lagebeschreibung, Check-in/out-Zeiten, Koordinaten, Sprachen, Haustiere ja/nein, familienfreundlich ja/nein, Wellness, Aktivitäten, Social-Media-Profile).

**Regel:** *ausschließlich* was wörtlich im gecrawlten Text steht — kein Trainingswissen, auch nicht über namensgleiche oder ähnliche Betriebe (reale Story dazu: zwei verschiedene Häuser "Steger's" in Zell am See und "Gästehaus Steger" in Kaprun wurden einmal verwechselt — seither gilt: **jeder** extrahierte Fakt muss sich zusätzlich in einer zweiten, unabhängigen Prüfung im Text wiederfinden, bevor er als belegt gilt** ("Fakten-Verankerung"):

- Textfelder (Name, Adresse, E-Mail, Lagebeschreibung): tragende Wörter (>3 Zeichen, keine Stoppwörter) müssen im Crawl-Text vorkommen.
- Telefonnummer: die Ziffernfolge muss vorkommen (Formatierung wie `+43`/`0043`/`0…` darf abweichen).
- Check-in/out-Zeiten: `14:00` zählt auch als `14.00`, `14 Uhr`.
- Sterne: nur, wenn der Text überhaupt von "Stern(e)" oder `*` spricht UND die Zahl (als Ziffer oder Zahlwort) vorkommt.
- Zimmerzahl/Koordinaten: die Zahl muss als eigenständige Ziffernfolge im Text stehen (0 gilt als "nicht angegeben", kein Verwurf).
- "Haustiere: ja" / "familienfreundlich: ja" nur, wenn ein Themenwort dazu im Text steht (`haustier/hund/katze` bzw. `famili/kind`); "nein" behauptet nichts und wird nicht geprüft.

Was diese Prüfung nicht besteht: **verwerfen**, nicht raten — es läuft dann als unbelegt über den Marker-Pfad weiter (siehe 2.4).

### 2.3 Welche Bausteine erzeugt werden (`bausteine_aus_befund`)

Immer erzeugt (Teil des Pakets, unabhängig vom Befund): **H1+Subheadline, USP-Box, 20 Keywords, Google-Business-Text, 3 Meta-Descriptions, Über-uns-Text**.

Bedingt erzeugt, abhängig vom kostenlosen Befund aus Abschnitt 1:
- **Strukturierter Datensatz (Schema.org)**: nur wenn Signal 2 ROT war oder der Beleg auf fehlendes JSON-LD / fehlende Lodging-Entität / fehlendes `geo` / fehlendes `sameAs` hinweist.
- **FAQ**: nur wenn Signal-2-Beleg "keine FAQPage" enthielt.

Reihenfolge der Auslieferung: FAQ zuerst (klarster Nutzen für den Hotelier), dann Schema-Datensatz, dann die sechs Marketing-Bausteine.

### 2.4 Halluzinationsschutz beim Formulieren — die Marker-Regel

Marker: `[bitte prüfen und ergänzen]` (generisch) oder präzisiert `[<konkretes Thema> bitte prüfen und ergänzen]` (z. B. `[Preisspanne: bitte prüfen und ergänzen]`).

**Zwei feste Formulierungsregeln, an die sich jeder Baustein hält:**
1. **Teilinformationen sauber trennen:** Ist ein Sachverhalt teilweise belegt (z. B. "familienfreundlich" bestätigt, aber keine konkreten Kinderangebote), den belegten Teil als vollständigen Satz formulieren und den offenen Teil klar abgesetzt als eigene Klammer-Notiz danach setzen. Richtig: *"Ja, wir heißen Familien mit Kindern herzlich willkommen. [Spezielle Kinderangebote: bitte prüfen und ergänzen]"*. Falsch: *"Wir bieten unter anderem [bitte prüfen und ergänzen] für Kinder"* (Marker mitten im Satz vermengt).
2. **Nie mitten im Satz abbrechen:** Jeder Satz/jede Description muss vollständig sein und sauber auf Punkt, Frage-/Ausrufezeichen oder Marker enden. Passt ein vollständiger Satz nicht in ein Zeichenlimit (z. B. Meta-Description 155 Zeichen), den Satz kürzer formulieren — niemals abschneiden.

### 2.5 Zentrale Belegprüfung (Kontrolldurchlauf) — das eigentliche Hallucination-Gate

Nachdem alle Bausteine formuliert sind, läuft **ein gemeinsamer Kontroll-Durchgang gegen die Belegliste** (die Summe aller verankerten Fakten aus 2.2). Diese Prüfung selbst folgt exakt drei Kategorien:

- **Kategorie A — erlaubt, ohne Beleg, NICHT flaggen:** unstrittiges geografisches Einordnungswissen, das sich zwingend aus einem belegten Ort ableitet (z. B. "Salzburger Land", "Pinzgau", "in den Alpen" bei belegtem Ort "Zell am See"). Die Grenze ist eng: erlaubt ist nur die reine Einordnung (Ort → übergeordnete Einheit) — sobald daraus eine Eignung, Qualität oder ein Angebot abgeleitet wird ("ideal für Familien wegen der Lage"), ist das keine Kategorie A mehr.
- **Kategorie B — schmückende Zuschreibung ohne Beleg:** Atmosphäre-, Qualitäts- oder Zielgruppenurteile, die nicht in der Belegliste stehen ("ruhig", "idyllisch", "ideal für Familien"). → **streichen**.
- **Kategorie C — konkrete, nachprüfbare Faktenaussage ohne Beleg:** jede Zahl (Entfernungen, Anzahlen, Preise, Sterne), jeder benannte externe Kanal/jedes Produkt/jede Partnerschaft ohne Beleg, jedes Ausstattungs-/Leistungsmerkmal ohne Beleg. Innerhalb C: trägt der Satz auch ohne die Angabe → **streichen**; ist es eine strukturell erwartete, vom Kunden leicht nachtragbare Angabe (Zimmerzahl, Preisspanne, Check-in-Zeiten, Sterne) → **markieren** (Marker setzen statt streichen).
- Der Marker selbst (`[bitte prüfen und ergänzen]` in jeder Form) ist **keine** Halluzination und wird nie beanstandet.
- Dieselbe Aussage bekommt in **allen** Bausteinen, in denen sie vorkommt, dieselbe Behandlung — nicht in einem Baustein streichen und im anderen stehen lassen.

**Praktisch im Chat:** nach dem Formulieren aller Bausteine einmal bewusst gegen die Belegliste aus 2.2 gegenlesen, Kategorie-B/C-Funde konsequent streichen oder markieren, und diesen Schritt dem Nutzer kurz bestätigen (z. B. "Beleglauf: 2 unbelegte Zuschreibungen entfernt, 1 Angabe markiert").

### 2.6 Die 8 Bausteine — exakte Prompts/Anleitungen

Für jeden Baustein unten gilt: `prompt_auftrag` ist wortgetreu der Auftrag, nach dem der Text erzeugt wird; `einfuegen_anleitung` ist der Text für den Hotelier selbst; `agentur_briefing` ist der Text, falls stattdessen die Webagentur beauftragt wird; `pruef_checkliste` sind die Abnahmepunkte.

---

**1. FAQ mit 10 Fragen** — *Zehn typische Gäste-Fragen und Antworten, die KI-Systeme in Antworten wortwörtlich zitieren können.*

> Erzeuge eine FAQ-Sammlung mit genau 10 Fragen und Antworten in österreichischem Deutsch, Sie-Form.
>
> Themen (jeweils 1 Frage) abdecken: 1. Anreise/Parkplatz, 2. Check-in Zeit, 3. Check-out Zeit, 4. Frühstück/Verpflegung, 5. WLAN/Internet, 6. Haustiere, 7. Familien mit Kindern, 8. Wellness/Freizeit im Haus, 9. Stornierung/Buchung, 10. Regionale Aktivitäten (nur die in den Fakten genannten).
>
> Antworten in 1-3 Sätzen. Kein Marketing-Sprech. [Marker-Formulierungsregeln aus 2.4 gelten.]
>
> Format: `Frage 1: ...` / `Antwort 1: ...` … bis Frage 10.

Einfügen: eigene Seite "Häufige Fragen" anlegen, Text hineinkopieren (ohne Nummerierung), im Hauptmenü verlinken.
Agentur-Briefing: FAQ-Seite einrichten, zusätzlich den mitgelieferten JSON-LD-Codeblock (FAQPage-Schema) 1:1 in den `<head>` der Seite einbetten.
Checkliste: Seite über Hauptmenü erreichbar; JSON-LD im `<head>` eingebunden; Google Rich-Results-Test findet gültige FAQPage; keine Platzhalter mehr offen; keine Rechtschreib-/Formatfehler.

**FAQ-Erkennung vor der Erzeugung (Ergänzungsmodus statt Doppelgleisigkeit):** Bevor die volle 10er-FAQ erzeugt wird, in den gecrawlten Seiten nach einer Überschrift wie "Häufige Fragen"/"FAQ"/"Fragen und Antworten" suchen, gefolgt von mindestens 3 fragezeichen-endenden Sätzen im Text danach. Wird eine vorhandene FAQ-Sektion erkannt: **nur** die auf der Website noch fehlenden Standardthemen ergänzen, keine Wiederholung vorhandener Fragen, keine komplette Neuerzeugung. Themen-Abgleich (Stichwörter, umlauttolerant): Anreise/Parkplatz (`park, anreise, anfahrt`), Check-in (`check-in, checkin, einchecken`), Check-out (`check-out, checkout, auschecken`), Verpflegung (`fruehstueck, verpflegung, halbpension, vollpension`), WLAN (`wlan, wifi, internet`), Haustiere (`haustier, hund, katze`), Familien (`famili, kind`), Wellness (`wellness, spa, sauna, pool, schwimmbad, fitness`), Buchung/Storno (`storno, buchung, buchen, reservier`), Umgebung (`umgebung, ausflu, aktivitaet, ski, wandern, region`). Nur die Themen mit `0` Treffern werden neu erzeugt.

---

**2. Strukturierter Datensatz (digitaler Steckbrief)** — *Der maschinenlesbare Steckbrief des Hauses, mit dem KI-Systeme und Suchmaschinen es zuverlässig zuordnen.*

> Erzeuge einen strukturierten Datensatz (JSON-LD) für dieses Haus. Als `@type` ist AUSSCHLIESSLICH einer dieser gültigen Schema.org-Lodging-Typen erlaubt: `BedAndBreakfast, Campground, Hostel, Hotel, Motel, Resort, VacationRental, LodgingBusiness`. Deutsche Betriebsbezeichnungen sind KEINE gültigen Typen: eine Pension/Frühstückspension ist `BedAndBreakfast`, eine Ferienwohnung/ein Apartmenthaus ist `VacationRental`, ein Gasthof oder jeder unklare Fall ist `LodgingBusiness`.
>
> Vollständige Kernfelder: `name`, `address` (PostalAddress mit street, postalCode, addressLocality, addressCountry), `telephone`, `url`, `image`, `priceRange`, `geo` (GeoCoordinates), `amenityFeature`, `checkinTime`, `checkoutTime`, `starRating` (NUR wenn die Sterne-Kategorie in den Fakten steht: `{"@type": "Rating", "ratingValue": <Zahl>}`), `sameAs` (Social-Media-Profile, falls in Fakten genannt).
>
> Rückgabe: ausschließlich der JSON-LD-Codeblock, mit `<script type="application/ld+json">`-Umschlag, sonst nichts. Fehlt ein Feld in den Fakten: weglassen, nicht raten.

Einfügen: Codeblock (vom `<script>` bis `</script>`) an den Webbetreuer, Auftrag "in den `<head>` der Startseite einfügen" — oder selbst über ein SEO-Plugin/"Insert Headers and Footers" in WordPress.
Agentur-Briefing: Datensatz im `<head>`-Bereich jeder Seite (mindestens Startseite) einbinden, unverändert übernehmen, bei künftigen Fakten-Änderungen (z. B. neue Telefonnummer) mitpflegen.
Checkliste: Datensatz im Seitenquelltext sichtbar; Rich-Results-Test findet gültige Hotel/Lodging-Entität; keine Platzhalter mehr; Adresse/Telefon stimmen mit dem Impressum überein.

---

**3. H1-Titel + Subheadline für die Startseite** — *Die zentrale Überschrift der Startseite mit erklärendem Untertitel.*

> Erzeuge einen Vorschlag für die zentrale Überschrift (H1) und einen erklärenden Untertitel (Subheadline) der Startseite. Die H1 soll Hausnamen, Betriebstyp und Ort nennen (z. B. "Hotel Alpenblick — Boutique-Hotel in Kitzbühel"). Die Subheadline in 1 Satz das Kernversprechen des Hauses (nur aus den Fakten ableitbar).
>
> Format: `H1: ...` / `Subheadline: ...`

Einfügen: großen Titel oben auf der Startseite ersetzen, Subheadline direkt darunter in kleinerer Schrift.
Agentur-Briefing: H1 als `<h1>`-Element (auf der Startseite genau einmal), Subheadline direkt darunter.
Checkliste: H1 als `<h1>` sichtbar; genau ein `<h1>` auf der Startseite; Subheadline direkt darunter.

---

**4. USP-Box: 4 Alleinstellungsmerkmale** — *Vier prägnante Merkmale, sichtbar auf der Startseite und in KI-Antworten.*

> Erzeuge eine USP-Box mit genau 4 Alleinstellungsmerkmalen des Hauses. Jedes Merkmal in Form: "Kurz-Titel (max 3 Wörter) — Erklärung (max 12 Wörter)". Die USPs müssen aus den Fakten abgeleitet sein, nicht erfunden.
>
> Format: `USP 1: [Titel] — [Erklärung]` … bis USP 4.

Einfügen: kleine Box auf der Startseite, direkt unter der H1 oder als eigener Abschnitt.
Agentur-Briefing: USP-Box prominent auf der Startseite einrichten, wenn möglich mit Icon je Merkmal.
Checkliste: 4 USPs prominent sichtbar; jedes mit Kurz-Titel + Erklärung; USPs entsprechen der Realität des Hauses.

---

**5. 20 lokale Keywords** — *Suchbegriffe, unter denen Gäste das Haus wahrscheinlich anfragen — Grundlage für Texte und Meta-Descriptions.*

> Erzeuge eine Liste von genau 20 lokalen Keywords und Longtail-Suchphrasen für dieses Haus. Aus den Fakten kombinierbar: Betriebstyp + Ort + typische Zusätze (mit Wellness, Familien, Hund, mit Frühstück, Direkt am Berg, in der Nähe von...). Keine allgemeinen Keywords wie "Urlaub" — alle mit lokalem und thematischem Bezug.
>
> Format: eine Zeile pro Keyword, ohne Nummerierung.

Einfügen: Referenzliste — bei jedem neuen Text 1-2 Begriffe natürlich einflechten; an den Webbetreuer für Meta-Descriptions/Seiten-Titel weitergeben.
Agentur-Briefing: pro Seite prüfen, ob mindestens ein Keyword im Meta-Title und in der H1 abgedeckt ist, sonst nachtragen.
Checkliste: Keywords passen zu Haus und Region; wichtigste (Betriebstyp+Ort) auf Startseite in Meta-Title/H1 abgedeckt; keine falschen regionalen Zuschreibungen.

---

**6. Google-Business-Text (Kurzbeschreibung)** — *Kurzbeschreibung fürs Google-Business-Profil, erscheint bei Google-Maps-Suchen und speist AI-Overviews.*

> Erzeuge eine Kurzbeschreibung für das Google-Business-Profil. Maximal 750 Zeichen. Sie-Form, sachlich, ausschließlich Fakten des Hauses. Keine Sonderzeichen außer Standard-Interpunktion.
>
> Struktur (je 1-3 Sätze): Wer wir sind + wo; Kern-USPs; Zielgruppe; Aufruf (buchen/Kontakt/mehr erfahren).
>
> WICHTIG: auch bei dünner Faktenlage immer zusammenhängenden Fließtext liefern — nie leer, nie nur Aufzählungszeichen, nie nur Marker. Fehlt eine Angabe: umgebenden Satz vollständig formulieren, Marker mit klarem Bezug direkt an die offene Stelle setzen.
>
> Rückgabe: nur Fließtext, keine Überschriften, keine Aufzählungszeichen, keine Meta-Kommentare.

Einfügen: business.google.com → Profil bearbeiten → Beschreibung ersetzen (bzw. Profil neu anlegen, falls es noch keins gibt).
Agentur-Briefing: Beschreibung im Google-Business-Profil eintragen (Feld "Beschreibung", Limit 750 Zeichen), Profil ggf. neu einrichten, nichts umschreiben.
Checkliste: Beschreibung im Profil sichtbar; unter 750 Zeichen; keine Platzhalter mehr.

---

**7. 3 Meta-Descriptions** — *Erscheinen in Google unter dem blauen Ergebnis-Titel — je eine für Startseite, Zimmer-Seite, Kontakt-Seite.*

> Erzeuge genau 3 Meta-Descriptions, je maximal 155 Zeichen, österreichisches Deutsch, Sie-Form.
> A) Startseite: Betriebstyp + Ort + Kern-USP + Buchungs-Aufruf.
> B) Zimmer-Seite: Zimmertypen + Ausstattungs-Highlight + Preis-Signal.
> C) Kontakt-Seite: Ort + Anreise-Hinweis + Kontaktweg.
>
> Platzhalter deutlich kennzeichnen: fehlt eine Kernangabe, IMMER `[bitte prüfen und ergänzen]` an dieser Stelle setzen — den Satz nicht so formulieren, als wäre er schon fertig.
> Nie mitten im Wort/Satz abbrechen: jede Description muss ein vollständiger Satz sein, sauber endend auf Punkt/Frage-/Ausrufezeichen oder Marker. Passt der vollständige Satz nicht in 155 Zeichen: kürzer formulieren, niemals abschneiden.
>
> Format: `A (Startseite): ...` / `B (Zimmer): ...` / `C (Kontakt): ...`

Einfügen: in WordPress mit SEO-Plugin je Seite im SEO-Snippet-Feld "Beschreibung" einfügen.
Agentur-Briefing: die drei Descriptions in die entsprechenden Seiten eintragen, sonst keine anderen Meta-Tags ändern.
Checkliste: `site:<domain>`-Test zeigt neue Descriptions; jede unter 155 Zeichen; kein Platzhaltertext mehr.

---

**8. Über-uns-Text** — *Persönlicher, sachlicher Text über Haus, Geschichte, Werte und die Menschen dahinter — Grundlage der Vertrauensbildung.*

> Erzeuge einen Über-uns-Text von ca. 200-350 Wörtern, österreichisches Deutsch, warmer aber sachlicher Ton. Ausschließlich Fakten des Hauses.
>
> Struktur: Absatz 1 — wer wir sind (Familienbetrieb? Geschichte? Alter?), Ort und Lage. Absatz 2 — was uns ausmacht, 2-3 Aspekte aus den USPs. Absatz 3 — für wen wir da sind, was Gäste erleben.
>
> Keine Superlative wie "einzigartig", "unvergleichlich". Fehlt Geschichte/Alter: Absatz kürzer halten statt füllen.

Einfügen: als "Über uns"-Seite einfügen bzw. bestehenden Text ersetzen.
Agentur-Briefing: Text der "Über uns"-Seite ersetzen, normale Absätze, keine zusätzlichen Überschriften.
Checkliste: Seite über Hauptmenü erreichbar; neuer Text ersetzt alten; alle Marker ergänzt oder entfernt.

---

### 2.7 Technische Fehlstellen ohne Textbaustein-Lösung

Zwei Befunde erzeugen **kein** Textbaustein, sondern ein fertiges Agentur-Briefing (weil kein Text das Problem behebt):

**JavaScript-Rendering** (wenn Signal 3 ROT/GELB war und der Beleg SPA/React/Vue/Angular/Next/Nuxt/Vite/JavaScript nennt):
> Die Website liefert im rohen HTML nur ein Gerüst aus; die Inhalte werden erst durch JavaScript im Browser aufgebaut. KI-Crawler lesen typischerweise nur das rohe HTML und erfassen die Seite dadurch kaum. Bitte Server-Side-Rendering (SSR) oder statisches Pre-Rendering einrichten, sodass die zentralen Inhalte (Zimmer, Angebot, Kontakt) bereits im initialen HTML enthalten sind.

Checkliste: "Seitenquelltext anzeigen" zeigt Zimmer-/Adress-/Telefondaten als lesbaren Text (nicht nur `<div id="root"></div>`); Mobile-Friendly-Test zeigt Inhalte; geladenes HTML mindestens ~5000 Zeichen groß.

**Zugangs-Blockade (robots.txt)** (wenn Signal 1 ROT war):
> In der robots.txt sind eine oder mehrere KI-Suchmaschinen-Bots ausgeschlossen. Bitte robots.txt prüfen und die `Disallow: /`-Zeile für die sichtbarkeitskritischen Bots entfernen (mindestens OAI-SearchBot, ChatGPT-User, PerplexityBot, Google-Extended, Bingbot). Trainings-Bots (GPTBot, ClaudeBot, CCBot) können auf Wunsch weiterhin ausgeschlossen bleiben.

Checkliste: `<domain>/robots.txt` erreichbar; keine `Disallow: /` für die genannten Bots; nach Änderung erneuten Radar-Lauf machen, Signal 1 sollte GRÜN sein.

---

## 3. Regionsanalyse / Destinations-Türöffner (TVB/DMO-Batch)

**Zweck:** ein TVB/eine DMO liefert alle Mitgliedsbetriebe einer Kategorie (Name + Domain, z. B. alle Hotels), der Skill prüft jeden Betrieb einzeln nach Abschnitt 1 und aggregiert zu einer Destinations-Übersicht. Dies ist der kostenlose Türöffner-Testlauf vor dem eigentlichen Angebot (Online-Termin, ReviewRadar/GEO-Pakete).

**Wichtig zur Einordnung:** Die Pro-Betrieb-Prüfung (Schritt A-D) ist 1:1 dieselbe Logik wie in Abschnitt 1 und damit exakt wie geo-radar's `scanner.py`. Die **Destinations-Zusammenfassung** unten (Prozent-Verteilung, häufigste Stolpersteine) hat dagegen **kein direktes Code-Vorbild** in geo-radar — sie ist eine Synthese-Schicht, die auf den exakten Einzelergebnissen aufbaut. Das wird hier ausdrücklich offengelegt, damit "exakt wie geo-radar" nicht fälschlich auch für diesen Teil beansprucht wird.

### 3.1 Ablauf

1. Für jeden Betrieb der Liste: Schritte A-D aus Abschnitt 1 durchführen (Signal 1, 2, 3, Gesamt-Ampel).
2. **Destinationsranking** erzeugen: alle Betriebe sortiert — schlechteste Ampel zuerst, dann alphabetisch (identisch zur Sortierlogik der geo-radar-Ergebnis-CSV). Aggregationsregel für "schlechtester Status" (`batch_status`, exakt wie `scanner.py`):
   ```
   Rangordnung: ROT (0) < GELB (1) < UNBEKANNT (2) < GRÜN (3)
   Batch-Status = der Status mit der niedrigsten Zahl in der Gruppe.
   ```
   (Dieselbe Rangordnung gilt auch, wenn z. B. "wie steht Signal 1 destinationsweit da" gefragt ist — schlimmster Einzelbefund gewinnt.)
3. **Destinations-Zusammenfassung** (Synthese, siehe oben): Prozent-Verteilung GRÜN/GELB/ROT/UNBEKANNT über die Gesamt-Ampel aller Betriebe, plus dieselbe Verteilung getrennt je Signal (1/2/3) — das zeigt, ob z. B. vor allem Signal 2 (Schema.org) der Flaschenhals der Destination ist. Dazu die 2-3 am häufigsten wiederkehrenden Befund-Begründungen je Signal (z. B. "12 von 30 Betrieben: keine Lodging-Entität gefunden").

### 3.2 Ausgabeformat Regionsanalyse

```
GEO-Radar Destinationsanalyse — <Destination/TVB-Name>
Kategorie: <z. B. "alle Hotels">, Anzahl Betriebe: <n>
Datum: <Datum>

DESTINATIONS-ZUSAMMENFASSUNG
Gesamt-Ampel-Verteilung: <x>% GRÜN, <x>% GELB, <x>% ROT, <x>% UNBEKANNT
Signal 1 (KI-Crawler-Zugang):      <x>% GRÜN / <x>% GELB / <x>% ROT / <x>% UNBEKANNT
Signal 2 (Strukturierte Daten):    <x>% GRÜN / <x>% GELB / <x>% ROT / <x>% UNBEKANNT
Signal 3 (Maschinenlesbarkeit):    <x>% GRÜN / <x>% GELB / <x>% ROT / <x>% UNBEKANNT

Häufigste Stolpersteine:
- Signal 2: <Befund>, betrifft <n> Betriebe
- Signal 3: <Befund>, betrifft <n> Betriebe

DESTINATIONS-RANKING (schlechtester Status zuerst, dann alphabetisch)
| Betrieb | Domain | Gesamt-Ampel | Signal 1 | Signal 2 | Signal 3 |
|---|---|---|---|---|---|
| ... | ... | ROT | ... | ... | ... |
```

### 3.3 Umfang und praktischer Hinweis

Für sehr große Mitgliederlisten (Richtwert: >20-30 Betriebe) im Chat kurz ansagen, dass ein Lauf dieser Größe lange dauert und anbieten, in Tranchen zu arbeiten oder auf die geo-radar-CLI (`scanner.py --from-csv`) auszuweichen, die für Batches gebaut ist. Kein stiller Abbruch mitten in der Liste — wenn eine Domain nicht erreichbar ist, mit UNBEKANNT weiterlaufen und am Ende alle nicht abrufbaren Domains gesammelt ausweisen, statt sie kommentarlos wegzulassen.

---

## 4. Praktische Hinweise für den Chat-Einsatz

- **Wenn Web-Fetch in der aktuellen Umgebung nicht verfügbar ist:** ehrlich sagen, dass robots.txt/HTML nicht abgerufen werden können, und NICHT aus Erinnerung/Trainingswissen über die Domain urteilen. Stattdessen auf den geo-radar-Ordner ("Neuer Kunde"-Button) oder die Streamlit-Web-Checker-Version verweisen.
- **Trigger-Phrasen**, die diesen Skill aktivieren sollen: "GEO-Radar", "Betrieb prüfen für [Domain]", "GEO-Check", "Destinationsanalyse", "TVB-Testlauf", "Bausteine erzeugen für [Betrieb]", "Auftrag [Nummer]".
- **Abgrenzung zum Skill `geo-checker-tourism`:** jener beschreibt das Produktportfolio/die Preise und den kostenlosen Streamlit-Web-Checker (das "Schaufenster" für Endkunden) — dieser Skill hier ist die ausführende Prüf-Logik für den Chat-Einsatz selbst. Beide zusammen nutzen, wenn im Chat sowohl über Preise/Vertrieb als auch über eine konkrete technische Prüfung gesprochen wird.

---

## 5. Quellenverweis

Alle Regeln oben stammen wortgetreu aus: Repo `griedel69-spec/geo-radar`, Commit `c6546a3839829776ccbfc3b24d384057e4ad1817`.
- Signal 1: `src/signal1_robots.py` (komplett)
- Signal 2: `src/signal2_schema.py` (komplett)
- Signal 3: `src/signal3_rendering.py` (komplett)
- Batch-Aggregation/Sortierung: `src/scanner.py` (`STATUS_ORDER`, `batch_status`)
- Gesamt-Ampel Einzelbetrieb: `src/report.py` (`compute_overall`)
- Produktionsstufe/8 Bausteine/Kontrolldurchlauf/Kostenkonstanten: `src/production.py` (`BAUSTEINE`-Dict, `bausteine_aus_befund`, `technische_fehler_aus_befund`, `erkenne_vorhandene_faq`, `verankere_fakten`, `KONTROLLE_SYSTEM_PROMPT`, `MAX_KOSTEN_PRO_LAUF_USD`/`MAX_KOSTEN_PRO_HAUS_USD`, `CRAWL_PFADE`/`CRAWL_LINK_HINTS`)

Bei Widerspruch zwischen diesem Text und dem tatsächlichen geo-radar-Code gilt der Code. Dieser Skill sollte bei größeren geo-radar-Änderungen erneut gegen den Quellcode abgeglichen werden.
