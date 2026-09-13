---
name: prompt-verstaendnis
description: >
  Interpretiert und versteht Nutzer-Prompts eines deutschsprachigen Entwicklers, der an seiner eigenen App
  (Agrarmonitor, TypeScript) arbeitet. Der Nutzer schreibt schnell, direkt und mit natürlichen Tippfehlern —
  dieser Skill dekodiert die tatsächliche Absicht, erkennt das wiederkehrende Dreier-Agenten-Setup
  (Research → Code → Test), identifiziert Qualitätsanforderungen und stellt sicher, dass die
  Selbst-Reflexions-Klausel am Ende jeder Ausarbeitung eingehalten wird.
  Nutze diesen Skill IMMER wenn: der Nutzer einen komplexen Entwicklungs-Prompt auf Deutsch schreibt,
  ein Agenten-Setup erwähnt, Begriffe wie "sehr detailliert", "spezifisch", "hinterfrage", "Agenten",
  "Testsprite", "Agrarmonitor" verwendet, oder wenn der Prompt mehrere verschachtelte Anweisungen enthält,
  die entschlüsselt werden müssen. Auch bei kurzen Prompts triggern, wenn sie Agenten-Referenzen oder
  Qualitätsmarker enthalten.
---

# Prompt-Verständnis Skill

Dieser Skill ermöglicht das präzise Verstehen und Ausführen von Prompts eines spezifischen Nutzers.
Der Nutzer entwickelt Agrarmonitor (eine TypeScript-App) und kommuniziert in einem charakteristischen
Stil, der ohne diesen Skill leicht missverstanden werden kann.

## Warum dieser Skill existiert

Der Nutzer denkt schnell und tippt im Flow. Seine Prompts sind dicht gepackt mit Informationen,
enthalten Tippfehler und setzen voraus, dass Claude den Kontext von Agrarmonitor, das Agenten-Setup
und die impliziten Qualitätserwartungen bereits kennt. Ohne strukturierte Dekodierung gehen
Teilanweisungen verloren oder werden falsch priorisiert.

---

## Schritt 1: Prompt-Dekodierung

Beim Eingang eines Prompts diese Analyse-Sequenz durchlaufen — **intern, nicht als Output an den Nutzer**:

### 1.1 Tippfehler-Korrektur (still, ohne Erwähnung)

Der Nutzer macht konsistente Tippfehler. Diese niemals kommentieren, sondern still korrekt interpretieren:

| Häufige Schreibweise       | Gemeinte Bedeutung            |
|----------------------------|-------------------------------|
| detaliert / detaliert      | detailliert                   |
| ausarbietung               | Ausarbeitung                  |
| ein sein Team              | in sein Team                  |
| spezialiesiert             | spezialisiert                 |
| rücksoicht / rückbetracht  | Rücksicht / Rückbezug         |
| etablieren (im Kontext)    | einbinden / integrieren       |
| Testsprite                 | Testsprite MCP (Testing-Tool) |

Grundregel: Wenn ein Wort phonetisch oder visuell einem deutschen Wort ähnelt, ist das gemeint.
Niemals nachfragen ob ein Tippfehler vorliegt — einfach korrekt interpretieren und ausführen.

### 1.2 Struktur-Extraktion

Jeder Prompt des Nutzers folgt einem wiederkehrenden Muster mit bis zu 5 Schichten.
Extrahiere diese Schichten in genau dieser Reihenfolge:

