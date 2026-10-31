/* ============================================================================
   etsym.js — Schaltzeichen nach DIN EN 60617 als SVG-Bausteine
   Vollstaendiger Neubau, 07.08.2026. Ersetzt die gewachsene Fassung mit 24 Zeichen.

   QUELLE
   Jedes Zeichen ist gegen die Zeichentabellen des Westermann-Tabellenbuchs
   ("Technische Dokumentation und Formeln", S. 445-455) und die Schuetzschaltungen
   der Steuerungstechnik (S. 114-116) geprueft. Welche Seite fuer welches Zeichen
   gilt und wie das Zeichen in Worten auszusehen hat, steht Zeichen fuer Zeichen
   im Symbolregister (symbolregister.json, Felder "quelle" und "norm").
   Der norm-Satz ist der eigentliche Pruefmassstab: Wer ein Zeichen abnimmt,
   vergleicht das Bild gegen den Satz, nicht gegen sein Gedaechtnis.

   ----------------------------------------------------------------------------
   DIE MASSTABELLE — ein Satz Grundmasse fuer alle Zeichen
   ----------------------------------------------------------------------------
   Bis hierher hatten Sicherung, Schuetzspule und box drei verschiedene
   Rechteckgroessen, weil sie zu drei verschiedenen Zeitpunkten entstanden.
   Ab jetzt gilt genau diese Tabelle, und zwar fuer jedes Zeichen:

     Zelle                 120 x 60, Mittelachse y = 30
     Anschluesse           (0,30) und (120,30)
     Raster                40  (ein Bauteil ist 3 Rastereinheiten lang)
     Strichstaerke  sw     5
     dritter Anschluss     senkrecht bei x = 60, 40 Einheiten (= 1 Raster) ueber
                           der Achse, also lokal (60,-10)
     Mehrpolige Zeichen    zusaetzliche Anschluesse liegen auf x = 0 bzw. x = 120,
                           genau 40 Einheiten (= 1 Raster) ueber und unter der
                           Achse, also lokal y = -10 und y = 70. Zelle, Bezugspunkt
                           und Drehpunkt bleiben unveraendert; das Zeichen ragt
                           dann oben und unten je 10 Einheiten aus der Zelle —
                           so wie erde schon immer nach unten herausragt.
                           (trafo, optokoppler, opamp, Gatter, flipflopRS,
                            transistoren, wechsler)

     Kreis                 r = 30 um (60,30)      -> Zuleitung 0..30 / 90..120
     Rechteck LAENGS       80 x 32, x 20..100, y 14..46   -> Zuleitung 0..20 / 100..120
     Rechteck QUER         28 x 48, x 46..74,  y  6..54   -> Zuleitung 0..46 / 74..120
     Quadrat               52 x 52, x 34..86,  y  4..56   -> Zuleitung 0..34 / 86..120
     Platten (Kond./Batt.) x 52 und x 68            -> Zuleitung 0..52 / 68..120
                           Kondensator beide 44 lang (y 8..52)
                           Batterie   lang 48 (y 6..54) / kurz 24 (y 18..42)
     Spule                 4 Boegen r = 9, x 24..96, Scheitel y = 21
                           Magnetkern y = 12 (ueber den Boegen, s. u.)
     Diode                 Dreieck x 40..80, y 10..50; Kathodenstrich x 80, y 6..54
     Kontakthebel          (90,30) -> (34,8)      Schliesser: Drehpunkt RECHTS,
                                                  abgehobenes Ende LINKS, offen
                           (30,30) -> (90,8)      Oeffner:    Drehpunkt LINKS,
                                                  abgehobenes Ende RECHTS, auf dem Balken
     Kontaktbalken         x 90, y 8..30 (22 lang, quer zur Zuleitung)  nur Oeffner
     Betaetigung "Druecken" Stiel auf dem Hebel bei x=60 senkrecht bis y=0,
                           Platte y=0 von x 46 bis 74

   DIE BEIDEN KONTAKTE GEHEN IN ENTGEGENGESETZTE RICHTUNGEN AUF. Das ist kein Zufall und
   keine Kosmetik: Im Tabellenbuch (S. 448, und in jeder Schuetzschaltung S. 114/116)
   lehnt der Hebel des Schliessers zur einen, der des Oeffners zur anderen Seite — weil der
   Oeffner sein abgehobenes Ende dorthin bringen muss, wo der Querbalken absteht. Nebeneinander
   gestellt sind die beiden dadurch auf einen Blick zu trennen, auch auf 180 px:
       Schliesser  \  abgehobenes Ende links, davor nur das blanke Leitungsende
       Oeffner     /  abgehobenes Ende rechts, dort der Querbalken, der den Kreis schliesst

   WARUM LAENGS UND QUER ZWEI VERSCHIEDENE RECHTECKE SIND — das ist kein Geschmack,
   das ist die Aussage: Nach DIN EN 60617-4 liegt der Widerstandskoerper mit seiner
   langen Achse LAENGS zum Strompfad. Nach DIN EN 60617-7 liegt das Betaetigungsglied
   (Relais-/Schuetzspule) mit seiner langen Achse QUER dazu; die Anschluesse gehen
   durch die Laengsseiten (Tabellenbuch S. 451, Form 1). In den Schuetzschaltungen
   auf S. 114/116 ist genau das zu sehen: Anlasswiderstaende hochkant, Spulen quer.
   Damit sind Widerstand und Spule auch bei 180 px Kachelbreite auseinanderzuhalten,
   ohne dass eins der beiden Zeichen ein Merkmal traegt, das ihm nicht zusteht.

   ----------------------------------------------------------------------------
   DIE SECHS VERTRAEGE
   ----------------------------------------------------------------------------
   1. Zelle 120 x 60, Anschluesse exakt auf x = 0 und x = 120, halbe Hoehe.
      Ausnahmen (Zeichen ohne zwei Anschluesse) sind unten am Zeichen vermerkt.
   2. Nur Striche, keine Flaechen: fill="none", alles ueber stroke.
      FLAECHEN GIBT ES IN DIESER DATEI NUR DORT, WO DIE FUELLUNG SELBST DAS
      KENNZEICHEN IST. Das sind genau neun Stellen, und jede ist hier benannt:
        knoten()             der Verbindungspunkt IST nach DIN EN 60617-3 ein
                             gefuellter Punkt; ein leerer Kreis bedeutet dort
                             "Anschluss/Klemme" und damit etwas anderes.
        zeitrelaisAbfall     der schwarze Balken am Antrieb ist das Kennzeichen
        zeitrelaisAnzugAbfall  selbst (S. 451).
        vorschaltgeraet      der gefuellte Balken ist das Kennzeichen (S. 449).
        leiterN, leiterPEN,  der Punkt am Leiterkennzeichen (S. 447); ohne Punkt
        leiter3NPE           waere es der Schutzleiter, und das ist ein anderer
                             Leiter mit einer anderen Aufgabe.
        anschlussdose,       der Punkt heisst "hier sind Leiter verbunden"; ohne
        hausanschlusskasten  Punkt ist es die Leerdose (S. 448).
      Alles andere, auch jede Pfeilspitze, ist offen gezeichnet. Damit greifen
      strichInit() und zeichneAuf() auf JEDEM Teil jedes Zeichens.
   3. Farben nur als Variablen. Der Aufrufer uebergibt o.farbe, Vorgabe var(--wid).
      --strom orange, --spannung blau, --magnet rosa, --ok gruen, --gefahr rot,
      --wid grau. Ein Zeichen entscheidet seine Farbe nicht selbst.
   4. Drehung um den linken Anschluss, Muster in _wrap() unveraendert uebernommen.
      Jedes Zeichen wurde zusaetzlich in 90, 180 und 270 Grad angesehen.
   5. Beschriftung an genormter Stelle ueber _LPOS, Systematik unveraendert.
   6. Einheitliche Strichstaerke sw = 5 und die Masstabelle oben.

   ----------------------------------------------------------------------------
   RUECKWAERTSKOMPATIBILITAET
   ----------------------------------------------------------------------------
   Alle 24 Namen der bisherigen Datei gibt es weiter und sie werden gleich
   aufgerufen: widerstand, poti, ntc, kondensator, spule, spuleKern, quelleDC,
   quelleI, quelleAC, batterie, schalter, taster, schliesser, oeffner, sicherung,
   schuetzspule, diode, led, lampe, motor, messer, klemme, erde, box.
   Ebenso die Zusatzfunktionen wire(), knoten(), pfeilI(), pfeilU(), schaltung()
   und die Optionen id, rot, label, wert, farbe, farbeLabel, cls, sw, art, text.
   sym.schalter() traegt weiterhin <path id="<id>_arm"> auf dem Hebel, damit
   bestehende Szenen den Schalter animieren koennen; schliesser und oeffner
   tragen es jetzt ebenfalls.
   GEAENDERT HAT SICH DIE GEOMETRIE mehrerer dieser 24 Zeichen — was genau und
   wogegen, steht in BERICHT.md, Abschnitt 3.
   ============================================================================ */

const SYMW = 120, SYMH = 60, SYMC = 30;   // Zellbreite, Zellhöhe, Mittelachse

function _attr(o) {
  o = o || {};
  return {
    id: o.id ? ` id="${o.id}"` : '',
    cls: ` class="sym${o.cls ? ' ' + o.cls : ''}"`,
    f: o.farbe || 'var(--wid)',
    sw: o.sw || 5
  };
}

/* Wohin die Beschriftung gehört, abhängig von der Drehung.
   Die Beschriftung sitzt in einer NICHT gedrehten Gruppe — sonst steht sie
   im Video auf dem Kopf. Werte sind relativ zum linken Anschluss (0,0). */
const _LPOS = {
  0:   { lx: 60, ly: -46, wx: 60, wy: 58,  an: 'middle' },
  90:  { lx: 48, ly: 52,  wx: 48, wy: 92,  an: 'start'  },
  180: { lx:-60, ly: -46, wx:-60, wy: 58,  an: 'middle' },
  270: { lx: 48, ly: -68, wx: 48, wy: -28, an: 'start'  }
};
function _txt(o, rot) {
  if (!o || (!o.label && !o.wert)) return '';
  const P = _LPOS[rot] || _LPOS[0];
  let s = '';
  if (o.label) s += `<text x="${P.lx}" y="${P.ly}" text-anchor="${P.an}"
    font-family="PlexMono" font-weight="600" font-size="30" stroke="none"
    fill="${o.farbeLabel || o.farbe || 'var(--text)'}">${o.label}</text>`;
  if (o.wert) s += `<text x="${P.wx}" y="${P.wy}" text-anchor="${P.an}"
    font-family="PlexMono" font-weight="500" font-size="27" stroke="none"
    fill="var(--text2)">${o.wert}</text>`;
  return s;
}
/* Die Zelle wird um 30 nach oben geschoben, damit der LINKE ANSCHLUSS genau
   auf (x,y) liegt und die Drehung um genau diesen Punkt geht. Nur so lassen
   sich Bauteile ohne Nachrechnen an Rasterpunkte setzen. */
function _wrap(inner, x, y, o) {
  const a = _attr(o); const rot = (o && o.rot) || 0;
  return `<g${a.id}${a.cls} transform="translate(${x},${y})">
    <g transform="rotate(${rot})" fill="none" stroke="${a.f}" stroke-width="${a.sw}"
       stroke-linecap="round" stroke-linejoin="round">
      <g transform="translate(0,-30)">${inner}</g>
    </g>${_txt(o, rot)}</g>`;
}
const _lead = (a, b) => `<path d="M0 30 H${a} M${b} 30 H120"/>`;
/* Einpolige Zeichen (Installationsplan, Erde, Klemme) haben nur die linke
   Zuleitung — im Installationsschaltplan sitzt das Zeichen am Ende einer Leitung. */
const _lead1 = (a) => `<path d="M0 30 H${a}"/>`;

/* Beschriftung IM Zeichen (Kennbuchstabe im Kreis, Kennzeichen am Rechteck).
   Eigene Funktion, damit die Schriftgroessen an einer Stelle stehen — und damit
   die Schrift AN EINER STELLE gegen die Drehung gesichert ist:
   Diese Texte sitzen INNERHALB der gedrehten Gruppe, weil sie am Zeichen kleben
   (das M gehoert in den Kreis, nicht daneben). Ohne Gegendrehung stuende das M
   eines senkrecht eingebauten Motors auf der Seite und das V eines senkrechten
   Voltmeters auf dem Kopf. Buchstaben in einem Schaltplan stehen aber immer
   aufrecht — deshalb dreht _kb/_km um den eigenen Ankerpunkt zurueck. */
