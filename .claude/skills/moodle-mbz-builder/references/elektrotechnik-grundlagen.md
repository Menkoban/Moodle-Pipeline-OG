# Referenzwissen: Elektrotechnische Grundlagen & Schaltungstechnik

Dieses Referenzdokument bündelt die fachlichen Grundlagen, Formeln, Normbezüge und Schaltungsstrukturen für elektrotechnische Moodle-Kurse (nach DIN EN 60617, DIN EN 81346, DIN VDE 0100). Es dient als Wissensbasis für die Generierung von Infoblättern, Rechenbeispielen, Simulationen und Schaltplänen.

---

## 1. Gleichstromkreis & Grundgesetze

### Ohmsches Gesetz
Der Zusammenhang zwischen elektrischer Spannung $U$, elektrischem Strom $I$ und dem Widerstand $R$:
$$U = R \cdot I \quad \Longleftrightarrow \quad I = \frac{U}{R} \quad \Longleftrightarrow \quad R = \frac{U}{I}$$
* Einheiten: $[U] = \text{V}$ (Volt), $[I] = \text{A}$ (Ampere), $[R] = \Omega$ (Ohm).

### Elektrische Leistung & Energie
$$P = U \cdot I = I^2 \cdot R = \frac{U^2}{R}$$
$$W = P \cdot t$$
* Einheiten: $[P] = \text{W}$ (Watt), $[W] = \text{J} = \text{W}\text{s}$ bzw. $\text{kWh}$.

### Kirchhoffsche Gesetze
1. **1. Kirchhoffsches Gesetz (Knotenpunktregel):**
   In jedem Knotenpunkt eines Stromkreises ist die algebraische Summe aller Ströme gleich null:
   $$\sum I_{\text{zu}} = \sum I_{\text{ab}} \quad \Longleftrightarrow \quad \sum_{k=1}^n I_k = 0$$
2. **2. Kirchhoffsches Gesetz (Maschenregel):**
   In jedem geschlossenen Umlauf (Masche) eines Stromkreises ist die algebraische Summe aller Quellenspannungen gleich der Summe aller Spannungsabfälle:
   $$\sum_{k=1}^m U_k = 0$$

### Zusammenschaltung von Widerständen
* **Reihenschaltung (Serienschaltung):**
  $$R_{\text{ges}} = R_1 + R_2 + \dots + R_n$$
  $$I_{\text{ges}} = I_1 = I_2 = \dots = I_n, \quad U_{\text{ges}} = U_1 + U_2 + \dots + U_n$$
  Spannungsteiler: $\frac{U_1}{U_2} = \frac{R_1}{R_2}$ bzw. $U_1 = U_{\text{ges}} \cdot \frac{R_1}{R_{\text{ges}}}$.
* **Parallelschaltung:**
  $$\frac{1}{R_{\text{ges}}} = \frac{1}{R_1} + \frac{1}{R_2} + \dots + \frac{1}{R_n} \quad \left(\text{für 2 Widerstände: } R_{\text{ges}} = \frac{R_1 \cdot R_2}{R_1 + R_2}\right)$$
  $$U_{\text{ges}} = U_1 = U_2 = \dots = U_n, \quad I_{\text{ges}} = I_1 + I_2 + \dots + I_n$$
  Stromteiler: $\frac{I_1}{I_2} = \frac{R_2}{R_1}$ bzw. $I_1 = I_{\text{ges}} \cdot \frac{R_{\text{ges}}}{R_1}$.

### Leiterwiderstand & Temperaturabhängigkeit
$$R = \rho \cdot \frac{l}{A} = \frac{l}{\gamma \cdot A}$$
* $\rho$: spezifischer Widerstand in $\frac{\Omega \cdot \text{mm}^2}{\text{m}}$ (z. B. Kupfer: $\rho \approx 0{,}0178\,\frac{\Omega\cdot\text{mm}^2}{\text{m}}$).
* $\gamma$: elektrische Leitfähigkeit in $\frac{\text{m}}{\Omega \cdot \text{mm}^2} = \frac{\text{MS}}{\text{m}}$ (Kupfer: $\gamma \approx 56\,\frac{\text{m}}{\Omega\cdot\text{mm}^2}$).
* Temperaturformel: $R(\vartheta) = R_{20} \cdot [1 + \alpha_{20} \cdot (\vartheta - 20\,{^\circ}\text{C})]$.

---

## 2. Dreiphasenwechselstrom (Drehstrom)