```
┌─────────────────────────────────────────────────┐
│ SCHICHT 1: AUFGABE                              │
│ Was soll konkret getan werden?                  │
│ → Erste(r) Satz/Sätze des Prompts              │
├─────────────────────────────────────────────────┤
│ SCHICHT 2: QUALITÄTSMARKER                      │
│ Wie tief/genau soll gearbeitet werden?          │
│ → Signalwörter: "sehr", "spezifisch",          │
│   "detailliert", "gib dir Mühe", "organisiert" │
├─────────────────────────────────────────────────┤
│ SCHICHT 3: AGENTEN-SETUP                        │
│ Welche Agenten-Rollen werden zugewiesen?        │
│ → Siehe Referenz: references/agent-setup.md     │
├─────────────────────────────────────────────────┤
│ SCHICHT 4: KONTEXT-REFERENZEN                   │
│ Wird auf Agrarmonitor, Module oder Tools        │
│   verwiesen?                                    │
│ → Bekannte Module & Tech-Stack beachten         │
├─────────────────────────────────────────────────┤
│ SCHICHT 5: SELBST-REFLEXIONS-KLAUSEL            │
│ Fast immer am Ende: "Hinterfrage..."            │
│ → PFLICHT: Immer ausführen, auch wenn vergessen │
└─────────────────────────────────────────────────┘
```

Für detaillierte Muster-Analyse mit realen Beispielen: lies `references/prompt-patterns.md`.

---

## Schritt 2: Qualitätsmarker interpretieren

Der Nutzer verwendet Intensitäts-Signale, die direkte Auswirkungen auf die erwartete Ausgabetiefe haben.
Das sind keine Floskeln — der Nutzer meint jedes Wort ernst:

| Signal im Prompt                 | Erwartete Reaktion                                              |
|----------------------------------|-----------------------------------------------------------------|
| "sehr detailliert"               | Jeder Aspekt einzeln ausarbeiten, keine Zusammenfassungen       |
| "sehr spezifisch"                | Keine generischen Antworten, immer auf Agrarmonitor bezogen     |
| "organisiert"                    | Klare Gliederung mit Überschriften, Sektionen, Reihenfolge     |
| "spezialisiert"                  | Fachlich tiefgehend, nicht oberflächlich                        |
| "gib dir Mühe"                   | Maximale Qualität, keine Abkürzungen, kein "Good enough"       |
| "strukturiert"                   | Logischer Aufbau, nachvollziehbare Schritte                    |
| Mehrere Marker kombiniert        | Höchste Qualitätsstufe — umfangreich UND präzise arbeiten      |

Wenn der Nutzer 3+ Marker in einem Prompt kombiniert (z.B. "sehr spezifisch detailliert und organisiert"),
bedeutet das: Dies ist eine wichtige Aufgabe. Investiere maximale Sorgfalt. Kürze nichts ab.

---

## Schritt 3: Agenten-Setup erkennen und anwenden

Der Nutzer arbeitet mit einem **Dreier-Agenten-System**. Die Grundstruktur ist:

| Agent   | Kernrolle                | Standard-Aufgabe                                    |
|---------|--------------------------|-----------------------------------------------------|
| Agent 1 | **Research / Analyse**   | Informationen holen, prüfen, Kontext aufbauen       |
| Agent 2 | **Code / Implementierung** | Code schreiben, Architektur umsetzen               |
| Agent 3 | **Test / QA (Testsprite MCP)** | Fehler suchen, testen, Qualität sicherstellen  |

Für die vollständige Agenten-Konfiguration mit Rollenbeschreibungen, Übergabe-Protokollen
und flexiblen Anpassungen: lies `references/agent-setup.md`.

### Wann das Agenten-Setup anwenden?

- **Explizit genannt**: Nutzer schreibt "Dreier-Agenten-Setup", "3 Agenten", oder beschreibt Rollen →
  Sofort das Setup strukturiert anwenden.
- **Implizit erkennbar**: Nutzer beschreibt eine Aufgabe die Research, Coding UND Testing umfasst →
  Agenten-Setup vorschlagen und anwenden.
- **Nicht relevant**: Einfache Fragen, kurze Änderungen, konzeptuelle Diskussionen →
  Kein Agenten-Setup erzwingen.

---

## Schritt 4: Agrarmonitor-Kontext

Agrarmonitor ist die App des Nutzers. Folgende Annahmen immer im Hintergrund mitführen:

- **Tech-Stack**: TypeScript (Hauptsprache)
- **Bekannte Module** (aus Prompts extrahiert): Team-Modul, Kunden-Datenbank, Aufträge,
  Karten-Ansicht, Stunden-Tracking, Gutschriften-System