const _gegen = (o, x, y) => `transform="rotate(${-((o && o.rot) || 0)} ${x} ${y})"`;
const _kb = (o, x, y, s, size, anchor) =>
  `<text x="${x}" y="${y}" text-anchor="${anchor || 'middle'}" ${_gegen(o, x, y)}
     font-family="BarlowC" font-weight="700" font-size="${size || 34}" stroke="none"
     fill="${_attr(o).f}">${s}</text>`;
/* Kennzeichen am Rechteck (-t°, +t°, U). Waagerecht UND senkrecht auf den
   Ankerpunkt zentriert: nur so bleibt der Abstand zum Koerper in allen vier
   Drehungen gleich. Ohne dominant-baseline wuchs der Text nur nach oben und lag
   bei rot 180 auf dem Rechteck. */
const _km = (o, x, y, s, size) =>
  `<text x="${x}" y="${y}" text-anchor="middle" dominant-baseline="middle" ${_gegen(o, x, y)}
     font-family="PlexMono" font-weight="600" font-size="${size || 22}" stroke="none"
     fill="${_attr(o).f}">${s}</text>`;

/* Offene Pfeilspitze an (tx,ty), Richtung (dx,dy). Keine Flaeche — Vertrag 2. */
function _spitze(tx, ty, dx, dy, l, b) {
  const n = Math.hypot(dx, dy) || 1; const ux = dx / n, uy = dy / n;
  l = l || 12; b = b || 5.5;
  const bx = tx - ux * l, by = ty - uy * l;
  const px = -uy * b, py = ux * b;
  const r = (v) => Math.round(v * 10) / 10;
  return `<path d="M${r(bx + px)} ${r(by + py)} L${r(tx)} ${r(ty)} L${r(bx - px)} ${r(by - py)}"/>`;
}
/* Vier Spulenboegen, Scheitel nach oben. */
const _wick = `<path d="M24 30 a9 9 0 0 1 18 0 a9 9 0 0 1 18 0 a9 9 0 0 1 18 0 a9 9 0 0 1 18 0"/>`;
/* Schraeger Strich durch das Rechteck: Kennzeichen "inhaerent veraenderbar"
   (Tabellenbuch S. 445). Steht bei NTC, PTC, Varistor. Ohne Pfeilspitze!
   Mit Pfeilspitze bedeutet derselbe Strich "nicht inhaerent" = von aussen
   einstellbar — das ist der einstellbare Widerstand, nicht der Thermistor. */
const _schraeg = `<path d="M14 54 L106 6"/>`;
/* Grundformen */
const _rectL = `<rect x="20" y="14" width="80" height="32"/>`;   // laengs
const _rectQ = `<rect x="46" y="6" width="28" height="48"/>`;    // quer
const _quad  = `<rect x="34" y="4" width="52" height="52"/>`;