Im europäischen Niederspannungsnetz:
* Frequenz $f = 50\,\text{Hz}$, Periode $T = 20\,\text{ms}$, Kreisfrequenz $\omega = 2\pi f \approx 314{,}16\,\text{s}^{-1}$.
* Drei sinusförmige Wechselspannungen, jeweils um $120^\circ$ phasenverschoben.
* **Strangspannung:** $U_{\text{Str}} = 230\,\text{V}$ (Spannung zwischen Außenleiter $L_1, L_2, L_3$ und Neutralleiter $N$).
* **Außenleiterspannung (verkettete Spannung):** $U_{\text{L}} = 400\,\text{V}$ (Spannung zwischen zwei Außenleitern, z. B. $L_1\text{-}L_2$).
* **Verkettungsfaktor:** $\sqrt{3} \approx 1{,}732$:
  $$U_{\text{L}} = \sqrt{3} \cdot U_{\text{Str}} = \sqrt{3} \cdot 230\,\text{V} \approx 400\,\text{V}$$

### Sternschaltung ($Y$)
* Die Enden der drei Stränge ($U_2, V_2, W_2$) sind im Sternpunkt zusammengeschaltet.
* Spannungen: $U = \sqrt{3} \cdot U_{\text{Str}}$ ($400\,\text{V}$ Netz $\rightarrow 230\,\text{V}$ am Motorstrang).
* Ströme: $I = I_{\text{Str}}$ (Außenleiterstrom = Strangstrom).

### Dreieckschaltung ($\Delta$)
* Die Stränge sind in Reihe geschaltet ($U_1\text{-}W_2, V_1\text{-}U_2, W_1\text{-}V_2$).
* Spannungen: $U = U_{\text{Str}} = 400\,\text{V}$ (volle Netzspannung liegt an jedem Motorstrang an).
* Ströme: $I = \sqrt{3} \cdot I_{\text{Str}}$.

### Leistungen im symmetrischen Drehstromnetz
* **Scheinleistung:** $S = \sqrt{3} \cdot U \cdot I \quad [\text{VA}]$
* **Wirkleistung:** $P = \sqrt{3} \cdot U \cdot I \cdot \cos\varphi \quad [\text{W}]$
* **Blindleistung:** $Q = \sqrt{3} \cdot U \cdot I \cdot \sin\varphi \quad [\text{var}]$
* **Leistungsfaktor:** $\cos\varphi = \frac{P}{S}$

---

## 3. Schütz- & Steuerungstechnik (DIN EN 60617, DIN EN 81346)

### Kennzeichnung der Betriebsmittel (BMK)
* $Q$: Schaltgeräte für Starkstrom / Leistungsschalter ($Q_1$ = Motorschutzschalter / Hauptschalter).
* $K$: Relais und Schütze ($K_1$ = Netzschütz / Rechtslauf, $K_2$ = Linkslauf / Dreieckschütz, $K_3$ = Sternschütz).
* $F$: Schutzeinrichtungen ($F_0$ = Steuersicherung, $F_1$ = Thermisches Überlastrelais / Bimetall).
* $S$: Schalter, Taster ($S_0$ = Aus-Taster [Öffner], $S_1$ = Ein-Taster Rechts [Schließer], $S_2$ = Ein-Taster Links).
* $M$: Motoren ($M_1$ = Drehstrom-Asynchronmotor).

### Klemmenbezeichnungen nach Norm
* **Hauptkontakte (Schütze):**
  * Zuleitung oben: `1`, `3`, `5`
  * Abgang unten: `2`, `4`, `6`
* **Hilfskontakte (Schütze/Relais):**
  * Schließer (NO): Endziffern `.3` und `.4` (z. B. `13-14`, `23-24`, `33-34`, `43-44`)
  * Öffner (NC): Endziffern `.1` und `.2` (z. B. `11-12`, `21-22`, `31-32`, `41-42`)
* **Thermisches Überlastrelais ($F_1$):**
  * Auslöse-Öffner (in Steuerstromkreis): `95-96`
  * Melde-Schließer (für Störmeldeleuchte): `97-98`
* **Schützspulen:** `A1` (Spulenanfang, Phase) und `A2` (Spulenende, Neutralleiter $N$ oder $0\,\text{V}$).

---

## 4. Die Wendeschützschaltung (Drehsinn-Umkehr)