- **Architektur-Annahme**: Modularer Aufbau, verschiedene Bereiche/Module die interagieren
- **Nutzer-Rolle**: Der Nutzer ist Entwickler UND Produkt-Owner — er denkt gleichzeitig
  in Features (was soll es tun) und Implementierung (wie soll es gebaut werden)

Wenn der Nutzer ein neues Modul oder Feature beschreibt, immer prüfen ob es mit bekannten
Modulen interagiert. Der Nutzer denkt vernetzt — einzelne Features stehen nie isoliert.

---

## Schritt 5: Selbst-Reflexion (PFLICHT)

Der Nutzer beendet fast jeden Prompt mit einer Variante von:
- "Hinterfrage am Ende mit Rücksicht auf den gegebenen Prompt"
- "Hinterfrage deine Ausarbeitung mit Rückbetracht auf den Prompt"
- "Hinterfrage mit Rücksicht auf den Prompt"

### Was damit gemeint ist:

Dies ist KEINE optionale Höflichkeitsfloskel. Der Nutzer erwartet eine **strukturierte
Selbst-Überprüfung** am Ende jeder Ausarbeitung. Diese Überprüfung umfasst:

1. **Vollständigkeits-Check**: Wurde jeder Aspekt des Prompts adressiert? Punkt für Punkt durchgehen.
2. **Prompt-Treue-Check**: Entspricht die Ausarbeitung dem, was tatsächlich gefragt wurde —
   oder wurde abgeschweift?
3. **Qualitäts-Check**: Wurden die Qualitätsmarker eingehalten? Ist es wirklich "sehr detailliert"
   wenn das verlangt wurde?
4. **Agenten-Check**: Wurden die Agenten-Rollen korrekt zugewiesen und ausgeführt?
5. **Lücken-Identifikation**: Was fehlt noch? Was könnte verbessert werden?

Format der Selbst-Reflexion:
```
## Selbst-Reflexion (Rückbezug auf Prompt)

✅ [Aspekt der erfüllt wurde] — [kurze Begründung]
✅ [Weiterer erfüllter Aspekt]
⚠️ [Aspekt der teilweise erfüllt wurde] — [was fehlt]
❌ [Aspekt der nicht erfüllt wurde] — [warum & nächste Schritte]

**Gesamtbewertung**: [Einschätzung ob der Prompt vollständig beantwortet wurde]
```

Selbst-Reflexion auch dann durchführen, wenn der Nutzer es in einem bestimmten Prompt
nicht explizit erwähnt — es ist sein Standard-Erwartung.

---

## Zusammenfassung: Verarbeitungs-Pipeline

Bei jedem eingehenden Prompt diese Pipeline durchlaufen:

```
PROMPT EINGANG
     │
     ▼
[1] Tippfehler still korrigieren
     │
     ▼
[2] 5-Schichten-Struktur extrahieren
     │
     ▼
[3] Qualitätsmarker → Tiefe bestimmen
     │
     ▼
[4] Agenten-Setup erkennen & konfigurieren
     │
     ▼
[5] Agrarmonitor-Kontext einbeziehen
     │
     ▼
[6] AUSFÜHRUNG mit voller Tiefe
     │
     ▼
[7] Selbst-Reflexion gegen Original-Prompt
     │
     ▼
OUTPUT AN NUTZER
```

---

## Referenz-Dateien

- `references/prompt-patterns.md` — Detaillierte Analyse realer Prompt-Beispiele mit
  Dekodierung jeder Schicht. Lies diese Datei wenn du unsicher bist, wie ein neuer Prompt
  zu interpretieren ist.
- `references/agent-setup.md` — Vollständige Beschreibung des Dreier-Agenten-Systems mit
  Rollen, Übergabe-Protokollen, flexiblen Anpassungen und Tool-Integration (Testsprite MCP).
  Lies diese Datei bei jeder Aufgabe die ein Agenten-Setup erfordert.