const sym = {

  /* ======================= Anschluss, Erde, Funktionseinheit ================ */

  /* Anschluss/Klemme = OFFENER Kreis (S. 447). Gefuellt waere "Verbindung von
     Leitern", also der Knoten — ein anderer Sachverhalt. Einpolig. */
  klemme: (x, y, o) => _wrap(`<circle cx="0" cy="30" r="9"/>`, x, y, o),

  /* Erde: senkrechter Anschluss, drei waagerechte Striche, nach unten kuerzer
     werdend (S. 445). Einpolig, waechst nach unten aus der Zelle heraus. */
  erde: (x, y, o) => _wrap(
    `<path d="M0 30 V54"/><path d="M-30 54 H30"/><path d="M-19 66 H19"/><path d="M-8 78 H8"/>`,
    x, y, o),

  /* Schutzerde: dasselbe Zeichen, aber in einem Kreis (S. 445). */
  schutzerde: (x, y, o) => _wrap(
    `<path d="M0 30 V52"/><circle cx="0" cy="58" r="24"/>
     <path d="M-16 58 H16"/><path d="M-10 66 H10"/><path d="M-4 74 H4"/>`, x, y, o),

  /* Masse/Gehaeuse: ein Balken mit Schraffur (S. 445). Nicht mit Erde
     verwechseln — Masse ist ein Bezugspotential, keine Erdverbindung. */
  masse: (x, y, o) => _wrap(
    `<path d="M0 30 V54"/><path d="M-26 54 H26"/>
     <path d="M-16 54 L-26 68"/><path d="M-2 54 L-12 68"/><path d="M12 54 L2 68"/>`,
    x, y, o),

  /* Betriebsmittel/Komponente/Funktionseinheit, Form 1 = QUADRAT (S. 445).
     Bewusst kein liegendes Rechteck: das ist der Widerstandskoerper. */
  box: (x, y, o) => _wrap(_lead(34, 86) + _quad +
    ((o && o.text) ? _kb(o, 60, 41, o.text, String(o.text).length > 3 ? 22 : 30) : ''),
    x, y, o),

  /* ======================= Widerstaende ==================================== */

  widerstand: (x, y, o) => _wrap(_lead(20, 100) + _rectL, x, y, o),

  /* Widerstand, veraenderbar, allgemein (S. 446): Rechteck mit PFEIL schraeg
     hindurch, ueber beide Ecken hinausragend. Der Pfeil heisst "nicht inhaerent
     veraenderbar" = von aussen einstellbar. Zwei Anschluesse. */
  widerstandEinstellbar: (x, y, o) => _wrap(_lead(20, 100) + _rectL +
    `<path d="M14 54 L102 8"/>` + _spitze(106, 6, 92, -48), x, y, o),

  /* Widerstand mit Schleifkontakt, POTENZIOMETER (S. 446): DREI Anschluesse.
     Der Schleifer ist ein Pfeil, der von aussen senkrecht auf den Koerper zeigt
     und selbst ein Anschluss ist. Ein Zweipol mit Schraegpfeil waere der
     einstellbare Widerstand (widerstandEinstellbar) — das sind zwei Bauteile.
     Dritter Anschluss bei (60,-10), also 1 Raster ueber der Achse. */
  poti: (x, y, o) => _wrap(_lead(20, 100) + _rectL +
    `<path d="M60 -10 V14"/>` + _spitze(60, 14, 0, 24, 10, 5), x, y, o),

  /* Widerstand, einstellbar (Trimmer): Rechteck mit schraegem Strich und dem
     Kennzeichen "trimmbar" — Querstrich am oberen Ende (S. 445). Zwei Anschluesse. */
  trimmer: (x, y, o) => _wrap(_lead(20, 100) + _rectL +
    `<path d="M14 54 L104 7"/><path d="M96 0 L110 12"/>`, x, y, o),

  /* NTC: Rechteck, schraeger Strich (inhaerent veraenderbar) und die
     Temperaturmarkierung MIT MINUS. Der Widerstand faellt mit der Temperatur —
     das Vorzeichen ist die ganze Aussage des Zeichens. */
  ntc: (x, y, o) => _wrap(_lead(20, 100) + _rectL + _schraeg +
    _km(o, 60, -8, '−t°'), x, y, o),

  /* PTC (Kaltleiter): dasselbe mit PLUS. */
  ptc: (x, y, o) => _wrap(_lead(20, 100) + _rectL + _schraeg +
    _km(o, 60, -8, '+t°'), x, y, o),

  /* Varistor/VDR: schraeger Strich und "U" — spannungsabhaengig (S. 446). */
  varistor: (x, y, o) => _wrap(_lead(20, 100) + _rectL + _schraeg +
    _km(o, 60, -8, 'U'), x, y, o),

  /* LDR/Photowiderstand (S. 446, Sensoren): Rechteck mit zwei Lichtpfeilen, die
     AUF das Bauteil zeigen. Kein schraeger Strich — die Pfeile sagen schon,
     wovon der Widerstand abhaengt. */
  ldr: (x, y, o) => _wrap(_lead(20, 100) + _rectL +
    `<path d="M76 -14 L60 2"/>` + _spitze(58, 4, -16, 16) +
    `<path d="M92 -14 L76 2"/>` + _spitze(74, 4, -16, 16), x, y, o),

  /* Heizelement (S. 446): Rechteck mit Querstrichen. */
  heizelement: (x, y, o) => _wrap(_lead(20, 100) + _rectL +
    `<path d="M40 14 V46"/><path d="M60 14 V46"/><path d="M80 14 V46"/>`, x, y, o),

  /* ======================= Kondensatoren =================================== */

  kondensator: (x, y, o) => _wrap(_lead(52, 68) +
    `<path d="M52 8 V52"/><path d="M68 8 V52"/>`, x, y, o),

  /* Gepolter Kondensator, Elko (S. 446): eine gerade Platte (Pluspol, mit +)
     und eine doppelt gezogene Gegenplatte. */
  kondensatorPol: (x, y, o) => _wrap(`<path d="M0 30 H52 M76 30 H120"/>` +
    `<path d="M52 8 V52"/><path d="M68 8 V52"/><path d="M76 8 V52"/>
     <path d="M32 14 H44"/><path d="M38 8 V20"/>`, x, y, o),

  /* Kondensator, veraenderbar (S. 446): Platten mit Pfeil schraeg hindurch. */
  kondensatorVar: (x, y, o) => _wrap(_lead(52, 68) +
    `<path d="M52 8 V52"/><path d="M68 8 V52"/><path d="M28 54 L88 12"/>` +
    _spitze(92, 9, 60, -42), x, y, o),

  /* ======================= Induktivitaeten ================================= */

  spule: (x, y, o) => _wrap(_lead(24, 96) + _wick, x, y, o),

  /* Induktivitaet mit Magnetkern (S. 446): der Kernstrich liegt auf der Seite,
     ZU DER SICH DIE BOEGEN WOELBEN — bei nach oben gewoelbten Boegen also
     darueber. Gegenprobe am Transformator (S. 453): dort woelben sich beide
     Wicklungen zum Kern in der Mitte hin. */
  spuleKern: (x, y, o) => _wrap(_lead(24, 96) + _wick +
    `<path d="M24 12 H96"/>`, x, y, o),

  /* Einphasentransformator mit zwei Wicklungen (S. 453, Form 2).
     VIER Anschluesse, je 1 Raster ueber und unter der Achse:
     (0,-10) und (0,70) primaer, (120,-10) und (120,70) sekundaer.
     Beide Wicklungen woelben sich ZUM Kern in der Mitte hin — dieselbe Regel
     wie bei spuleKern. */
  trafo: (x, y, o) => _wrap(
    `<path d="M0 -10 H38 V0"/><path d="M0 70 H38 V60"/>
     <path d="M120 -10 H82 V0"/><path d="M120 70 H82 V60"/>
     <path d="M38 0 a10 10 0 0 1 0 20 a10 10 0 0 1 0 20 a10 10 0 0 1 0 20"/>
     <path d="M82 0 a10 10 0 0 0 0 20 a10 10 0 0 0 0 20 a10 10 0 0 0 0 20"/>
     <path d="M56 -4 V64"/><path d="M64 -4 V64"/>`, x, y, o),

  /* ======================= Quellen ========================================= */

  /* IDEALE SPANNUNGSQUELLE: Kreis mit DURCHGEHENDEM Laengsstrich von Anschluss
     zu Anschluss. IDEALE STROMQUELLE (quelleI): Strich QUER dazu. Das ist der
     einzige Unterschied zwischen beiden Zeichen und deshalb heilig. Ein
     unterbrochener Laengsstrich ist keins von beidem. */
  quelleDC: (x, y, o) => _wrap(
    `<path d="M0 30 H120"/><circle cx="60" cy="30" r="30"/>`, x, y, o),

  quelleI: (x, y, o) => _wrap(_lead(30, 90) +
    `<circle cx="60" cy="30" r="30"/><path d="M60 12 V48"/>`, x, y, o),

  quelleAC: (x, y, o) => _wrap(_lead(30, 90) +
    `<circle cx="60" cy="30" r="30"/>
     <path d="M42 30 q9 -14 18 0 q9 14 18 0"/>`, x, y, o),

  /* Primaerzelle / Primaerelement / Akkumulator (S. 454): LANGE Platte = Pluspol,
     KURZE Platte = Minuspol, gleiche Strichstaerke. Der Unterschied liegt allein
     in der Laenge — eine dickere kurze Platte waere ein Merkmal zu viel und
     wuerde Vertrag 6 (einheitliche Strichstaerke) brechen.
     Hier steht der Pluspol LINKS. */
  batterie: (x, y, o) => _wrap(_lead(52, 68) +
    `<path d="M52 6 V54"/><path d="M68 18 V42"/>`, x, y, o),

  /* Akkumulator: nach S. 454 dasselbe Zeichen wie die Primaerzelle. Eigener
     Name, damit die Szene sagen kann, was sie meint — die Geometrie ist gleich. */
  akku: (x, y, o) => _wrap(_lead(52, 68) +
    `<path d="M52 6 V54"/><path d="M68 18 V42"/>`, x, y, o),

  /* Batterie aus mehreren Zellen: lang-kurz-lang-kurz. */
  batterieMehrzellig: (x, y, o) => _wrap(_lead(36, 84) +
    `<path d="M36 6 V54"/><path d="M52 18 V42"/>
     <path d="M68 6 V54"/><path d="M84 18 V42"/>`, x, y, o),

  /* Maschine allgemein mit Kennbuchstaben (S. 453): G = Generator. */
  generator: (x, y, o) => _wrap(_lead(30, 90) +
    `<circle cx="60" cy="30" r="30"/>` + _kb(o, 60, 42, 'G', 36), x, y, o),

  /* Fotoelektrischer Generator, Solarzelle (S. 454): Quadrat mit G und dem
     Zeichen der Primaerzelle darin, dazu zwei Lichtpfeile, die darauf zeigen. */
  solarzelle: (x, y, o) => _wrap(_lead(34, 86) + _quad +
    _kb(o, 60, 27, 'G', 26) +
    `<path d="M52 34 V50"/><path d="M64 31 V53"/>` +
    `<path d="M2 4 L24 14"/>` + _spitze(26, 15, 22, 10) +
    `<path d="M2 26 L24 36"/>` + _spitze(26, 37, 22, 10), x, y, o),

  /* ======================= Schaltgeraete =================================== */

  /* Schalter allgemein = Schliesser (S. 448: "Schliesser, Schaltfunktion,
     allgemein Schalter"). Der Hebel traegt id="<id>_arm", damit Szenen ihn
     animieren koennen — das war in der bisherigen Datei so und bleibt so.
     Die beiden gefuellten Punkte der alten Fassung sind raus: ein gefuellter
     Punkt bedeutet nach S. 447 "Verbindung von Leitern" und hat an einer
     Kontaktstelle nichts zu suchen. */
  schalter: (x, y, o) => _wrap(_lead(30, 90) +
    `<path id="${(o && o.id) || 'sw'}_arm" d="M90 30 L34 8"/>`, x, y, o),

  /* Schliesser (Arbeitskontakt, NO): Der Hebel ist RECHTS angelenkt und hebt nach LINKS
     ab; sein freies Ende steht ueber dem blanken Ende der linken Zuleitung, ohne es zu
     beruehren — offen. Kein Querbalken, der gehoert dem Oeffner.
     Die Richtung ist die Gegenrichtung zum Oeffner, und genau daran sind die beiden
     nebeneinander zu trennen (Andre, 07.08.2026: "beim Oeffner geht der Strich in die
     andere Richtung auf"). */
  schliesser: (x, y, o) => _wrap(_lead(30, 90) +
    `<path id="${(o && o.id) || 'sw'}_arm" d="M90 30 L34 8"/>`, x, y, o),

  /* Oeffner (Ruhekontakt, NC): im Ruhezustand GESCHLOSSEN.
     Nach S. 448 und den Schuetzschaltungen S. 114/116 knickt die eine Zuleitung
     am Kontakt um 90 Grad ab — dieser QUER stehende Balken ist der feste
     Kontakt — und der Hebel liegt mit seiner Spitze auf dessen freiem Ende.
     Der Strom laeuft also durch: Zuleitung, Hebel, Balken, Zuleitung.
     Genau darauf beruht die Not-Halt-Kette.
     Der Hebel ist LINKS angelenkt und hebt nach RECHTS ab — die Gegenrichtung zum
     Schliesser —, und dort steht der Querbalken, auf dem er aufliegt. */
  oeffner: (x, y, o) => _wrap(_lead(30, 90) +
    `<path id="${(o && o.id) || 'sw'}_arm" d="M30 30 L90 8"/><path d="M90 8 V30"/>`,
    x, y, o),

  /* Wechsler mit Unterbrechung (S. 448): ein Hebel, zwei feste Kontakte.
     DREI Anschluesse: gemeinsam links (0,30), Oeffner-Seite rechts oben
     (120,-10), Schliesser-Seite rechts auf der Achse (120,30).
     Im Ruhezustand liegt der Hebel am oberen (Oeffner-)Kontakt an. */
  wechsler: (x, y, o) => _wrap(
    `<path d="M0 30 H30"/><path d="M120 30 H90"/><path d="M120 -10 H90"/>
     <path d="M90 -10 V10"/>
     <path id="${(o && o.id) || 'sw'}_arm" d="M30 30 L90 10"/>`, x, y, o),

  /* Taster (Drucktaster, Schliesser): Schliesser mit dem Betaetigungsglied
     "Druecken" (S. 445/451) — Stiel auf dem Hebel, Platte quer darueber.
     Die bisherige Fassung zeichnete stattdessen einen waagerechten Balken
     zwischen den Anschluessen: das ist ein geschlossener Kontakt, also die
     Aussage eines Oeffners. */
  taster: (x, y, o) => _wrap(_lead(30, 90) +
    `<path id="${(o && o.id) || 'sw'}_arm" d="M90 30 L34 8"/>
     <path d="M60 18 V0"/><path d="M46 0 H74"/>`, x, y, o),

  /* Taster mit Oeffner — das Bauteil der Not-Halt-Kette und jeder
     Ausschaltbedingung: gedrueckt trennt er. */
  tasterOeffner: (x, y, o) => _wrap(_lead(30, 90) +
    `<path id="${(o && o.id) || 'sw'}_arm" d="M30 30 L90 8"/><path d="M90 8 V30"/>
     <path d="M60 19 V0"/><path d="M46 0 H74"/>`, x, y, o),

  /* Pilz-Notdrucktaster (S. 451): Oeffner mit Pilzkopf statt flacher Platte.
     Die Kennzeichen "zwangslaeufige Betaetigung" und "Selbsthaltung" der Vorlage
     sind hier NICHT gezeichnet — sie sind bei 180 px Kachelbreite nicht mehr
     aufloesbar. Siehe BERICHT.md, Abschnitt 4. */
  notaus: (x, y, o) => _wrap(_lead(30, 90) +
    `<path id="${(o && o.id) || 'sw'}_arm" d="M30 30 L90 8"/><path d="M90 8 V30"/>
     <path d="M60 19 V4"/><path d="M42 4 a18 18 0 0 1 36 0"/>`, x, y, o),

  /* Grenzschalter/Endschalter, Schliesser (S. 451): Schliesser mit dem
     Betaetigungsglied "mechanisch" — Dreieck (Rolle/Stoessel) am Hebel. */
  grenztaster: (x, y, o) => _wrap(_lead(30, 90) +
    `<path id="${(o && o.id) || 'sw'}_arm" d="M90 30 L34 8"/>
     <path d="M12 18 L36 18 L24 40 Z"/>`, x, y, o),

  /* Trennschalter (S. 451): Schalter mit dem Kennzeichen "Trennschalter-Funktion"
     — ein kurzer Strich quer am festen Kontakt (S. 448). */
  trennschalter: (x, y, o) => _wrap(_lead(30, 90) +
    `<path d="M90 30 L34 8"/><path d="M24 16 V44"/>`, x, y, o),

  /* Leistungsschalter (S. 451): Schalter mit dem Kennzeichen "x". */
  leistungsschalter: (x, y, o) => _wrap(_lead(30, 90) +
    `<path d="M90 30 L34 8"/><path d="M15 21 L33 39"/><path d="M33 21 L15 39"/>`, x, y, o),

  /* Leitungsschutzschalter (S. 451): Schliesser mit dem waagerechten
     Ausloeserpfeil (selbsttaetige Ausloesung durch Ueberstrom). */
  lsSchalter: (x, y, o) => _wrap(_lead(30, 90) +
    `<path d="M90 30 L34 8"/><path d="M14 2 H42"/>` + _spitze(46, 2, 30, 0), x, y, o),

  /* Motorschutz (Motorschutzrelais, thermischer Ausloeser): OEFFNER mit dem
     Kennzeichen "thermische Wirkung" (S. 445) — der gestufte Haken. In den
     Schuetzschaltungen S. 114/116 sitzt genau dieses Zeichen als F4/F7/F8 mit
     den Klemmen 95/96 im Steuerstromkreis. */
  motorschutz: (x, y, o) => _wrap(_lead(30, 90) +
    `<path d="M30 30 L90 8"/><path d="M90 8 V30"/>
     <path d="M26 52 H40 V40 H54 V52 H68"/>`, x, y, o),

  /* Sicherung (S. 452): Rechteck LAENGS mit durchgehendem Strich von Anschluss
     zu Anschluss. Der durchgehende Strich ist das Merkmal, an dem sie bei
     180 px vom leeren Widerstandsrechteck zu unterscheiden ist. */
  sicherung: (x, y, o) => _wrap(_lead(20, 100) + _rectL +
    `<path d="M20 30 H100"/>`, x, y, o),

  /* Schuetz-/Relaisspule = elektromechanischer Antrieb, Form 1 (S. 451):
     SCHLICHTES Rechteck, Kennbuchstabe K bzw. Q. Lange Achse QUER zum
     Strompfad — genau daran unterscheidet es sich vom Widerstand.
     Eine Diagonale gehoert NICHT hinein: die bedeutet "veraenderbar/abhaengig"
     und stammte in der alten Datei erkennbar vom NTC. */
  schuetzspule: (x, y, o) => _wrap(_lead(46, 74) + _rectQ, x, y, o),

  relaisspule: (x, y, o) => _wrap(_lead(46, 74) + _rectQ, x, y, o),

  /* Antrieb mit Ansprechverzoegerung (S. 451): Rechteck mit dem Kennzeichen an
     der Seite, an der die Zuleitung eintritt. */
  zeitrelaisAnzug: (x, y, o) => _wrap(_lead(46, 74) + _rectQ +
    `<path d="M46 40 H74"/><path d="M46 40 L74 54"/><path d="M74 40 L46 54"/>`, x, y, o),

  /* Antrieb mit Rueckfallverzoegerung (S. 451): gefuellter Balken.
     EINE DER ZWEI FLAECHEN IN DIESER DATEI — der schwarze Balken IST das
     Kennzeichen, offen gezeichnet waere es ein anderes. */
  zeitrelaisAbfall: (x, y, o) => _wrap(_lead(46, 74) + _rectQ +
    `<rect x="46" y="40" width="28" height="14" fill="${_attr(o).f}"/>`, x, y, o),

  /* ======================= Installationsschaltzeichen ======================
     DIN EN 60617-11, einpolige Darstellung (S. 448). Der offene Kreis IST der
     Anschluss; das Zeichen sitzt am Ende einer Leitung und hat deshalb nur die
     linke Zuleitung — wie erde und klemme. Die Schaltglieder sind schraege
     Striche mit einem Haekchen am freien Ende. */

  ausschalter: (x, y, o) => _wrap(_lead1(51) +
    `<circle cx="60" cy="30" r="9"/><path d="M66 24 L88 6"/>
     <path d="M88 6 a8 8 0 0 1 8 8"/>`, x, y, o),

  serienschalter: (x, y, o) => _wrap(_lead1(51) +
    `<circle cx="60" cy="30" r="9"/>
     <path d="M66 24 L88 6"/><path d="M88 6 a8 8 0 0 1 8 8"/>
     <path d="M66 36 L88 54"/><path d="M88 54 a8 8 0 0 0 8 -8"/>`, x, y, o),

  wechselschalter: (x, y, o) => _wrap(_lead1(51) +
    `<circle cx="60" cy="30" r="9"/>
     <path d="M66 24 L88 6"/><path d="M88 6 a8 8 0 0 1 8 8"/>
     <path d="M54 36 L32 54"/><path d="M32 54 a8 8 0 0 1 -8 -8"/>`, x, y, o),

  kreuzschalter: (x, y, o) => _wrap(_lead1(51) +
    `<circle cx="60" cy="30" r="9"/>
     <path d="M66 24 L88 6"/><path d="M88 6 a8 8 0 0 1 8 8"/>
     <path d="M66 36 L88 54"/><path d="M88 54 a8 8 0 0 0 8 -8"/>
     <path d="M54 24 L32 6"/><path d="M32 6 a8 8 0 0 0 -8 8"/>
     <path d="M54 36 L32 54"/><path d="M32 54 a8 8 0 0 1 -8 -8"/>`, x, y, o),

  /* Taster im Installationsplan (S. 448): zwei Kreise ineinander. */
  tasterInst: (x, y, o) => _wrap(_lead1(43) +
    `<circle cx="60" cy="30" r="17"/><circle cx="60" cy="30" r="9"/>`, x, y, o),

  /* Schutzkontaktsteckdose (S. 448): Bogen, dessen Scheitel die Zuleitung
     aufnimmt, mit dem Schutzkontakt als Querstrich darueber. */
  steckdose: (x, y, o) => _wrap(_lead1(52) +
    `<path d="M74 8 A22 22 0 0 0 74 52"/><path d="M60 2 V58"/>`, x, y, o),

  /* Dose, allgemein / Leerdose (S. 448): ein Kreis. */
  dose: (x, y, o) => _wrap(_lead1(42) + `<circle cx="60" cy="30" r="18"/>`, x, y, o),

  /* Verteiler, dargestellt mit fuenf Anschluessen (S. 448). */
  verteiler: (x, y, o) => _wrap(_lead1(24) +
    `<rect x="24" y="22" width="72" height="28"/>
     <path d="M34 22 V2"/><path d="M47 22 V2"/><path d="M60 22 V2"/>
     <path d="M73 22 V2"/><path d="M86 22 V2"/>`, x, y, o),

  /* Stromstossschalter (S. 448): Rechteck mit dem Stufenzeichen. */
  stromstossschalter: (x, y, o) => _wrap(_lead(20, 100) + _rectL +
    `<path d="M32 40 H56 V20 H88"/>`, x, y, o),

  /* ======================= Halbleiter ====================================== */

  /* Halbleiterdiode (S. 446): Dreieck OFFEN, Spitze in Durchlassrichtung, davor
     der Kathodenstrich. Die Vorlage zeichnet das Dreieck nicht gefuellt — damit
     erfuellt die Diode auch Vertrag 2 und laesst sich von zeichneAuf() malen. */
  diode: (x, y, o) => _wrap(_lead(40, 80) +
    `<path d="M40 10 L40 50 L80 30 Z"/><path d="M80 6 V54"/>`, x, y, o),

  /* Leuchtdiode (S. 446): Diode mit zwei Pfeilen, die VOM Bauteil weg zeigen. */
  led: (x, y, o) => _wrap(_lead(40, 80) +
    `<path d="M40 10 L40 50 L80 30 Z"/><path d="M80 6 V54"/>
     <path d="M56 6 L76 -12"/>` + _spitze(80, -16, 20, -18) +
    `<path d="M72 6 L92 -12"/>` + _spitze(96, -16, 20, -18), x, y, o),

  /* Fotodiode (S. 446, Sensoren): dieselben Pfeile, aber ZUM Bauteil hin. */
  fotodiode: (x, y, o) => _wrap(_lead(40, 80) +
    `<path d="M40 10 L40 50 L80 30 Z"/><path d="M80 6 V54"/>
     <path d="M80 -16 L60 2"/>` + _spitze(56, 6, -20, 18) +
    `<path d="M96 -16 L76 2"/>` + _spitze(72, 6, -20, 18), x, y, o),

  /* Z-Diode / Durchbruch-Diode (S. 446): Kathodenstrich mit abgewinkeltem Ende. */
  zdiode: (x, y, o) => _wrap(_lead(40, 80) +
    `<path d="M40 10 L40 50 L80 30 Z"/><path d="M92 6 L80 6 V54"/>`, x, y, o),

  /* NPN-Transistor (S. 446): Basisstrich quer, Emitterpfeil zeigt VOM Basisstrich
     weg. DREI Anschluesse: Basis links (0,30), Kollektor und Emitter rechts.
     Kollektor (120,-10), Emitter (120,70) — je 1 Raster ueber und unter der Achse. */
  transistorNPN: (x, y, o) => _wrap(
    `<path d="M0 30 H44"/><path d="M44 6 V54"/>
     <path d="M44 20 L84 -10 H120"/>
     <path d="M44 40 L84 70 H120"/>` + _spitze(80, 67, 40, 30), x, y, o),

  /* PNP-Transistor: derselbe Aufbau, der Emitterpfeil zeigt ZUM Basisstrich. */
  transistorPNP: (x, y, o) => _wrap(
    `<path d="M0 30 H44"/><path d="M44 6 V54"/>
     <path d="M44 20 L84 -10 H120"/>
     <path d="M44 40 L84 70 H120"/>` + _spitze(48, 43, -40, -30), x, y, o),

  /* Thyristortriode (S. 446): Diode mit Steueranschluss (Gate) an der Kathode.
     Dritter Anschluss (Gate) bei (120,70). */
  thyristor: (x, y, o) => _wrap(_lead(40, 80) +
    `<path d="M40 10 L40 50 L80 30 Z"/><path d="M80 6 V54"/>
     <path d="M80 46 L100 70 H120"/>`, x, y, o),

  /* Triac / bidirektionale Thyristortriode (S. 446): zwei gegensinnige Dreiecke
     mit gemeinsamem Querstrich, Gate seitlich. */
  triac: (x, y, o) => _wrap(_lead(34, 86) +
    `<path d="M34 8 L34 52 L60 30 Z"/><path d="M86 8 L86 52 L60 30 Z"/>
     <path d="M60 4 V56"/><path d="M34 44 L14 70 H0"/>`, x, y, o),

  /* Gleichrichter in Brueckenschaltung (S. 454): Raute mit Diode darin. */
  bruecke: (x, y, o) => _wrap(_lead(20, 100) +
    `<path d="M60 -6 L100 30 L60 66 L20 30 Z"/>
     <path d="M46 14 L46 46 L76 30 Z"/><path d="M76 12 V48"/>`, x, y, o),

  /* Verstaerker, allgemein (S. 454, Form 1): Dreieck, Spitze in Signalrichtung. */
  verstaerker: (x, y, o) => _wrap(_lead(30, 96) +
    `<path d="M30 2 L96 30 L30 58 Z"/>`, x, y, o),

  /* Operationsverstaerker: das Verstaerkerdreieck mit zwei Eingaengen.
     Anschluesse: invertierender Eingang (0,-10), nicht invertierender (0,70),
     Ausgang (120,30).
     ACHTUNG: Die Vorlage kennt nur "Verstaerker, allgemein" — die Kennzeichnung
     der Eingaenge mit - und + stammt NICHT aus ihr. Siehe BERICHT.md, Abschnitt 4. */
  opamp: (x, y, o) => _wrap(
    `<path d="M0 -10 H36"/><path d="M0 70 H36"/><path d="M100 30 H120"/>
     <path d="M36 -18 L100 30 L36 78 Z"/>
     <path d="M44 -10 H58"/>
     <path d="M44 70 H58"/><path d="M51 63 V77"/>`, x, y, o),

  /* ======================= Verbraucher und Maschinen ======================= */

  /* Leuchte/Lampe (S. 449/450): Kreis mit Kreuz. */
  lampe: (x, y, o) => _wrap(_lead(30, 90) +
    `<circle cx="60" cy="30" r="30"/><path d="M39 9 L81 51"/><path d="M81 9 L39 51"/>`,
    x, y, o),

  /* Maschine allgemein mit Kennbuchstaben (S. 453): M = Motor. */
  motor: (x, y, o) => _wrap(_lead(30, 90) +
    `<circle cx="60" cy="30" r="30"/>` + _kb(o, 60, 42, 'M', 36), x, y, o),

  /* Drehstrom-Asynchronmotor mit Kaefiglaeufer (S. 453): M und 3~ im Kreis. */
  motor3: (x, y, o) => _wrap(_lead(30, 90) +
    `<circle cx="60" cy="30" r="30"/>` + _kb(o, 60, 26, 'M', 24) +
    _kb(o, 60, 50, '3~', 22), x, y, o),

  /* Horn, Hupe (S. 450): Rechteck mit Trichter. */
  hupe: (x, y, o) => _wrap(_lead(20, 100) +
    `<rect x="20" y="14" width="24" height="32"/>
     <path d="M44 14 L100 2 V58 L44 46"/>`, x, y, o),

  /* Wecker, Klingel (S. 450): Halbkreis mit Fuss. */
  klingel: (x, y, o) => _wrap(_lead(24, 96) +
    `<path d="M24 30 A36 36 0 0 1 96 30"/><path d="M24 30 H96"/>`, x, y, o),

  /* ======================= Messtechnik ===================================== */

  /* Messgeraet, anzeigend (S. 452): Kreis mit dem Kennbuchstaben der Groesse.
     sym.messer(x, y, {art:'V'|'A'|'W'|'Ω'|'Hz'|'cos φ'|'n'|'Θ'}) */
  messer: (x, y, o) => _wrap(_lead(30, 90) +
    `<circle cx="60" cy="30" r="30"/>` +
    _kb(o, 60, 42, (o && o.art) || 'V', ((o && o.art) || 'V').length > 1 ? 24 : 34),
    x, y, o),

  /* Elektrizitaetszaehler (S. 452): Rechteck mit abgeteiltem Kopf und Wh. */
  zaehler: (x, y, o) => _wrap(_lead(20, 100) +
    `<rect x="20" y="4" width="80" height="52"/><path d="M20 20 H100"/>` +
    _kb(o, 60, 44, (o && o.art) || 'Wh', 24), x, y, o),

  /* Oszilloskop (S. 452): Kreis mit Kurvenzug. */
  oszilloskop: (x, y, o) => _wrap(_lead(30, 90) +
    `<circle cx="60" cy="30" r="30"/>
     <path d="M40 42 L52 42 L60 16 L68 42 L80 42"/>`, x, y, o),

  /* ======================= Stromrichter ==================================== */

  /* Gleichrichter (S. 454): Quadrat mit Diagonale, ~ auf der Eingangsseite,
     = auf der Ausgangsseite. */
  gleichrichter: (x, y, o) => _wrap(_lead(34, 86) + _quad +
    `<path d="M34 56 L86 4"/><path d="M39 18 q5 -7 10 0 q5 7 10 0"/>
     <path d="M63 40 H81"/><path d="M63 49 H81"/>`, x, y, o),

  /* Wechselrichter (S. 454): dasselbe Quadrat, Kennzeichen vertauscht. */
  wechselrichter: (x, y, o) => _wrap(_lead(34, 86) + _quad +
    `<path d="M34 56 L86 4"/><path d="M39 13 H57"/><path d="M39 22 H57"/>
     <path d="M61 44 q5 -7 10 0 q5 7 10 0"/>`, x, y, o),

  /* ======================= Ueberspannungsschutz ============================ */

  /* Ueberspannungsableiter (S. 452): Rechteck laengs mit Pfeil nach innen. */
  ueberspannungsableiter: (x, y, o) => _wrap(_lead(20, 100) + _rectL +
    `<path d="M34 30 H62"/>` + _spitze(72, 30, 30, 0), x, y, o),

  /* Funkenstrecke (S. 452): zwei Elektroden, die sich gegenueberstehen. */
  funkenstrecke: (x, y, o) => _wrap(
    `<path d="M0 30 H42"/>` + _spitze(52, 30, 30, 0) +
    `<path d="M120 30 H78"/>` + _spitze(68, 30, -30, 0), x, y, o),

  /* Antenne, allgemein (S. 449): Stab mit zwei schraegen Aesten. Einpolig. */
  antenne: (x, y, o) => _wrap(_lead1(60) +
    `<path d="M60 30 V6"/><path d="M60 6 L34 -20"/><path d="M60 6 L86 -20"/>`, x, y, o),

  /* ======================= Binaere Elemente (Logik) ========================
     DIN EN 60617-12. IN DER VORLAGE NICHT ENTHALTEN — die Referenzmappe deckt
     -2, -3, -4, -5, -6, -7, -8, -9, -10 und -11 ab, aber nicht -12.
     Gezeichnet ist deshalb die Rechteckform mit Kennzeichen im Kopf, so wie sie
     in jedem deutschen Lehrbuch und in KOP/FUP steht. Steht als offene Frage in
     BERICHT.md, Abschnitt 4.
     Anschluesse: Eingang A (0,-10), Eingang B (0,70), Ausgang (120,30). */
  gatterUND: (x, y, o) => _wrap(
    `<path d="M0 -10 H40"/><path d="M0 70 H40"/><path d="M96 30 H120"/>
     <rect x="40" y="-14" width="56" height="88"/>` + _kb(o, 68, 42, '&amp;', 34), x, y, o),

  gatterODER: (x, y, o) => _wrap(
    `<path d="M0 -10 H40"/><path d="M0 70 H40"/><path d="M96 30 H120"/>
     <rect x="40" y="-14" width="56" height="88"/>` + _kb(o, 68, 41, '≥1', 30), x, y, o),

  gatterNICHT: (x, y, o) => _wrap(
    `<path d="M0 30 H40"/><path d="M108 30 H120"/>
     <rect x="40" y="-2" width="56" height="64"/><circle cx="102" cy="30" r="6"/>` +
    _kb(o, 68, 42, '1', 34), x, y, o),

  gatterNAND: (x, y, o) => _wrap(
    `<path d="M0 -10 H40"/><path d="M0 70 H40"/><path d="M108 30 H120"/>
     <rect x="40" y="-14" width="56" height="88"/><circle cx="102" cy="30" r="6"/>` +
    _kb(o, 68, 42, '&amp;', 34), x, y, o),

  gatterNOR: (x, y, o) => _wrap(
    `<path d="M0 -10 H40"/><path d="M0 70 H40"/><path d="M108 30 H120"/>
     <rect x="40" y="-14" width="56" height="88"/><circle cx="102" cy="30" r="6"/>` +
    _kb(o, 68, 41, '≥1', 30), x, y, o),

  gatterXOR: (x, y, o) => _wrap(
    `<path d="M0 -10 H40"/><path d="M0 70 H40"/><path d="M96 30 H120"/>
     <rect x="40" y="-14" width="56" height="88"/>` + _kb(o, 68, 41, '=1', 30), x, y, o),

  /* ============ Ergaenzungen aus S. 454, S. 445 und S. 455 =================
     Achter Schritt, 07.08.2026. */

  /* --- Vierpole und Signalquellen (S. 454, DIN EN 60617-9) --- */

  /* Filter, allgemein (S. 454): Quadrat mit einer Sinuslinie.
     Tiefpass, Hochpass, Bandpass und Bandsperre unterscheiden sich davon NUR
     dadurch, welche der uebereinanderliegenden Wellen durchgestrichen ist. Genau
     das ist im Scan nicht sicher zu lesen, und eine Verwechslung machte aus einem
     Tiefpass einen Hochpass — deshalb sind sie nicht gezeichnet, siehe BERICHT.md. */
  filter: (x, y, o) => _wrap(_lead(34, 86) + _quad +
    `<path d="M42 30 q6 -10 12 0 q6 10 12 0 q6 -10 12 0"/>`, x, y, o),

  /* Daempfungsglied, fest eingestellt (S. 454): Quadrat mit A. */
  daempfungsglied: (x, y, o) => _wrap(_lead(34, 86) + _quad +
    _kb(o, 60, 40, 'A', 28), x, y, o),

  /* Daempfungsglied, veraenderbar (S. 454): dasselbe mit dem Pfeil
     "nicht inhaerent veraenderbar" schraeg hindurch. */
  daempfungsgliedVar: (x, y, o) => _wrap(_lead(34, 86) + _quad +
    _kb(o, 60, 42, 'A', 26) + `<path d="M28 58 L88 2"/>` + _spitze(92, -2, 60, -56),
    x, y, o),

  /* Phasenschieber (S. 454): Quadrat mit dem Formelzeichen des Phasenwinkels. */
  phasenschieber: (x, y, o) => _wrap(_lead(34, 86) + _quad +
    _kb(o, 60, 40, '&#966;', 30), x, y, o),

  /* Sinusgenerator (S. 454): Quadrat mit G und der Sinuslinie darunter. */
  sinusgenerator: (x, y, o) => _wrap(_lead(34, 86) + _quad +
    _kb(o, 60, 26, 'G', 24) +
    `<path d="M44 42 q6 -10 12 0 q6 10 12 0"/>`, x, y, o),

  /* Pulsgenerator (S. 454): Quadrat mit G und dem Rechtecksignal darunter. */
  pulsgenerator: (x, y, o) => _wrap(_lead(34, 86) + _quad +
    _kb(o, 60, 26, 'G', 24) +
    `<path d="M42 46 H52 V36 H66 V46 H78"/>`, x, y, o),

  /* Spannungskonstanthalter (S. 454): Quadrat mit U const. */
  spannungskonstanthalter: (x, y, o) => _wrap(_lead(34, 86) + _quad +
    _kb(o, 60, 28, 'U', 24) + _kb(o, 60, 48, 'const', 16), x, y, o),

  /* Gleichstromumrichter (S. 454): Quadrat mit Diagonale, auf beiden Seiten das
     Gleichstromzeichen. Beim Wechselstromumrichter steht beidseitig die Welle. */
  umrichterDC: (x, y, o) => _wrap(_lead(34, 86) + _quad +
    `<path d="M34 56 L86 4"/>
     <path d="M40 14 H58"/><path d="M40 22 H58"/>
     <path d="M62 40 H80"/><path d="M62 48 H80"/>`, x, y, o),

  umrichterAC: (x, y, o) => _wrap(_lead(34, 86) + _quad +
    `<path d="M34 56 L86 4"/>
     <path d="M39 18 q5 -7 10 0 q5 7 10 0"/>
     <path d="M61 44 q5 -7 10 0 q5 7 10 0"/>`, x, y, o),

  /* Frequenzteiler (S. 454): Quadrat mit Diagonale, oben f, unten f/n. */
  frequenzteiler: (x, y, o) => _wrap(_lead(34, 86) + _quad +
    `<path d="M34 56 L86 4"/>` + _kb(o, 46, 26, 'f', 22) + _kb(o, 72, 50, 'f/n', 18),
    x, y, o),

  /* --- Symbolelemente und Kennzeichen (S. 445, DIN EN 60617-2) ---
     Die Antriebsarten dieser Seite (Druecken, Drehen, Ziehen, Schluessel, Pedal,
     Rolle, Nocken, Motor) sind KEINE eigenen Zeichen, sondern Zusaetze: sie
     stecken bereits in taster, notaus, grenztaster, schluesselschalter und
     schaltuhr. Hier stehen nur die Kennzeichen, die auch allein gebraucht werden. */

  /* Gleichstrom (S. 445): durchgezogener Strich mit gestricheltem darunter. */
  gleichstrom: (x, y, o) => _wrap(
    `<path d="M28 24 H92"/><path d="M28 38 H40 M52 38 H68 M80 38 H92"/>`, x, y, o),

  /* Wechselstrom (S. 445): eine Sinuslinie. */
  wechselstrom: (x, y, o) => _wrap(
    `<path d="M26 30 q9 -16 18 0 q9 16 18 0 q9 -16 18 0 q9 16 18 0"/>`, x, y, o),

  /* Drehstrom, Dreiphasensystem (S. 445): drei Striche und die Sinuslinie. */
  drehstrom: (x, y, o) => _wrap(
    `<path d="M14 38 L22 20"/><path d="M24 38 L32 20"/><path d="M34 38 L42 20"/>
     <path d="M52 30 q9 -16 18 0 q9 16 18 0"/>`, x, y, o),

  /* Schirm, Abschirmung (S. 445): gestrichelte Umrandung, nach einer Seite offen. */
  schirm: (x, y, o) => _wrap(
    `<path d="M20 54 V10 H100 V54" stroke-dasharray="9 7"/>`, x, y, o),

  /* Wirkverbindung, mechanisch (S. 445, Form 1): gestrichelte Linie. Sie sagt,
     dass zwei Zeichen zusammengehoeren, ohne dass Strom fliesst — genau das, was
     der Kontaktspiegel eines Schuetzes zeigt. */
  wirkverbindung: (x, y, o) => _wrap(
    `<path d="M0 30 H120" stroke-dasharray="10 8"/>`, x, y, o),

  /* Begrenzungslinie einer Gruppe zusammengehoeriger Objekte (S. 445):
     Strichpunktlinie. */
  begrenzungslinie: (x, y, o) => _wrap(
    `<path d="M0 30 H120" stroke-dasharray="22 7 3 7"/>`, x, y, o),

  /* Huelle, Gehaeuse, Kolben, Kessel (S. 445, Form 2). */
  huelle: (x, y, o) => _wrap(_lead(24, 96) +
    `<rect x="24" y="12" width="72" height="36" rx="18"/>`, x, y, o),

  /* --- Nachrichtentechnik (S. 455, DIN EN 60617-10) --- */

  /* Lichtwellenleiter, LWL (S. 447/455): die Leitung mit einem Kreis, in dem ein
     schraeger Strich steht. */
  lwl: (x, y, o) => _wrap(
    `<path d="M0 30 H46"/><path d="M74 30 H120"/><circle cx="60" cy="30" r="14"/>
     <path d="M52 40 L68 20"/>`, x, y, o),

  /* Koaxialleiter (S. 447/455): die Leitung mit einem Kreis darauf. */
  koaxleiter: (x, y, o) => _wrap(
    `<path d="M0 30 H46"/><path d="M74 30 H120"/><circle cx="60" cy="30" r="14"/>`,
    x, y, o),

  /* ======================= Ergaenzungen aus S. 450 =========================
     Melde- und Signaleinrichtungen (DIN EN 60617-8). Siebter Schritt, 07.08.2026. */

  /* Uhr, allgemein / Nebenuhr (S. 450): Kreis mit Zeigern. */
  uhr: (x, y, o) => _wrap(_lead(30, 90) +
    `<circle cx="60" cy="30" r="30"/><path d="M60 12 V30 H80"/>`, x, y, o),

  /* Temperaturmelder (S. 450): Rechteck mit dem Formelzeichen der Temperatur. */
  temperaturmelder: (x, y, o) => _wrap(_lead(20, 100) + _rectL +
    _kb(o, 60, 38, '&#977;', 26), x, y, o),

  /* Rauchmelder, selbsttaetig, lichtabhaengiges Prinzip (S. 450): Melderkasten mit
     zwei Lichtpfeilen, die HINEIN zeigen — der Rauch stoert den Lichtstrahl. */
  rauchmelder: (x, y, o) => _wrap(_lead1(24) +
    `<rect x="24" y="6" width="60" height="48"/>
     <path d="M34 16 L52 30"/>` + _spitze(56, 33, 18, 14, 11, 5) +
    `<path d="M52 14 L66 32"/>` + _spitze(69, 36, 14, 18, 11, 5), x, y, o),

  /* Brandmelder (S. 450): Melderkasten mit dem Meldekontakt darin. */
  brandmelder: (x, y, o) => _wrap(_lead1(20) +
    `<rect x="20" y="4" width="64" height="52"/>
     <rect x="32" y="18" width="40" height="24"/>
     <circle cx="52" cy="30" r="6"/><path d="M84 30 H104"/>`, x, y, o),

  /* Lichtsender, Gleichlichtsender (S. 450): Kasten mit dem Strahlungszeichen und
     der Leuchte. Zusammen mit dem Lichtempfaenger die Lichtschranke. */
  lichtsender: (x, y, o) => _wrap(_lead1(20) +
    `<rect x="20" y="4" width="60" height="52"/>
     <path d="M30 24 L44 12"/>` + _spitze(48, 9, 14, -12, 10, 4.5) +
    `<path d="M44 24 L58 12"/>` + _spitze(62, 9, 14, -12, 10, 4.5) +
    `<circle cx="50" cy="42" r="10"/><path d="M43 35 L57 49"/><path d="M57 35 L43 49"/>`,
    x, y, o),

  /* Lichtempfaenger mit Kontaktausgang (S. 450): Kasten mit dem Strahlungszeichen,
     dem Verstaerkerdreieck und einem Schaltglied. */
  lichtempfaenger: (x, y, o) => _wrap(
    `<rect x="20" y="4" width="60" height="52"/><path d="M80 30 H120"/>
     <path d="M44 22 L30 10"/>` + _spitze(46, 24, 14, 12, 10, 4.5) +
    `<path d="M58 22 L44 10"/>` + _spitze(60, 24, 14, 12, 10, 4.5) +
    `<path d="M60 12 L74 22 L60 32 Z"/><path d="M28 48 L46 40"/><path d="M52 44 H70"/>`,
    x, y, o),

  /* Sirene (S. 450): spitzer Bogen. Der Gong hat zwei senkrechte Striche, die
     Klingel eine gerade Grundlinie — die drei nicht verwechseln. */
  sirene: (x, y, o) => _wrap(_lead(24, 96) +
    `<path d="M24 30 L60 -6 L96 30"/><path d="M24 30 H96"/>`, x, y, o),

  /* Gong, Einschlagwecker (S. 450): Halbkreis mit zwei senkrechten Strichen. */
  gong: (x, y, o) => _wrap(_lead(24, 96) +
    `<path d="M24 30 A36 36 0 0 1 96 30"/><path d="M24 30 H96"/>
     <path d="M48 30 V-2"/><path d="M72 30 V-2"/>`, x, y, o),

  /* Fernsprecher, allgemein (S. 450): Gehaeuse mit dem Hoerer als Bogen darauf. */
  fernsprecher: (x, y, o) => _wrap(_lead1(24) +
    `<path d="M24 54 H96 V30 A36 36 0 0 0 24 30 Z"/>`, x, y, o),

  /* ======================= Ergaenzungen aus S. 449 =========================
     Leuchten und Antennen (DIN EN 60617-11). Sechster Schritt, 07.08.2026. */

  /* Leuchte fuer Leuchtstofflampe (S. 449): ein Stab mit einer kurzen Kappe an
     jedem Ende. Mehrere Lampen werden durch mehrere Staebe dargestellt. */
  leuchtstofflampe: (x, y, o) => _wrap(_lead(20, 100) +
    `<path d="M20 14 V46"/><path d="M100 14 V46"/><path d="M20 30 H100"/>`, x, y, o),

  leuchtstofflampe3: (x, y, o) => _wrap(_lead(20, 100) +
    `<path d="M20 10 V50"/><path d="M100 10 V50"/>
     <path d="M20 18 H100"/><path d="M20 30 H100"/><path d="M20 42 H100"/>`, x, y, o),

  /* Leuchtenauslass, dargestellt mit Leitung (S. 449): die Leitung endet in einem
     Kreuz — hier kommt eine Leuchte hin, gezeichnet ist sie nicht. */
  leuchtenauslass: (x, y, o) => _wrap(_lead1(44) +
    `<path d="M44 14 L76 46"/><path d="M76 14 L44 46"/>`, x, y, o),

  /* Scheinwerfer, allgemein (S. 449): die Leuchte mit einem Bogen davor —
     das Licht ist gerichtet. */
  scheinwerfer: (x, y, o) => _wrap(_lead1(30) +
    `<circle cx="60" cy="30" r="26"/><path d="M42 12 L78 48"/><path d="M78 12 L42 48"/>
     <path d="M30 2 A34 34 0 0 0 30 58"/>`, x, y, o),

  /* Punktleuchte (S. 449): Scheinwerfer mit zwei PARALLELEN Strahlpfeilen —
     gebuendeltes Licht. Bei der Flutlichtleuchte laufen die Pfeile auseinander. */
  punktleuchte: (x, y, o) => _wrap(_lead1(30) +
    `<circle cx="60" cy="30" r="26"/><path d="M42 12 L78 48"/><path d="M78 12 L42 48"/>
     <path d="M30 2 A34 34 0 0 0 30 58"/><path d="M90 22 H106"/><path d="M90 38 H106"/>` +
    _spitze(112, 22, 20, 0, 10, 5) + _spitze(112, 38, 20, 0, 10, 5), x, y, o),

  /* Flutlichtleuchte (S. 449): Scheinwerfer mit zwei AUSEINANDERLAUFENDEN
     Strahlpfeilen — breit streuendes Licht. */
  flutlichtleuchte: (x, y, o) => _wrap(_lead1(30) +
    `<circle cx="60" cy="30" r="26"/><path d="M42 12 L78 48"/><path d="M78 12 L42 48"/>
     <path d="M30 2 A34 34 0 0 0 30 58"/>
     <path d="M86 20 L102 4"/><path d="M86 40 L102 56"/>` +
    _spitze(106, 0, 16, -16, 10, 5) + _spitze(106, 60, 16, 16, 10, 5), x, y, o),

  /* Leuchte fuer Entladungslampe (S. 449): die Huelle Form 2 (Rechteck mit
     runden Enden) mit einem Kreuz darin. */
  entladungslampe: (x, y, o) => _wrap(_lead(24, 96) +
    `<rect x="24" y="14" width="72" height="32" rx="16"/>
     <path d="M50 22 L70 38"/><path d="M70 22 L50 38"/>`, x, y, o),

  /* Vorschaltgeraet fuer Entladungslampen (S. 449): Rechteck mit einem gefuellten
     Balken. Der gefuellte Balken IST das Kennzeichen. */
  vorschaltgeraet: (x, y, o) => _wrap(_lead(24, 96) +
    `<rect x="24" y="12" width="72" height="36"/>
     <rect x="38" y="24" width="44" height="12" fill="${_attr(o).f}"/>`, x, y, o),

  /* Ventilator, dargestellt mit Leitung (S. 449): Rechteck mit dem Zeichen der
     Endlosschleife. */
  ventilator: (x, y, o) => _wrap(_lead1(24) +
    `<rect x="24" y="10" width="72" height="40"/>
     <circle cx="50" cy="30" r="11"/><circle cx="70" cy="30" r="11"/>`, x, y, o),

  /* Parabolantenne (S. 449): der Reflektorbogen mit dem Erreger davor. */
  parabolantenne: (x, y, o) => _wrap(_lead1(30) +
    `<rect x="30" y="20" width="18" height="20"/><path d="M48 30 H62"/>
     <path d="M96 -6 A46 46 0 0 0 96 66"/>`, x, y, o),

  /* ======================= Ergaenzungen aus S. 448 =========================
     Schaltglieder mit Verzoegerung und Geraete des Installationsplans.
     Nachgetragen am 07.08.2026, fuenfter Schritt.

     DAS VERZOEGERUNGSKENNZEICHEN (S. 448) ist ein Halbkreis am Ende eines
     Querstrichs auf dem Hebel — der "Fallschirm". Seine OEFFNUNGSRICHTUNG ist
     die ganze Aussage:
        Woelbung VOM Hebel weg  = anzugverzoegert (verzoegert beim Betaetigen)
        Woelbung ZUM Hebel hin   = abfallverzoegert (verzoegert beim Loslassen)
     Wer die beiden vertauscht, dreht die Zeitfunktion einer Steuerung um. */

  schliesserAnzug: (x, y, o) => _wrap(_lead(30, 90) +
    `<path id="${(o && o.id) || 'sw'}_arm" d="M90 30 L34 8"/>
     <path d="M62 19 V50"/><path d="M48 44 A14 14 0 0 0 76 44"/>`, x, y, o),

  schliesserAbfall: (x, y, o) => _wrap(_lead(30, 90) +
    `<path id="${(o && o.id) || 'sw'}_arm" d="M90 30 L34 8"/>
     <path d="M62 19 V50"/><path d="M48 44 A14 14 0 0 1 76 44"/>`, x, y, o),

  oeffnerAnzug: (x, y, o) => _wrap(_lead(30, 90) +
    `<path id="${(o && o.id) || 'sw'}_arm" d="M30 30 L90 8"/><path d="M90 8 V30"/>
     <path d="M60 19 V50"/><path d="M46 44 A14 14 0 0 0 74 44"/>`, x, y, o),

  oeffnerAbfall: (x, y, o) => _wrap(_lead(30, 90) +
    `<path id="${(o && o.id) || 'sw'}_arm" d="M30 30 L90 8"/><path d="M90 8 V30"/>
     <path d="M60 19 V50"/><path d="M46 44 A14 14 0 0 1 74 44"/>`, x, y, o),

  /* Wechsler mit Mittelstellung "Aus" (S. 448): drei feste Stellungen, in der
     mittleren ist der Kreis offen. Der Hebel steht senkrecht zwischen beiden
     Kontakten und beruehrt keinen. */
  wechslerMittelstellung: (x, y, o) => _wrap(
    `<path d="M0 30 H30"/><path d="M120 30 H90"/><path d="M120 -10 H90"/>
     <path id="${(o && o.id) || 'sw'}_arm" d="M30 30 L84 10"/>
     <circle cx="30" cy="30" r="6"/>`, x, y, o),

  /* --- Geraete des Installationsplans (S. 448) --- */

  /* Zeitrelais (S. 448): Rechteck mit dem Kennbuchstaben t. */
  zeitrelaisInst: (x, y, o) => _wrap(_lead(20, 100) + _rectL +
    _kb(o, 60, 38, 't', 26), x, y, o),

  /* Schaltuhr (S. 448): Rechteck mit einem Uhrzeichen und einem Schaltglied. */
  schaltuhr: (x, y, o) => _wrap(_lead(20, 100) + _rectL +
    `<circle cx="40" cy="30" r="11"/><path d="M40 22 V30 H46"/>
     <path d="M60 38 L84 24"/>`, x, y, o),

  /* Daemmerungsschalter (S. 448): Rechteck mit dem Kennzeichen der
     Beleuchtungsstaerke und einem Schaltglied. */
  daemmerungsschalter: (x, y, o) => _wrap(_lead(20, 100) + _rectL +
    _km(o, 38, 24, 'L', 22) + `<path d="M48 19 L58 29"/><path d="M58 19 L48 29"/>` +
    _km(o, 70, 24, '<', 22) + `<path d="M32 42 H60"/><path d="M66 46 L88 34"/>`, x, y, o),

  /* Schluesselschalter, Waechtermelder (S. 448): Rechteck mit dem Schluesselloch. */
  schluesselschalter: (x, y, o) => _wrap(_lead(20, 100) + _rectL +
    `<circle cx="60" cy="24" r="7"/><path d="M56 40 L60 29 L64 40 Z"/>`, x, y, o),

  /* Anschlussdose, Verbindungsdose (S. 448): Kreis mit einem Punkt darin —
     die Leerdose (dose) hat keinen Punkt. */
  anschlussdose: (x, y, o) => _wrap(_lead1(42) +
    `<circle cx="60" cy="30" r="18"/>
     <circle cx="60" cy="30" r="5" fill="${_attr(o).f}"/>`, x, y, o),

  /* Hausanschlusskasten (S. 448), allgemein dargestellt mit Leitung. */
  hausanschlusskasten: (x, y, o) => _wrap(_lead1(34) +
    `<rect x="34" y="8" width="52" height="44"/>
     <circle cx="60" cy="30" r="6" fill="${_attr(o).f}"/>
     <path d="M60 8 V-8"/>`, x, y, o),

  /* Dimmer (S. 448): Installationsschalter mit einem Querstrich am Schaltglied. */
  dimmer: (x, y, o) => _wrap(_lead1(51) +
    `<circle cx="60" cy="30" r="9"/><path d="M66 24 L88 6"/>
     <path d="M88 6 a8 8 0 0 1 8 8"/><path d="M70 6 L84 24"/>`, x, y, o),

  /* Zeitschalter, einpolig (S. 448): Installationsschalter mit dem Kennbuchstaben t. */
  zeitschalter: (x, y, o) => _wrap(_lead1(51) +
    `<circle cx="60" cy="30" r="9"/><path d="M66 24 L88 6"/>
     <path d="M88 6 a8 8 0 0 1 8 8"/>` + _km(o, 84, 34, 't', 24), x, y, o),

  /* Taster mit Leuchte (S. 448): Kreis mit Kreuz — der Taster ohne Leuchte ist
     der Doppelkreis (tasterInst). */
  tasterLeuchte: (x, y, o) => _wrap(_lead1(43) +
    `<circle cx="60" cy="30" r="17"/>
     <path d="M48 18 L72 42"/><path d="M72 18 L48 42"/>`, x, y, o),

  /* Schalter mit Kontrollleuchte (S. 448): wie der Ausschalter, aber der
     Anschlusskreis traegt ein Kreuz. */
  schalterKontrollleuchte: (x, y, o) => _wrap(_lead1(48) +
    `<circle cx="60" cy="30" r="12"/><path d="M52 22 L68 38"/><path d="M68 22 L52 38"/>
     <path d="M69 22 L88 6"/><path d="M88 6 a8 8 0 0 1 8 8"/>`, x, y, o),

  /* ======================= Ergaenzungen aus S. 453 =========================
     Erzeugung und Umwandlung elektrischer Energie (DIN EN 60617-6).
     Nachgetragen am 07.08.2026, vierter Schritt. */

  /* Maschine, allgemein (S. 453): Kreis mit dem Kennbuchstaben der Maschinenart
     und darunter der Stromart.
     sym.maschine(x, y, {art:'GS', strom:'3~'})
       C = Umformer, G = Generator, GS = Synchrongenerator, M = Motor,
       MG = als Generator oder Motor nutzbar, MS = Synchronmotor.
     Der Buchstabe ALLEIN sagt, was die Maschine ist — nichts an der Zeichnung. */
  maschine: (x, y, o) => _wrap(_lead(30, 90) +
    `<circle cx="60" cy="30" r="30"/>` +
    _kb(o, 60, (o && o.strom) ? 26 : 42, (o && o.art) || 'M',
        ((o && o.art) || 'M').length > 1 ? 24 : 34) +
    ((o && o.strom) ? _kb(o, 60, 50, o.strom, 22) : ''), x, y, o),

  /* Gleichstrommotor (S. 453): Kennbuchstabe M und darunter das Zeichen fuer
     Gleichstrom (zwei waagerechte Striche). */
  motorDC: (x, y, o) => _wrap(_lead(30, 90) +
    `<circle cx="60" cy="30" r="30"/>` + _kb(o, 60, 26, 'M', 26) +
    `<path d="M48 38 H72"/><path d="M48 46 H72"/>`, x, y, o),

  /* Einphasen-Wechselstrommotor (S. 453): M mit 1~ darunter. */
  motorAC1: (x, y, o) => _wrap(_lead(30, 90) +
    `<circle cx="60" cy="30" r="30"/>` + _kb(o, 60, 26, 'M', 26) +
    _kb(o, 60, 50, '1~', 22), x, y, o),

  /* Schrittmotor (S. 453): M mit dem Stufenzeichen darunter — er dreht in
     Schritten, nicht stetig. */
  schrittmotor: (x, y, o) => _wrap(_lead(30, 90) +
    `<circle cx="60" cy="30" r="30"/>` + _kb(o, 60, 26, 'M', 26) +
    `<path d="M44 48 H56 V36 H68 V48 H78"/>`, x, y, o),

  /* Linearmotor (S. 453): M mit einer geraden Sehne im unteren Teil des Kreises —
     die Bewegung laeuft geradlinig, nicht rund. */
  linearmotor: (x, y, o) => _wrap(_lead(30, 90) +
    `<circle cx="60" cy="30" r="30"/>` + _kb(o, 60, 34, 'M', 28) +
    `<path d="M33 44 H87"/>`, x, y, o),

  /* Drehstrom-Asynchronmotor mit Schleifringlaeufer (S. 453): wie der
     Kaefiglaeufer, aber mit den drei herausgefuehrten Laeuferanschluessen. */
  motorSchleifring: (x, y, o) => _wrap(_lead(30, 90) +
    `<circle cx="60" cy="30" r="30"/>` + _kb(o, 60, 26, 'M', 24) +
    _kb(o, 60, 50, '3~', 20) +
    `<path d="M42 56 V72"/><path d="M60 60 V72"/><path d="M78 56 V72"/>`, x, y, o),

  /* Kennzeichen der Schaltungsart (S. 453). Das sind KEINE Bauteile, sondern
     Kennzeichen: sie stehen neben oder in einem Maschinen- bzw. Trafozeichen und
     haben deshalb keine Anschluesse. */
  dreieckschaltung: (x, y, o) => _wrap(
    `<path d="M60 4 L88 52 L32 52 Z"/>`, x, y, o),

  sternschaltung: (x, y, o) => _wrap(
    `<path d="M60 52 V28"/><path d="M60 28 L36 8"/><path d="M60 28 L84 8"/>`, x, y, o),

  /* Sternschaltung mit herausgefuehrtem Neutralleiter: derselbe Stern mit einem
     Querstrich am Fuss. */
  sternschaltungN: (x, y, o) => _wrap(
    `<path d="M60 52 V28"/><path d="M60 28 L36 8"/><path d="M60 28 L84 8"/>
     <path d="M46 52 H74"/>`, x, y, o),

  /* Stromwandler, Impulstransformator (S. 453): der Primaerleiter laeuft GERADE
     hindurch, die Sekundaerwicklung liegt daneben am Kern. Genau das Bauteil
     hinter der Strommesszange: messen, ohne aufzutrennen.
     Anschluesse: Primaer (0,30) und (120,30), Sekundaer (120,-10) und (120,70). */
  stromwandler: (x, y, o) => _wrap(
    `<path d="M0 30 H120"/><path d="M56 4 V56"/>
     <path d="M74 6 a10 10 0 0 0 0 20 a10 10 0 0 0 0 20 a10 10 0 0 0 0 20"/>
     <path d="M74 6 V-10 H120"/><path d="M74 66 V70 H120"/>`, x, y, o),

  /* Spartransformator (S. 453): EINE Wicklung mit einer Anzapfung — Primaer- und
     Sekundaerseite haengen galvanisch zusammen, deshalb trennt er nicht.
     Anschluesse: (0,-10), (0,70) und die Anzapfung (120,30). */
  spartransformator: (x, y, o) => _wrap(
    `<path d="M0 -10 H44 V0"/><path d="M0 70 H44 V60"/>
     <path d="M44 0 a10 10 0 0 1 0 20 a10 10 0 0 1 0 20 a10 10 0 0 1 0 20"/>
     <path d="M54 30 H120"/>`, x, y, o),

  /* ======================= Ergaenzungen aus S. 447 =========================
     Leitungen und Leiterkennzeichen. Nachgetragen am 07.08.2026, dritter Schritt.
     Diese Zeichen sind KEINE Bauteile, sondern Kennzeichen AUF einer Leitung:
     die Leitung laeuft durchgehend von Anschluss zu Anschluss, das Kennzeichen
     sitzt in der Mitte. Deshalb kein _lead, sondern eine durchgehende Linie. */

  /* Neutralleiter N / Mittelleiter M (S. 447): ein schraeger Strich auf der
     Leitung mit einem PUNKT am oberen Ende. */
  leiterN: (x, y, o) => _wrap(
    `<path d="M0 30 H120"/><path d="M54 42 L66 18"/>
     <circle cx="67" cy="16" r="4" fill="${_attr(o).f}"/>`, x, y, o),

  /* Schutzleiter PE (S. 447): derselbe schraege Strich, aber mit einem QUERSTRICH
     am oberen Ende statt eines Punktes. Punkt und Querstrich sind der ganze
     Unterschied zwischen N und PE. */
  leiterPE: (x, y, o) => _wrap(
    `<path d="M0 30 H120"/><path d="M54 42 L66 18"/><path d="M59 12 L74 20"/>`, x, y, o),

  /* Neutralleiter mit Schutzfunktion PEN (S. 447): Punkt UND Querstrich — der
     Leiter tut beides zugleich. Genau der Leiter, der im TN-C-Netz aufgeteilt wird. */
  leiterPEN: (x, y, o) => _wrap(
    `<path d="M0 30 H120"/><path d="M54 42 L66 18"/><path d="M56 18 L71 26"/>
     <circle cx="68" cy="13" r="4" fill="${_attr(o).f}"/>`, x, y, o),

  /* Drei Leiter, ein Neutralleiter, ein Schutzleiter (S. 447): die einpolige
     Darstellung eines fuenfadrigen Drehstromkreises — drei schlichte Striche fuer
     L1 L2 L3, dann der N mit Punkt, dann der PE mit Querstrich. */
  leiter3NPE: (x, y, o) => _wrap(
    `<path d="M0 30 H120"/>
     <path d="M16 42 L28 18"/><path d="M26 42 L38 18"/><path d="M36 42 L48 18"/>
     <path d="M56 42 L68 18"/><circle cx="69" cy="16" r="4" fill="${_attr(o).f}"/>
     <path d="M78 42 L90 18"/><path d="M83 12 L98 20"/>`, x, y, o),

  /* Leiter, bewegbar (S. 447): die Leitung mit einer Wellenlinie. */
  leiterBeweglich: (x, y, o) => _wrap(
    `<path d="M0 30 H32"/><path d="M32 30 q14 -20 28 0 q14 20 28 0"/>
     <path d="M88 30 H120"/>`, x, y, o),

  /* Leitung auf Putz / im Putz / unter Putz (S. 447): dasselbe Kennzeichen,
     drei schraege Striche, in drei Lagen zur Leitung — DIE LAGE IST DIE AUSSAGE. */
  leitungAufPutz: (x, y, o) => _wrap(
    `<path d="M0 30 H120"/>
     <path d="M46 54 L58 34"/><path d="M56 54 L68 34"/><path d="M66 54 L78 34"/>`, x, y, o),

  leitungImPutz: (x, y, o) => _wrap(
    `<path d="M0 30 H120"/>
     <path d="M46 44 L58 16"/><path d="M56 44 L68 16"/><path d="M66 44 L78 16"/>`, x, y, o),

  leitungUnterPutz: (x, y, o) => _wrap(
    `<path d="M0 30 H120"/>
     <path d="M46 26 L58 6"/><path d="M56 26 L68 6"/><path d="M66 26 L78 6"/>`, x, y, o),

  /* Leiter im Erdreich, Erdkabel (S. 447): die Leitung mit dem Erdezeichen darunter. */
  erdkabel: (x, y, o) => _wrap(
    `<path d="M0 30 H120"/><path d="M44 42 H76"/><path d="M50 50 H70"/>
     <path d="M56 58 H64"/>`, x, y, o),

  /* Klemmenleiste (S. 447): eine Reihe gleich grosser Klemmen. */
  klemmenleiste: (x, y, o) => _wrap(_lead(20, 98) +
    `<rect x="20" y="16" width="78" height="28"/>
     <path d="M33 16 V44"/><path d="M46 16 V44"/><path d="M59 16 V44"/>
     <path d="M72 16 V44"/><path d="M85 16 V44"/>`, x, y, o),

  /* Trennstelle, Lasche geschlossen (S. 447, Form 2): zwei Querstriche auf der
     durchgehenden Leitung — die Verbindung laesst sich hier auftrennen. */
  trennstelle: (x, y, o) => _wrap(
    `<path d="M0 30 H120"/><path d="M44 18 V42"/><path d="M76 18 V42"/>`, x, y, o),

  /* ======================= Ergaenzungen aus S. 451 und 452 =================
     Nachgetragen am 07.08.2026, zweiter Ausbauschritt. */

  /* Erdungsschalter, allgemein (S. 451): ein Schalter, dessen bewegliche Seite
     auf Erde geht. Das Bauteil hinter Sicherheitsregel 4 (erden und kurzschliessen). */
  erdungsschalter: (x, y, o) => _wrap(
    `<path d="M0 30 H30"/>
     <path id="${(o && o.id) || 'sw'}_arm" d="M90 30 L34 8"/>
     <path d="M90 30 V52"/><path d="M66 52 H114"/><path d="M75 62 H105"/>
     <path d="M84 72 H96"/>`, x, y, o),

  /* Schraubsicherung, Typ D (S. 452): Sicherungskoerper mit drei schraegen
     Strichen — das Kennzeichen der Schraubbauform. */
  schraubsicherung: (x, y, o) => _wrap(_lead(20, 100) + _rectL +
    `<path d="M20 30 H100"/>
     <path d="M40 8 L52 52"/><path d="M52 8 L64 52"/><path d="M64 8 L76 52"/>`, x, y, o),

  /* Niederspannungs-Hochleistungssicherung, NH (S. 452): Sicherungskoerper mit
     einem Querbalken an JEDEM Ende — sie laesst sich ziehen und trennt dabei. */
  nhSicherung: (x, y, o) => _wrap(_lead(20, 100) + _rectL +
    `<path d="M20 30 H100"/><path d="M20 4 V56"/><path d="M100 4 V56"/>`, x, y, o),

  /* Blitzstromableiter (S. 452): Koerper mit einem Blitzzeichen darin.
     Nicht mit dem Ueberspannungsableiter verwechseln — der traegt einen Pfeil. */
  blitzstromableiter: (x, y, o) => _wrap(_lead(20, 100) + _rectL +
    `<path d="M42 18 L62 27 L50 33 L74 42"/>`, x, y, o),

  /* Antrieb eines Thermorelais (S. 451): Antriebsrechteck mit einem zweiten
     Rechteck darin. */
  thermorelais: (x, y, o) => _wrap(_lead(46, 74) + _rectQ +
    `<rect x="52" y="14" width="16" height="32"/>`, x, y, o),

  /* Fortschaltrelais, Stromstossrelais (S. 451): Antriebsrechteck mit dem
     Stufenzeichen — ein Impuls kippt den Schaltzustand um. */
  stromstossrelais: (x, y, o) => _wrap(_lead(46, 74) + _rectQ +
    `<path d="M52 44 H60 V22 H68"/>`, x, y, o),

  /* Antrieb mit Ansprech- UND Rueckfallverzoegerung (S. 451): beide Kennzeichen
     an derselben Schmalseite. */
  zeitrelaisAnzugAbfall: (x, y, o) => _wrap(_lead(46, 74) + _rectQ +
    `<rect x="46" y="44" width="28" height="10" fill="${_attr(o).f}"/>
     <path d="M46 30 H74"/><path d="M46 30 L74 44"/><path d="M74 30 L46 44"/>`, x, y, o),

  /* Galvanometer (S. 452): Messgeraet mit einem Pfeil statt eines Kennbuchstabens —
     es zeigt kleinste Stroeme an und wird als Nullindikator benutzt. */
  galvanometer: (x, y, o) => _wrap(_lead(30, 90) +
    `<circle cx="60" cy="30" r="30"/><path d="M60 46 V24"/>` +
    _spitze(60, 16, 0, -20), x, y, o),

  /* ======================= Ergaenzungen aus S. 446 =========================
     Nachgetragen am 07.08.2026, nachdem Andre die Vollstaendigkeit angemahnt hat.
     Alle elf gegen dieselbe Seite geprueft wie der Rest. */

  /* Widerstand mit Anzapfungen (S. 446): Widerstandskoerper mit zwei Abgriffen,
     die als eigene Anschluesse herausgefuehrt sind. VIER Anschluesse:
     links, rechts und die zwei Abgriffe bei x = 40 und x = 80, je 1 Raster hoch. */
  widerstandAnzapfung: (x, y, o) => _wrap(_lead(20, 100) + _rectL +
    `<path d="M40 14 V-10"/><path d="M80 14 V-10"/>`, x, y, o),

  /* Induktivitaet mit Luftspalt im Magnetkern (S. 446): wie spuleKern, aber der
     Kernstrich ist in der Mitte unterbrochen — der Spalt IST die Aussage. */
  spuleLuftspalt: (x, y, o) => _wrap(_lead(24, 96) + _wick +
    `<path d="M24 12 H54"/><path d="M66 12 H96"/>`, x, y, o),

  /* Piezoelektrischer Kristall mit zwei Elektroden (S. 446): der Kristall als
     Rechteck zwischen zwei Elektrodenplatten. */
  piezo: (x, y, o) => _wrap(_lead(46, 74) +
    `<path d="M46 10 V50"/><path d="M74 10 V50"/>
     <rect x="52" y="18" width="16" height="24"/>`, x, y, o),

  /* Kapazitaetsdiode, Varactor (S. 446): Diode mit einer Kondensatorplatte
     hinter der Kathode. */
  kapazitaetsdiode: (x, y, o) => _wrap(`<path d="M0 30 H34 M84 30 H120"/>` +
    `<path d="M34 10 L34 50 L70 30 Z"/><path d="M70 8 V52"/><path d="M84 8 V52"/>`,
    x, y, o),

  /* Thyristordiode, bidirektional, DIAC (S. 446): zwei gegensinnige Dreiecke mit
     gemeinsamem Querstrich, OHNE Steueranschluss — mit Gate waere es der Triac. */
  diac: (x, y, o) => _wrap(_lead(34, 86) +
    `<path d="M34 8 L34 52 L60 30 Z"/><path d="M86 8 L86 52 L60 30 Z"/>
     <path d="M60 4 V56"/>`, x, y, o),

  /* Sperrschicht-Feldeffekt-Transistor (JFET) mit N-Kanal (S. 446): Kanal als
     durchgehender Balken, Gate mit einem Pfeil, der ZUM Kanal zeigt. Beim
     P-Kanal zeigt derselbe Pfeil vom Kanal WEG — das ist der ganze Unterschied.
     Anschluesse: Gate (0,30), Drain (120,-10), Source (120,70). */
  jfetN: (x, y, o) => _wrap(
    `<path d="M0 30 H36"/>` + _spitze(50, 30, 30, 0) +
    `<path d="M52 6 V54"/>
     <path d="M52 14 H90 V-10 H120"/><path d="M52 46 H90 V70 H120"/>`, x, y, o),

  jfetP: (x, y, o) => _wrap(
    `<path d="M0 30 H50"/>` + _spitze(14, 30, -30, 0) +
    `<path d="M52 6 V54"/>
     <path d="M52 14 H90 V-10 H120"/><path d="M52 46 H90 V70 H120"/>`, x, y, o),

  /* Isolierschicht-Feldeffekt-Transistor (IGFET/MOSFET), Anreicherungstyp,
     Substrat mit Source verbunden (S. 446): Das Gate ist eine eigene Elektrode
     MIT ABSTAND zum Kanal — der Abstand ist die Isolierschicht und damit die
     Aussage des Bauteils. Der Kanal ist UNTERBROCHEN (drei Stuecke): das heisst
     Anreicherungstyp, er leitet erst, wenn das Gate ihn aufsteuert. Ein
     durchgehender Kanal waere der Verarmungstyp.
     Anschluesse: Gate (0,30), Drain (120,-10), Source (120,70). */
  mosfetN: (x, y, o) => _wrap(
    `<path d="M0 30 H38"/><path d="M38 4 V56"/>
     <path d="M50 4 V15"/><path d="M50 25 V35"/><path d="M50 45 V56"/>
     <path d="M50 9 H90 V-10 H120"/><path d="M50 51 H90 V70 H120"/>
     <path d="M90 30 H64"/>` + _spitze(54, 30, -30, 0) +
    `<path d="M90 30 V51"/>`, x, y, o),

  /* Insulated Gate Bipolar Transistor, IGBT (S. 446): isoliertes Gate wie beim
     MOSFET, Ausgangsseite wie beim Bipolartransistor — Emitterpfeil zeigt vom
     Steuerbalken WEG. Anschluesse: Gate (0,30), Kollektor (120,-10),
     Emitter (120,70). */
  igbt: (x, y, o) => _wrap(
    `<path d="M0 30 H36"/><path d="M36 10 V50"/><path d="M48 6 V54"/>
     <path d="M48 20 L84 -10 H120"/><path d="M48 40 L84 70 H120"/>` +
    _spitze(80, 67, 36, 30), x, y, o),

  /* Photoelement, Photozelle (S. 446, Sensoren): das Zeichen der Primaerzelle
     mit zwei Lichtpfeilen, die darauf zeigen. */
  fotoelement: (x, y, o) => _wrap(_lead(52, 68) +
    `<path d="M52 6 V54"/><path d="M68 18 V42"/>
     <path d="M18 -14 L34 0"/>` + _spitze(36, 2, 16, 14) +
    `<path d="M34 -14 L50 0"/>` + _spitze(52, 2, 16, 14), x, y, o),

  /* Optokoppler: Leuchtdiode und Phototransistor in einem Gehaeuse (S. 446).
     VIER Anschluesse: Diode links oben/unten, Transistor rechts oben/unten.
     Die zwei Pfeile in der Mitte sind die optische Kopplung — ohne sie waeren es
     zwei Bauteile nebeneinander. */
  optokoppler: (x, y, o) => _wrap(
    `<rect x="14" y="-14" width="92" height="88"/>
     <path d="M0 -10 H14"/><path d="M0 70 H14"/><path d="M120 -10 H106"/><path d="M120 70 H106"/>
     <path d="M14 -10 H32 V2"/><path d="M32 24 V70 H14"/>
     <path d="M20 2 L44 2 L32 24 Z"/><path d="M20 24 H44"/>
     <path d="M76 8 V52"/><path d="M76 20 L94 -10 H106"/><path d="M76 40 L94 70 H106"/>` +
    _spitze(91, 65, 18, 30) +
    `<path d="M52 18 H62"/>` + _spitze(66, 18, 12, 0) +
    `<path d="M52 40 H62"/>` + _spitze(66, 40, 12, 0), x, y, o),

  /* Hall-Generator (S. 446, Sensoren): Koerper mit einem Kreuz; der Steuerstrom
     laeuft laengs hindurch, die Hallspannung wird QUER dazu abgegriffen. VIER
     Anschluesse: (0,30) und (120,30) laengs, (60,-10) und (60,70) quer. */
  hallgenerator: (x, y, o) => _wrap(_lead(20, 100) + _rectL +
    `<path d="M50 20 L70 40"/><path d="M70 20 L50 40"/>
     <path d="M60 14 V-10"/><path d="M60 46 V70"/>`, x, y, o),

  /* Speicherglied RS (DIN EN 60617-12): Rechteck mit S und R als Eingaengen und
     Q als Ausgang. Ebenfalls nicht aus der Vorlage belegt. */
  flipflopRS: (x, y, o) => _wrap(
    `<path d="M0 -10 H40"/><path d="M0 70 H40"/><path d="M96 30 H120"/>
     <rect x="40" y="-14" width="56" height="88"/>` +
    _kb(o, 47, 8, 'S', 26, 'start') + _kb(o, 47, 66, 'R', 26, 'start') +
    _kb(o, 89, 40, 'Q', 26, 'end'), x, y, o)
};

