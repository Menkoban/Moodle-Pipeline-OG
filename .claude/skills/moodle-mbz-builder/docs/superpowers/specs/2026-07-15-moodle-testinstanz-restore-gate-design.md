# Design: `moodle-testinstanz` als optionales Live-Restore-Gate

- **Datum:** 2026-07-15
- **Status:** Design freigegeben (Brainstorming), Umsetzungsplan folgt
- **Betroffene Skills:** `moodle-mbz-builder`, `moodle-adaptive-mbz-builder` (Integration) · `moodle-testinstanz` (neu, wird in Parallel-Chat gebaut)
- **Zweck des Dokuments:** Zugleich **Spec** der Integration UND **Vertrag** (`run_restore.py`-Schnittstelle), den der Parallel-Chat beim Bau von `moodle-testinstanz` 1:1 erfüllen muss.

---

## 1. Kontext & Ziel

Die Builder-Skills erzeugen `.mbz`-Kurssicherungen und prüfen sie heute **rein statisch**
(`validate_mbz.py` = XML-Struktur, `simulate_pathways.py` = adaptive Pfade). Ob Moodle die
Sicherung beim **Restore tatsächlich annimmt**, wird nie gegen eine echte Instanz getestet.

Ziel: ein **optionaler, automatisch erkannter** Live-Restore-Smoke-Test. Ist der Skill
`moodle-testinstanz` (mit lokalem, Docker-freiem Moodle-4.5-Lab, `format_tiles`) vorhanden,
restauriert das Schluss-Gate die frisch gebaute `.mbz` wirklich und meldet, ob „der Kurs
hochgeht". Ist er **nicht** vorhanden, läuft alles **exakt wie heute** weiter.

## 2. Problem, das nur ein echter Restore lösen kann

Die dokumentierte Bug-Historie besteht fast vollständig aus **Restore-Zeit-Fehlern**, die eine
statische XML-Prüfung strukturell **nicht** fangen kann:

- `dmlwriteexception` durch `$@NULL@$` in **Attributen** (Restore dekodiert NULL nur in
  Element-Texten)
- `required_param(): contextid fehlt` (verwaiste Kontexte / Quiz-Fragen im falschen
  `contextlevel`)
- `question_categories`-Scope generatorweit
- unerreichbare Tiles

Nur ein echter Restore in eine laufende Instanz erzeugt den **Moodle-Stacktrace**, der diese
Klasse aufdeckt. **Compounding-Effekt:** Jeder so gefundene Fehler wird anschließend als
statischer Check in `validate_mbz.py` verewigt → das Lab wird zur *Validator-Fabrik*.

## 3. Nicht-Ziele (YAGNI)

- **Kein** pytest-Hook (bewusst verworfen — ein Einhängepunkt genügt: das Schluss-Gate).
- **Kein** CI-Server, keine Multi-Moodle-Versions-Matrix (eine Instanz: Moodle 4.5).
- **Kein** Performance-/Last-Test. Reiner **Smoke-Test**: Restore läuft durch, ja/nein.
- **Keine** Docker-Abhängigkeit — das Lab ist portabel.
- Die Builder-Skills bekommen **keine** neuen schwergewichtigen Abhängigkeiten in ihre
  `requirements.txt`.

## 4. Architektur-Überblick

```
moodle-mbz-builder ─┐
                    ├─(optional, auto-detect)→  moodle-testinstanz
moodle-adaptive-…  ─┘        scripts/run_restore.py  →  portables Moodle-4.5-Lab
        │                                                (kein Docker, format_tiles)
        ▼
 check_delivery.py  ──  Schritt 9 „Live-Restore" (neu, weiches Gate)
   1..8 wie bisher (validate_mbz, preview, editor, materials, video, simulate_pathways)
```

- **Abhängigkeitsrichtung:** Builder → `moodle-testinstanz` (optional, keine Rückkopplung,
  kein Zyklus).
- **`check_delivery.py` ist in beiden Builder-Skills byte-identisch** → Schritt 9 wird **einmal**
  geschrieben und in beide Kopien gespiegelt (skill-organizer-Sync).
- **`validate_mbz.py` ist zwischen den Skills gedriftet** — irrelevant, der Hook ruft
  ausschließlich `run_restore.py`.

## 5. Der Vertrag — `moodle-testinstanz/scripts/run_restore.py`

Das ist die **einzige** Kopplungsfläche zwischen den Skills. Klein und stabil halten.

### 5.1 Discovery (wie `check_delivery` den Skill findet)

```
Standardpfad:  ~/.claude/skills/moodle-testinstanz/scripts/run_restore.py
Override:      Env  MOODLE_TESTINSTANZ_HOME  (zeigt auf den Skill-Ordner)
```

Existiert die Datei nicht → Skill gilt als „nicht vorhanden" → Schritt 9 wird **still
übersprungen**.