### Funktionsprinzip Hauptstromkreis
1. Um die Drehrichtung eines Drehstrom-Asynchronmotors umzukehren, muss das Drehfeld der Statorwicklung umgekehrt werden.
2. Dies geschieht durch das **Vertauschen zweier beliebiger Außenleiter** (Standard: $L_1$ und $L_3$ werden getauscht, $L_2$ bleibt durchverbunden).
3. **Schütz $K_1$ (Rechtslauf):**
   * $L_1 \rightarrow 1\text{-}2 \rightarrow U_1$
   * $L_2 \rightarrow 3\text{-}4 \rightarrow V_1$
   * $L_3 \rightarrow 5\text{-}6 \rightarrow W_1$
4. **Schütz $K_2$ (Linkslauf):**
   * $L_1 \rightarrow 1\text{-}2 \rightarrow W_1$ (Phasentausch!)
   * $L_2 \rightarrow 3\text{-}4 \rightarrow V_1$
   * $L_3 \rightarrow 5\text{-}6 \rightarrow U_1$ (Phasentausch!)

### Sicherheits- & Verriegelungskonzept
> [!CAUTION]
> **Kurzschlussgefahr:** Würden beide Schütze $K_1$ und $K_2$ gleichzeitig anziehen, entstünde ein direkter zweipoliger Kurzschluss zwischen den Außenleitern $L_1$ und $L_3$!

Um dies absolut sicher zu verhindern, kommen **drei Verriegelungsarten** zum Einsatz:
1. **Elektrische Schützverriegelung (Pflicht):**
   * In Reihe zur Spule von $K_1$ liegt der Hilfsöffner $K_2$ (`21-22`).
   * In Reihe zur Spule von $K_2$ liegt der Hilfsöffner $K_1$ (`21-22`).
   * Zieht ein Schütz an, öffnet sein Hilfskontakt sofort den Strompfad des Gegenschützes.
2. **Tasterverriegelung (Doppel-Taster):**
   * Die Taster $S_1$ und $S_2$ besitzen je einen Schließer und einen Öffner. Beim Drücken von $S_1$ öffnet mechanisch der Öffner im Pfad von $K_2$.
3. **Mechanische Verriegelung (am Schützblock):**
   * Eine mechanische Wippe zwischen den Schützen blockiert das gleichzeitige Anziehen physisch.

---

## 5. Standard-Rechenbeispiel für Motordaten

### Aufgabe: Motorstrom & Überlastrelais-Einstellung
**Situation:** Ein Drehstrom-Asynchronmotor hat folgende Typenschilddaten:
* Bemessungsleistung $P = 4{,}0\,\text{kW}$
* Bemessungsspannung $U = 400\,\text{V}$ (Dreieckschaltung)
* Wirkungsgrad $\eta = 0{,}86$ ($86\%$)
* Leistungsfaktor $\cos\varphi = 0{,}82$

**Musterrechnung nach Bauplan:**
1. **Gegeben:** $P = 4{,}0\,\text{kW} = 4000\,\text{W}$, $U = 400\,\text{V}$, $\eta = 0{,}86$, $\cos\varphi = 0{,}82$
2. **Gesucht:** Elektrische Wirkleistung $P_{\text{el}}$ und Bemessungsstrom $I_{\text{N}}$ in $\text{A}$.
3. **Formel:**
   $$P_{\text{el}} = \frac{P}{\eta} = \sqrt{3} \cdot U \cdot I_{\text{N}} \cdot \cos\varphi \quad \Longrightarrow \quad I_{\text{N}} = \frac{P}{\sqrt{3} \cdot U \cdot \eta \cdot \cos\varphi}$$
4. **Schritt 1 – Nenner ausrechnen:**
   $$\text{Nenner} = 1{,}732 \cdot 400\,\text{V} \cdot 0{,}86 \cdot 0{,}82 \approx 488{,}56\,\text{V}$$
5. **Schritt 2 – Einsetzen und dividieren:**
   $$I_{\text{N}} = \frac{4000\,\text{W}}{488{,}56\,\text{V}} \approx 8{,}19\,\text{A}$$
6. **Schritt 3 – Einheitenprüfung:**
   $$\frac{\text{W}}{\text{V}} = \frac{\text{V} \cdot \text{A}}{\text{V}} = \text{A} \quad \text{(korrekt)}$$
7. **Ergebnis:** $I_{\text{N}} = 8{,}19\,\text{A}$.
8. **Praxisstufe:** Das thermische Überlastrelais $F_1$ wird im Hauptstromkreis exakt auf den Bemessungsstrom $I_{\text{N}} = 8{,}2\,\text{A}$ eingestellt.