/* JEDES ZEICHEN SAGT IM DOM, WAS ES IST.
   Die aeussere Gruppe traegt data-sym="batterie". Damit finden polprobe.js und
   die Kontinuitaetspruefung die Zeichen dort, wo sie wirklich stehen: im DOM,
   und nicht ueber eine Textsuche im Quelltext, die auch Kommentare trifft.
   Der Fingerabdruck von symbolprobe.js aendert sich dadurch NICHT — der
   ueberspringt <g> ausdruecklich und misst nur die gezeichneten Teile. */
Object.keys(sym).forEach(name => {
  const zeichnen = sym[name];
  sym[name] = (x, y, o) => zeichnen(x, y, o).replace('<g', `<g data-sym="${name}"`);
});

/* ---------- Leitungen ----------
   wire([[x1,y1],[x2,y2],...], {id, farbe, sw, cls})
   Nur rechtwinklig zeichnen — schräge Leitungen sind in Schaltplänen falsch.
   Die zurückgegebene <path> trägt die Klasse "wire" und ist damit für
   flow.js (Stromfluss-Animation) ansprechbar. */
function wire(pts, o) {
  o = o || {};
  const d = pts.map((p, i) => (i ? 'L' : 'M') + p[0] + ' ' + p[1]).join(' ');
  return `<path${o.id ? ` id="${o.id}"` : ''} class="wire${o.cls ? ' ' + o.cls : ''}"
    d="${d}" fill="none" stroke="${o.farbe || 'var(--wid)'}"
    stroke-width="${o.sw || 5}" stroke-linecap="round" stroke-linejoin="round"/>`;
}
/* Knotenpunkt — Pflicht überall, wo sich Leitungen verbinden. Kreuzungen OHNE
   Punkt bedeuten "keine Verbindung"; dieser Unterschied wird in Prüfungen bewertet.
   Der Punkt ist GEFÜLLT: so steht er in DIN EN 60617-3 (Tabellenbuch S. 447).
   Ein offener Kreis an derselben Stelle bedeutet "Anschluss, z. B. Klemme". */