### 5.2 Aufrufe & Exit-Codes

| Aufruf | Bedeutung | Exit-Codes |
|---|---|---|
| `run_restore.py --health` | Preflight: ist das Lab bereit für einen Restore? | `0` = Lab up · `3` = Lab down/fehlt/nicht gebootstrappt |
| `run_restore.py <kurs.mbz> [--json] [--keep]` | `.mbz` in Wegwerf-Kurs restaurieren | `0` = Restore ok · `2` = **echter Restore-Fehler** (Moodle lehnt ab) · `3` = Lab während Restore verloren |

**Exit-Code-Disziplin ist der Kern des weichen Gates:** `3` (Lab nicht da) darf **niemals**
mit `2` (Kurs kaputt) verwechselt werden — sonst bricht der „läuft wie bisher"-Fallback.

### 5.3 `--json`-Ausgabe (ein Objekt auf stdout)

```json
{
  "status": "ok",
  "restored_course_id": 42,
  "moodle_version": "4.5.2",
  "format_tiles": true,
  "log_tail": "…letzte Restore-Logzeilen (bei Fehler der Stacktrace)…"
}
```

`log_tail` ist bei Exit 2 das **Stacktrace-Futter** für neue `validate_mbz`-Checks.

### 5.4 Verhalten

- **Default = Teardown:** der angelegte Testkurs wird nach dem Restore wieder gelöscht
  → verhindert `contextid`-Kollisionen bei Folge-Restores (genau die Bug-Klasse, die wir jagen).
- `--keep` behält den Kurs zum Inspizieren.
- **Idempotent / mehrfach sicher aufrufbar** (eindeutiger `shortname` pro Lauf, sauberes
  Cleanup).
- `--health` ist **allein** für das Auffinden/Prüfen des Labs zuständig; `check_delivery`
  weiß nichts vom Lab-Ort.

### 5.5 Anforderungen an das Lab selbst (Aufgabe des Parallel-Chats)

- **Lab raus aus dem Temp-Pfad.** Aktuell unter
  `C:\Users\User\AppData\Local\Temp\claude\moodle-lab\` — dieser Bereich ist flüchtig
  (Session-Scratchpad, aufräumgefährdet). Für ein **dauerhaftes** Dev-Tool an stabilen Ort,
  Vorschlag: `~/.claude/moodle-lab/` (Override Env `MOODLE_LAB_HOME`).
- **Self-Bootstrap:** fehlt das Lab am stabilen Ort, baut `run_restore.py --health` es auf
  (Codebase + DB-Data + `format_tiles`) oder meldet sauber Exit 3 mit Hinweis.
- Alle schwergewichtigen Abhängigkeiten (portable PHP/MariaDB, Moodle-Codebase, Plugin)
  liegen **ausschließlich** in `moodle-testinstanz`.

## 6. `check_delivery.py` — Schritt 9 (einfügefertig)

### 6.1 Neue Konstante (bei den übrigen oben im Modul)

```python
TESTINSTANZ_HOME = os.environ.get(
    "MOODLE_TESTINSTANZ_HOME",
    os.path.expanduser("~/.claude/skills/moodle-testinstanz"),
)
```

### 6.2 Neue Hilfsfunktion

```python
def live_restore_probe(mbz_path, require):
    """Optionaler dynamischer Check: echte .mbz gegen das lokale Moodle-Lab
    restaurieren. Gibt (ok, warn, fehler) zurueck. Weiches Gate:
      - Skript fehlt    -> skip (leer)          ausser --require-live-restore
      - Lab down (rc=3) -> WARN                  ausser --require-live-restore
      - Restore-Fehler  -> FEHLER (Gate rot)
    """
    ok, warn, fehler = [], [], []
    runner = os.path.join(TESTINSTANZ_HOME, "scripts", "run_restore.py")
    if not os.path.exists(runner):
        if require:
            fehler.append("--require-live-restore gesetzt, aber Skill "
                          f"'moodle-testinstanz' nicht gefunden ({runner})")
        return ok, warn, fehler  # sonst still ueberspringen

    # Preflight: laeuft das Lab?
    h = subprocess.run([sys.executable, runner, "--health"],
                       capture_output=True, text=True)
    if h.returncode != 0:
        msg = ("Moodle-Lab nicht erreichbar — Live-Restore uebersprungen "
               f"(rc={h.returncode}: {h.stdout.strip()[-200:]})")
        (fehler if require else warn).append(msg)
        return ok, warn, fehler

    # Echter Restore
    r = subprocess.run([sys.executable, runner, mbz_path, "--json"],
                       capture_output=True, text=True)
    if r.returncode == 0:
        ver = ""
        try:
            info = json.loads(r.stdout)
            ver = (f" (Moodle {info.get('moodle_version', '?')}, "
                   f"tiles={info.get('format_tiles')})")
        except Exception:
            pass
        ok.append(f"Live-Restore gruen: Kurs geht hoch{ver}")
    elif r.returncode == 3:
        (fehler if require else warn).append(
            "Lab waehrend Restore verloren — uebersprungen")
    else:  # rc == 2 (oder unerwartet) -> echter Fehler
        tail = (r.stdout + r.stderr).strip()[-800:]
        fehler.append(f"LIVE-RESTORE FAIL (Moodle lehnt .mbz ab):\n{tail}")
    return ok, warn, fehler
