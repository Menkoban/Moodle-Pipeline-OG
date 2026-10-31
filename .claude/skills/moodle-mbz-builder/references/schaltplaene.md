# Normgerechte Schaltpläne nach DIN EN 60617 in Moodle-Kursen

Dieses Referenzdokument beschreibt das Schaltsystem und die Nutzung des Generators `scripts/circuit_builder.py`. Es ermöglicht die präzise, automatisierte Erstellung von Schaltplänen für Infoblätter (PDF/PPTX), interaktive Seiten und Simulationen im Moodle-Kurs.

---

## 1. Das Schaltsymbol-Register (180 genormte Symbole)

Alle Symbole liegen als geprüfte Vektor-Bausteine in `assets/schaltsymbole/SVG/<symbolname>.svg` und sind im `assets/schaltsymbole/symbolregister-neu.json` indiziert.

### Wichtigste Symbolgruppen:
* **Quellen:** `quelleDC` (Spannungsquelle), `quelleI` (Stromquelle), `quelleAC` (Wechselspannung), `batterie`, `akku`, `batterieMehrzellig`.
* **Widerstände & passive Bauelemente:** `widerstand`, `widerstandEinstellbar`, `poti` (Potenziometer 3-polig), `trimmer`, `ntc`, `ptc`, `fotowiderstand`, `varistor`.
* **Kondensatoren & Spulen:** `kondensator`, `kondensatorPol` (Elko), `spule`, `spuleKern` (Drossel mit Eisenkern), `trafo` (Transformator), `stromwandler`.
* **Halbleiter & Dioden:** `diode`, `led`, `zdiode`, `fotodiode`, `schottkydiode`, `transistorNPN`, `transistorPNP`, `jfetN`, `mosfetN`, `igbt`, `thyristor`, `triac`, `diac`, `optokoppler`.
* **Schaltgeräte & Schütze:** `schalter`, `schliesser` (Klemmen 13-14), `oeffner` (Klemmen 21-22), `wechsler`, `taster`, `tasterOeffner`, `notaus`, `schuetzspule` (Relais/Schütz A1-A2), `sicherung` (F).
* **Verbraucher & Maschinen:** `lampe`, `motor` (Gleichstrommotor), `motor3` (Drehstrom-Asynchronmotor 3~), `generator3`, `hupe`, `klingel`.
* **Messtechnik:** `messer` (Multimeter / Amperemeter / Voltmeter via `wert="A"` oder `wert="V"`), `zaehler`, `oszilloskop`.
* **Anschlüsse & Leitungen:** `klemme` (offener Kreis), `knoten` (Verbindungspunkt, gefüllter Punkt), `erde`, `schutzerde`, `masse`.

---

## 2. Das 120×60-Rastersystem & Anschlusspunkte

Jedes Symbol ist nach DIN EN 60617 auf einer **120×60-Zelle** aufgebaut (Mittelachse $y=30$).

```
        (0, -10)                   (60, -10)                  (120, -10)
        [top-left]                   [top]                    [top-right]
            |                          |                          |
(0, 30) ----+--------------------------+--------------------------+---- (120, 30)
[left / 1 / in / A1 / 13]                                 [right / 2 / out / A2 / 14]
            |                          |                          |
        (0, 70)                    (60, 70)                   (120, 70)
       [bot-left]                   [bottom]                  [bot-right]
```

### Drehungen (`rot`):
- `rot: 0`: Waagerecht (Eingang links, Ausgang rechts).
- `rot: 90`: Senkrecht (Eingang oben, Ausgang unten).
- `rot: 180`: Waagerecht umgekehrt (Eingang rechts, Ausgang links).
- `rot: 270`: Senkrecht umgekehrt (Eingang unten, Ausgang oben).

Die Beschriftungen (BMK und Wert) werden automatisch rotationssicher platziert und bleiben immer lesbar.

---

## 3. Der Schaltplan-Generator (`scripts/circuit_builder.py`)

### Aufruf über die Kommandozeile:
```bash
# Standard-Presets erzeugen:
python <skill-dir>/scripts/circuit_builder.py --preset grundstromkreis     -o assets/grundstromkreis.svg
python <skill-dir>/scripts/circuit_builder.py --preset graetz_bruecke        -o assets/graetz_gleichrichter.svg
python <skill-dir>/scripts/circuit_builder.py --preset wendeschuetz_haupt    -o assets/wendeschuetz_haupt.svg
python <skill-dir>/scripts/circuit_builder.py --preset wendeschuetz_steuer   -o assets/wendeschuetz_steuer.svg
python <skill-dir>/scripts/circuit_builder.py --preset sterndreieck_haupt    -o assets/sterndreieck_haupt.svg

# Aus eigener DSL-JSON-Datei erzeugen:
python <skill-dir>/scripts/circuit_builder.py mein_schaltplan.json -o assets/schaltplan.svg

# Alle 180 Symbole mit Normtext auflisten:
python <skill-dir>/scripts/circuit_builder.py --list-symbols
```

---

## 4. Schaltplan-DSL (JSON-Format)

Eigene Schaltpläne können als kompaktes JSON definiert werden:

```json
{
  "circuit": {
    "title": "Reihenschaltung mit Lampe und Schalter",
    "nodes": [
      { "id": "Q1", "symbol": "quelleDC", "x": 100, "y": 140, "rot": 90, "label": "U_q", "wert": "24 V", "grid": false },
      { "id": "S1", "symbol": "schalter", "x": 260, "y": 140, "rot": 0, "label": "S1", "grid": false },
      { "id": "P1", "symbol": "messer", "x": 420, "y": 140, "rot": 0, "label": "P1", "wert": "A", "grid": false },
      { "id": "E1", "symbol": "lampe", "x": 580, "y": 140, "rot": 90, "label": "E1", "wert": "24V / 5W", "grid": false }
    ],
    "wires": [
      { "from": "Q1:top", "to": "S1:left", "routing": "direct" },
      { "from": "S1:right", "to": "P1:left", "routing": "direct" },
      { "from": "P1:right", "to": "E1:top", "routing": "direct" },
      { "from": "E1:bottom", "to": "Q1:bottom", "routing": "direct" }
    ],
    "arrows": [
      { "type": "I", "x": 360, "y": 140, "dir": "r", "label": "I" },
      { "type": "U", "x1": 640, "y1": 150, "x2": 640, "y2": 250, "label": "U_L" }
    ],
    "junctions": []
  }
}
```

### DSL-Felder im Detail:
* `nodes`:
  * `id`: Eindeutige Kennung (z.B. `"R1"`, `"K1"`, `"Q1"`).
  * `symbol`: Symbolname aus dem Register (z.B. `"widerstand"`, `"schuetzspule"`, `"motor3"`).
  * `x, y`: Koordinaten (in Pixeln bei `"grid": false`, oder als Grid-Einheiten bei `"grid": true`).
  * `rot`: Drehung in Grad (0, 90, 180, 270).
  * `label`: Betriebsmittelkennzeichen (BMK) nach ISO/IEC 81346.
  * `wert`: Bemessungswert oder Formelgröße (z.B. `"10 kΩ"`, `"230 V"`, `"A1-A2"`).
* `wires`:
  * `from` / `to`: Port-Referenz im Format `"NodeId:Port"` (z.B. `"K1:top"`, `"R1:right"`, `"S1:13"`, `"Q1:1_in"`) oder absolute Koordinate `[x, y]`.
  * `routing`: `"direct"` (Gerade), `"hv"` (erst horizontal, dann vertikal), `"vh"` (erst vertikal, dann horizontal), `"hvh"`, `"vhv"`.
  * `waypoints`: Optionale Liste von Zwischenpunkten `[[x1,y1], [x2,y2], ...]`.
  * `cls`: CSS-Klasse (`"wire"`, `"wire-thick"`, `"wire-pe"`, `"wire-n"`).
* `arrows`:
  * Stromzählpfeil (`type: "I"`): `x, y`, `dir` (`"r"`, `"l"`, `"u"`, `"d"`), `label`.
  * Spannungszählpfeil (`type: "U"`): `x1, y1` (höheres Potential), `x2, y2` (niedrigeres Potential), `label`.
* `junctions`:
  * `x, y`: Position des gefüllten Verbindungspunktes.

---

## 5. Normative Gestaltungsregeln (Elektrotechnik BBS)

1. **Stromlaufpläne im Hauptstromkreis:**
   - Phasen $L_1, L_2, L_3$ laufen von oben nach unten.
   - Schutzleiter $PE$ wird grün/gestrichelt gezeichnet (`.wire-pe`).
   - Motoren stehen unten.
2. **Steuerstromkreise:**
   - Steuerphase $L_1$ (oder $+24\,\text{V}$) liegt oben, Neutralleiter $N$ (oder $0\,\text{V}$) liegt unten.
   - Strompfade verlaufen vertikal nebeneinander von oben nach unten.
   - Schützspulen liegen direkt vor dem Neutralleiter unten.
   - Vor jeder Spule liegen die zugehörigen Taster, Selbsthaltekontakte und Verriegelungsöffner.
3. **Leiterverbindungen:**
   - T-Kreuzungen mit Verbindung müssen **immer** einen Knotenpunkt (`junction`) tragen.
   - Reine Kreuzungen ohne Punkt bedeuten "keine elektrische Verbindung".

---

## 6. Integration in die Moodle-Build-Pipeline

1. Generiere das Schaltplan-SVG mit `circuit_builder.py` (oder speichere es in `assets/`).
2. Führe den Standard-Check aus:
   ```bash
   python <skill-dir>/scripts/autofit_svg.py course.json
   python <skill-dir>/scripts/validate_svg.py course.json --strict
   ```
3. Binde das SVG in die Moodle-Page ein:
   ```json
   {
     "type": "page",
     "name": "Infoblatt: Die Wendeschützschaltung",
     "material": true,
     "images": ["assets/wendeschuetz_haupt.svg"],
     "content": "<h3>Hauptstromkreis</h3><p>...</p><img src='@@PLUGINFILE@@/wendeschuetz_haupt.svg' style='max-width:100%'>"
   }
   ```
4. `make_materials.py` rendert den Schaltplan automatisch gestochen scharf in die Druck-PDFs und PowerPoint-Folien.