function knoten(x, y, o) {
  o = o || {};
  return `<circle${o.id ? ` id="${o.id}"` : ''} cx="${x}" cy="${y}" r="8"
    fill="${o.farbe || 'var(--wid)'}"/>`;
}

/* ---------- Zählpfeile ----------
   In der Elektrotechnik ist die Pfeilrichtung Teil der Aussage.
   Serienkonvention (Verbraucherzählpfeilsystem): am Verbraucher zeigen U und I
   in dieselbe Richtung. An der Quelle zeigen sie entgegengesetzt.
   Wer das durcheinanderbringt, produziert Vorzeichenfehler im Video — deshalb
   sind beide Pfeile eigene Bausteine und werden nie freihändig gezeichnet. */

/* Stromzählpfeil AUF der Leitung: pfeilI(x, y, richtung, label)
   richtung: 'r' rechts, 'l' links, 'u' hoch, 'd' runter */
function pfeilI(x, y, dir, label, o) {
  o = o || {};
  const f = o.farbe || 'var(--strom)';
  const rot = { r: 0, d: 90, l: 180, u: 270 }[dir] || 0;
  return `<g transform="translate(${x},${y}) rotate(${rot})" stroke="${f}" fill="none"
      stroke-width="5" stroke-linecap="round" stroke-linejoin="round">
    <path d="M-34 0 H32"/><path d="M18 -11 L32 0 L18 11"/>
    ${label ? `<text x="0" y="-20" text-anchor="middle" font-family="PlexMono"
      font-weight="600" font-size="30" fill="${f}" stroke="none"
      transform="rotate(${-rot})">${label}</text>` : ''}
  </g>`;
}
/* Spannungszählpfeil NEBEN dem Bauteil: pfeilU(x1,y1,x2,y2,label)
   Der Pfeil zeigt von x1,y1 nach x2,y2 — also vom höheren zum niedrigeren Potential. */