```

### 6.3 Neues Flag + Aufruf in `main()`

```python
# bei den argparse-Flags
ap.add_argument("--require-live-restore", action="store_true",
                help="Live-Restore gegen moodle-testinstanz erzwingen — "
                     "Abwesenheit/Lab-down werden dann zum Fehler.")

# nach Schritt 8 (adaptives Ratschen-Gate), vor der Ausgabe:
# 9. Live-Restore (optional, nur wenn Skill moodle-testinstanz vorhanden)
if len(mbzs) == 1:
    lok, lwarn, lfehler = live_restore_probe(mbzs[0], args.require_live_restore)
    ok += lok; warn += lwarn; fehler += lfehler
elif args.require_live_restore:
    fehler.append("--require-live-restore, aber keine eindeutige .mbz im Ordner")
```

## 7. `SKILL.md`-Änderungen (beide Builder)

An das jeweilige Schluss-Gate (mbz-Schritt 8 / adaptiv-Schritt 9) **ein Halbsatz**:

> Ist der Skill `moodle-testinstanz` installiert, führt `check_delivery.py` automatisch einen
> **Live-Restore** der `.mbz` gegen das lokale Moodle-Lab aus. Fehlt der Skill oder ist das Lab
> nicht erreichbar, wird der Schritt still übersprungen (WARN) — das Gate bleibt grün. **Rot**
> wird es nur bei einem **echten Restore-Fehler**. Mit `--require-live-restore` lässt sich der
> Test erzwingen.

## 8. Degradations-Matrix (Kern-Verhalten)

| Situation | ohne `--require-live-restore` | mit `--require-live-restore` |
|---|---|---|
| `run_restore.py` fehlt (Skill nicht da) | skip, **grün** (wie heute) | **rot** |
| Lab down / Health rc=3 | **WARN**, grün | **rot** |
| Restore ok (rc=0) | **ok**, grün | **ok**, grün |
| Restore-Fehler (rc=2) | **rot** | **rot** |

## 9. Teststrategie

- **Kein** neuer pytest-Test (Nicht-Ziel). Verifikation der Integration über das Gate selbst:
  1. Ohne `moodle-testinstanz` installiert → `check_delivery` verhält sich unverändert
     (Regression: bestehende Deliverable-Checks weiter grün, kein Schritt-9-Rauschen).
  2. Mit Dummy-`run_restore.py`, das rc=0 liefert → `ok: Live-Restore gruen …`.
  3. Dummy rc=3 → WARN, Gate grün; mit `--require-live-restore` → rot.
  4. Dummy rc=2 mit `log_tail` → `FEHLER`, Gate rot, Stacktrace im Output.
- Echter End-to-End-Restore wird über den fertigen `moodle-testinstanz`-Skill validiert.

## 10. Risiken & offene Punkte

- **Temp-Pfad-Persistenz** (Abschnitt 5.5): muss der Parallel-Chat lösen, sonst greift der
  Auto-Detect nur zufällig.
- **Parallele Skill-Ordner-Schreibzugriffe:** dieser Chat editiert `check_delivery.py` /
  `SKILL.md`; der andere Chat legt `moodle-testinstanz/` an. Keine Überschneidung der Dateien,
  aber Reihenfolge im Hinterkopf behalten (erst Vertrag fix, dann `run_restore.py` bauen).
- **Restore-Dauer:** zig Sekunden — akzeptabel, weil nur am Schluss-Gate, nicht in der
  Bau-Schleife.
- **Vertrags-Drift:** ändert der andere Chat die `run_restore.py`-Signatur, muss Abschnitt 5
  hier nachgezogen werden (Single Source of Truth für die Schnittstelle).

## 11. Umsetzungsschritte (Vorschau — Detailplan via writing-plans)

1. `check_delivery.py` (mbz-Kopie) um Konstante, `live_restore_probe`, Flag + Schritt-9-Aufruf
   ergänzen.
2. Datei nach `moodle-adaptive-mbz-builder/scripts/check_delivery.py` spiegeln (identisch halten).
3. Halbsatz in beide `SKILL.md` (Schritt 8 bzw. 9).
4. Verifikation per Dummy-`run_restore.py` (Matrix aus Abschnitt 8/9 durchspielen).
5. Diesen Vertrag (Abschnitt 5) an den Parallel-Chat übergeben, damit `moodle-testinstanz`
   passgenau gebaut wird.