function pfeilU(x1, y1, x2, y2, label, o) {
  o = o || {};
  const f = o.farbe || 'var(--spannung)';
  const dx = x2 - x1, dy = y2 - y1, L = Math.hypot(dx, dy);
  const ux = dx / L, uy = dy / L, nx = -uy, ny = ux;
  const mx = (x1 + x2) / 2 + nx * 26, my = (y1 + y2) / 2 + ny * 26;
  return `<g stroke="${f}" fill="none" stroke-width="5" stroke-linecap="round"
      stroke-linejoin="round">
    <path d="M${x1} ${y1} L${x2} ${y2}"/>
    <path d="M${x2 - ux*20 + nx*10} ${y2 - uy*20 + ny*10} L${x2} ${y2}
             L${x2 - ux*20 - nx*10} ${y2 - uy*20 - ny*10}"/>
    <path d="M${x1 - nx*9} ${y1 - ny*9} L${x1 + nx*9} ${y1 + ny*9}"/>
    ${label ? `<text x="${mx}" y="${my}" text-anchor="middle" dominant-baseline="middle"
      font-family="PlexMono" font-weight="600" font-size="30" fill="${f}"
      stroke="none">${label}</text>` : ''}
  </g>`;
}

/* ---------- Helfer: ganze Schaltung in die Grafikbühne setzen ----------
   schaltung('gfx', 1240, 680, inhalt)  — legt ein <svg> mit passendem viewBox an.
   In Szenen IMMER über diese Funktion, damit beide Formate dieselbe Geometrie sehen. */
function schaltung(hostId, w, h, inhalt) {
  const host = $(hostId);
  host.insertAdjacentHTML('beforeend',
    `<svg viewBox="0 0 ${w} ${h}" preserveAspectRatio="xMidYMid meet">${inhalt}</svg>`);
}
