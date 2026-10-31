#!/usr/bin/env python3
"""
circuit_builder.py — Normgerechter Schaltplan-Generator nach DIN EN 60617
fuer den Moodle-MBZ-Builder.

Features:
- Platziert Bauteile aus dem 180-Symbole-Register (assets/schaltsymbole/)
- 120x60-Zellraster mit exakten Anschlusspunkten
- Orthogonales Leitungsrouting (HV, VH, HVH, VHV, Pfade)
- Verbindungspunkte (Knoten nach DIN EN 60617-3)
- Zaehlpfeile (pfeilI, pfeilU)
- Betriebsmittelkennzeichnung (BMK) & Werte
- Fertige Presets fuer Standard-Schaltungen (Grundstromkreis, Wendeschuetz,
  Stern-Dreieck, Graetz-Bruecke, RLC-Netzwerke)
- CLI-Interface fuer JSON-DSL und Presets
"""

import json
import math
import os
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent
SYMBOLS_DIR = SKILL_DIR / 'assets' / 'schaltsymbole' / 'SVG'
INDEX_FILE = SKILL_DIR / 'assets' / 'schaltsymbole' / 'symbolregister-neu.json'

GRID_W = 120
GRID_H = 60
SW = 5  # Standard Strichstaerke

# CSS Styling fuer Standalone- und Inline-SVGs
CIRCUIT_STYLE = """
:root {
  --wid: #16232b;
  --text: #16232b;
  --text2: #5a6b75;
  --strom: #e07a2f;
  --spannung: #2f6fe0;
  --magnet: #d94f9a;
  --ok: #2e8b57;
  --gefahr: #d0392b;
  --leiter-l: #8a3b14;
  --leiter-n: #2f6fe0;
  --leiter-pe: #2e8b57;
}
svg { background: #ffffff; }
text { font-family: "IBM Plex Mono", Consolas, "Liberation Mono", monospace; }
text.bmk { font-size: 26px; font-weight: 700; fill: var(--text); }
text.wert { font-size: 22px; font-weight: 500; fill: var(--text2); }
text.pin { font-size: 18px; font-weight: 600; fill: var(--text2); }
text.title { font-size: 28px; font-weight: 700; fill: var(--text); }
text.leiter { font-size: 22px; font-weight: 700; fill: var(--text); }
.wire { fill: none; stroke: var(--wid); stroke-width: 5px; stroke-linecap: round; stroke-linejoin: round; }
.wire-thick { fill: none; stroke: var(--wid); stroke-width: 6px; stroke-linecap: round; stroke-linejoin: round; }
.wire-pe { fill: none; stroke: var(--leiter-pe); stroke-width: 5px; stroke-dasharray: 12 8; stroke-linecap: round; stroke-linejoin: round; }
.wire-n { fill: none; stroke: var(--leiter-n); stroke-width: 5px; stroke-linecap: round; stroke-linejoin: round; }
.knoten { fill: var(--wid); stroke: none; }
.klemme-dot { fill: #ffffff; stroke: var(--wid); stroke-width: 3px; }
"""

LPOS = {
    0:   {'lx': 60, 'ly': -46, 'wx': 60, 'wy': 58,  'an': 'middle'},
    90:  {'lx': 48, 'ly': 52,  'wx': 48, 'wy': 92,  'an': 'start'},
    180: {'lx': -60,'ly': -46, 'wx': -60,'wy': 58,  'an': 'middle'},
    270: {'lx': 48, 'ly': -68, 'wx': 48, 'wy': -28, 'an': 'start'}
}


class CircuitBuilder:
    def __init__(self, title=""):
        self.title = title
        self.nodes = {}
        self.wires = []
        self.junctions = []
        self.arrows = []
        self.texts = []
        self.busbars = []
        self._raw_elements = []

    def add_node(self, node_id, symbol, x, y, rot=0, label=None, wert=None,
                 pins=None, farbe=None, cls=None, is_grid=True):
        """Platziert ein Bauteil. x,y sind standardmaessig Grid-Koordinaten."""
        px = x * GRID_W if is_grid else x
        py = y * GRID_H if is_grid else y
        self.nodes[node_id] = {
            'id': node_id,
            'symbol': symbol,
            'x': px,
            'y': py,
            'grid_x': x if is_grid else x / GRID_W,
            'grid_y': y if is_grid else y / GRID_H,
            'rot': rot % 360,
            'label': label,
            'wert': wert,
            'pins': pins or {},
            'farbe': farbe or 'var(--wid)',
            'cls': cls or ''
        }
        return self

    def get_port_coord(self, node_id, port='right'):
        """Ermittelt die exakte (x,y)-Koordinate eines Anschlusses."""
        if node_id not in self.nodes:
            raise KeyError(f"Node '{node_id}' existiert nicht.")
        n = self.nodes[node_id]
        rot = n['rot']
        x0, y0 = n['x'], n['y']

        # Lokale Standard-Ports vor Drehung (Zelle 120x60, Drehpunkt bei 0,0)
        local_ports = {
            'left': (0, 0),
            '1': (0, 0),
            'in': (0, 0),
            'right': (120, 0),
            '2': (120, 0),
            'out': (120, 0),
            'top': (60, -40),
            '3': (60, -40),
            'bottom': (60, 40),
            '4': (60, 40),
            'mid': (60, 0),
            # Mehrpolige Klemmen / Transistoren / Schuetze
            'A1': (0, 0),
            'A2': (120, 0),
            '13': (0, 0),
            '14': (120, 0),
            '21': (0, 0),
            '22': (120, 0),
            '1_in': (0, -40),
            '1_out': (120, -40),
            '2_in': (0, 0),
            '2_out': (120, 0),
            '3_in': (0, 40),
            '3_out': (120, 40),
        }

        # Falls Port explizit in (lx, ly)
        if isinstance(port, (list, tuple)) and len(port) == 2:
            lx, ly = port
        else:
            lx, ly = local_ports.get(str(port), (120, 0))

        # Drehung um (0,0) des Bauteils
        rad = math.radians(rot)
        rx = lx * math.cos(rad) - ly * math.sin(rad)
        ry = lx * math.sin(rad) + ly * math.cos(rad)
        return (round(x0 + rx, 2), round(y0 + ry, 2))

    def add_wire(self, p_from, p_to, routing='direct', waypoints=None,
                 farbe=None, cls=None, sw=None):
        """Fuegt eine Leitung zwischen zwei Punkten oder Ports hinzu."""
        self.wires.append({
            'from': p_from,
            'to': p_to,
            'routing': routing,
            'waypoints': waypoints or [],
            'farbe': farbe or 'var(--wid)',
            'cls': cls or 'wire',
            'sw': sw or SW
        })
        return self

    def add_junction(self, x, y, farbe=None, is_grid=False):
        """Knotenpunkt (gefuellter Kreis)."""
        px = x * GRID_W if is_grid else x
        py = y * GRID_H if is_grid else y
        self.junctions.append({'x': px, 'y': py, 'farbe': farbe or 'var(--wid)'})
        return self

    def add_arrow_i(self, x, y, direction='r', label='I', farbe=None):
        """Stromzaehlpfeil auf Leitung: dir in ['r','l','u','d']."""
        self.arrows.append({
            'type': 'I',
            'x': x,
            'y': y,
            'dir': direction,
            'label': label,
            'farbe': farbe or 'var(--strom)'
        })
        return self

    def add_arrow_u(self, x1, y1, x2, y2, label='U', farbe=None):
        """Spannungszaehlpfeil neben Bauteil."""
        self.arrows.append({
            'type': 'U',
            'x1': x1, 'y1': y1,
            'x2': x2, 'y2': y2,
            'label': label,
            'farbe': farbe or 'var(--spannung)'
        })
        return self

    def add_text(self, text, x, y, cls='tx', anchor='start', size=24, weight=600):
        self.texts.append({
            'text': text, 'x': x, 'y': y, 'cls': cls,
            'anchor': anchor, 'size': size, 'weight': weight
        })
        return self

    def _extract_symbol_svg(self, symbol_name):
        """Liest das innere Geometrieelement aus assets/schaltsymbole/SVG/<name>.svg."""
        svg_file = SYMBOLS_DIR / f"{symbol_name}.svg"
        if not svg_file.exists():
            # Fallback wenn .svg fehlt: Platzhalter-Rechteck
            return f'<rect x="20" y="-16" width="80" height="32" fill="none" stroke="currentColor"/>' + \
                   f'<text x="60" y="6" text-anchor="middle" font-size="16">{symbol_name}</text>'

        try:
            tree = ET.parse(svg_file)
            root = tree.getroot()
            # Finde die <g>-Gruppe mit class="sym" (ausdruecklich kein <svg>)
            sym_group = None
            for elem in root.iter():
                if elem.tag.endswith('g') and 'sym' in elem.attrib.get('class', '').split():
                    sym_group = elem
                    break

            if sym_group is not None:
                # Extrahiere Kindelemente der sym-Gruppe
                # Wir entfernen XML-Namespaces aus den Tags
                def clean_tag(t):
                    return t.split('}')[-1] if '}' in t else t

                def elem_to_str(el):
                    tag = clean_tag(el.tag)
                    attrs = ' '.join(f'{k}="{v}"' for k, v in el.attrib.items() if not k.startswith('xmlns'))
                    attr_str = f" {attrs}" if attrs else ""
                    children_str = "".join(elem_to_str(c) for c in el)
                    text = el.text or ""
                    tail = el.tail or ""
                    if children_str or text:
                        return f"<{tag}{attr_str}>{text}{children_str}</{tag}>{tail}"
                    return f"<{tag}{attr_str}/>{tail}"

                inner_xml = "".join(elem_to_str(child) for child in sym_group)
                return inner_xml
        except Exception as e:
            print(f"Warning: Symbol {symbol_name} konnte nicht geparst werden: {e}", file=sys.stderr)

        # Fallback
        return f'<path d="M0 0 H20 M100 0 H120"/><rect x="20" y="-16" width="80" height="32" fill="none" stroke="currentColor"/>'

    def render_svg(self, padding=40):
        """Generiert das fertige, wohlgeformte SVG."""
        elements = []

        # 1. Sammle alle Koordinaten fuer ViewBox-Berechnung
        all_pts = []

        # 2. Nodes rendern
        for nid, n in self.nodes.items():
            sym = n['symbol']
            x, y = n['x'], n['y']
            rot = n['rot']
            f = n['farbe']
            all_pts.extend([(x, y), (x + 120, y), (x, y + 60), (x + 120, y + 60)])

            # Beschriftung berechnen
            lp = LPOS.get(rot, LPOS[0])
            txt_elements = []
            if n['label']:
                all_pts.extend([(x + lp['lx'] - 40, y + lp['ly'] - 20), (x + lp['lx'] + 40, y + lp['ly'] + 10)])
                txt_elements.append(
                    f'<text class="bmk" x="{lp["lx"]}" y="{lp["ly"]}" text-anchor="{lp["an"]}">{n["label"]}</text>'
                )
            if n['wert']:
                all_pts.extend([(x + lp['wx'] - 40, y + lp['wy'] - 20), (x + lp['wx'] + 40, y + lp['wy'] + 10)])
                txt_elements.append(
                    f'<text class="wert" x="{lp["wx"]}" y="{lp["wy"]}" text-anchor="{lp["an"]}">{n["wert"]}</text>'
                )

            # Pin-Nummern
            for pin_name, pin_label in n['pins'].items():
                p_coord = self.get_port_coord(nid, pin_name)
                txt_elements.append(
                    f'<text class="pin" x="{p_coord[0] - x}" y="{p_coord[1] - y - 8}" text-anchor="middle">{pin_label}</text>'
                )

            inner_svg = self._extract_symbol_svg(sym)

            node_markup = f'''
  <!-- Node: {nid} ({sym}) -->
  <g id="{nid}" class="sym {n['cls']}" transform="translate({x}, {y})">
    <g transform="rotate({rot})">
      {inner_svg}
    </g>
    {"".join(txt_elements)}
  </g>'''
            elements.append(node_markup)

        # 3. Wires rendern
        for w in self.wires:
            # Ausgangs- und Endpunkt bestimmen
            p1 = w['from']
            if isinstance(p1, (list, tuple)):
                x1, y1 = p1
            elif isinstance(p1, str) and ':' in p1:
                node_id, port = p1.split(':', 1)
                x1, y1 = self.get_port_coord(node_id, port)
            elif isinstance(p1, str) and p1 in self.nodes:
                x1, y1 = self.get_port_coord(p1, 'right')
            else:
                x1, y1 = (0, 0)

            p2 = w['to']
            if isinstance(p2, (list, tuple)):
                x2, y2 = p2
            elif isinstance(p2, str) and ':' in p2:
                node_id, port = p2.split(':', 1)
                x2, y2 = self.get_port_coord(node_id, port)
            elif isinstance(p2, str) and p2 in self.nodes:
                x2, y2 = self.get_port_coord(p2, 'left')
            else:
                x2, y2 = (0, 0)

            all_pts.extend([(x1, y1), (x2, y2)])

            # Pfadkonstruktion je nach Routing
            routing = w['routing']
            pts = [(x1, y1)]

            if w['waypoints']:
                for wp in w['waypoints']:
                    pts.append(tuple(wp))
                    all_pts.append(tuple(wp))
            elif routing == 'hv':
                pts.append((x2, y1))
            elif routing == 'vh':
                pts.append((x1, y2))
            elif routing == 'hvh':
                mid_x = (x1 + x2) / 2
                pts.append((mid_x, y1))
                pts.append((mid_x, y2))
            elif routing == 'vhv':
                mid_y = (y1 + y2) / 2
                pts.append((x1, mid_y))
                pts.append((x2, mid_y))

            pts.append((x2, y2))

            # SVG Pfadstring
            d = " ".join((f"M {p[0]} {p[1]}" if i == 0 else f"L {p[0]} {p[1]}") for i, p in enumerate(pts))
            cls_name = w['cls']
            stroke_farbe = w['farbe']
            sw = w['sw']

            elements.append(
                f'  <path d="{d}" class="{cls_name}" stroke="{stroke_farbe}" stroke-width="{sw}"/>'
            )

        # 4. Junctions (Knoten)
        for j in self.junctions:
            jx, jy = j['x'], j['y']
            jf = j['farbe']
            all_pts.append((jx, jy))
            elements.append(f'  <circle class="knoten" cx="{jx}" cy="{jy}" r="7" fill="{jf}"/>')

        # 5. Zaehlpfeile
        for a in self.arrows:
            if a['type'] == 'I':
                x, y, d, lbl, f = a['x'], a['y'], a['dir'], a['label'], a['farbe']
                all_pts.append((x, y))
                rot_deg = {'r': 0, 'd': 90, 'l': 180, 'u': 270}.get(d, 0)
                elements.append(f'''
  <!-- Strompfeil: {lbl} -->
  <g transform="translate({x},{y}) rotate({rot_deg})" stroke="{f}" fill="none" stroke-width="4" stroke-linecap="round" stroke-linejoin="round">
    <path d="M-28 0 H26"/><path d="M14 -9 L26 0 L14 9"/>
    {f'<text x="0" y="-14" text-anchor="middle" font-size="22" font-weight="700" fill="{f}" stroke="none" transform="rotate({-rot_deg})">{lbl}</text>' if lbl else ''}
  </g>''')
            elif a['type'] == 'U':
                x1, y1, x2, y2, lbl, f = a['x1'], a['y1'], a['x2'], a['y2'], a['label'], a['farbe']
                all_pts.extend([(x1, y1), (x2, y2)])
                dx, dy = x2 - x1, y2 - y1
                L = math.hypot(dx, dy) or 1
                ux, uy = dx / L, dy / L
                nx, ny = -uy, ux
                mx = (x1 + x2) / 2 + nx * 24
                my = (y1 + y2) / 2 + ny * 24
                elements.append(f'''
  <!-- Spannungspfeil: {lbl} -->
  <g stroke="{f}" fill="none" stroke-width="4" stroke-linecap="round" stroke-linejoin="round">
    <path d="M{x1} {y1} L{x2} {y2}"/>
    <path d="M{x2 - ux*16 + nx*8} {y2 - uy*16 + ny*8} L{x2} {y2} L{x2 - ux*16 - nx*8} {y2 - uy*16 - ny*8}"/>
    <path d="M{x1 - nx*8} {y1 - ny*8} L{x1 + nx*8} {y1 + ny*8}"/>
    {f'<text x="{mx}" y="{my}" text-anchor="middle" dominant-baseline="middle" font-size="22" font-weight="700" fill="{f}" stroke="none">{lbl}</text>' if lbl else ''}
  </g>''')

        # 6. Freie Texte
        for t in self.texts:
            all_pts.append((t['x'], t['y']))
            elements.append(
                f'  <text class="{t["cls"]}" x="{t["x"]}" y="{t["y"]}" text-anchor="{t["anchor"]}" font-size="{t["size"]}px" font-weight="{t["weight"]}">{t["text"]}</text>'
            )

        # 7. ViewBox ermitteln
        if not all_pts:
            min_x, min_y, max_x, max_y = 0, 0, 400, 300
        else:
            xs = [p[0] for p in all_pts]
            ys = [p[1] for p in all_pts]
            min_x = min(xs) - padding
            min_y = min(ys) - padding
            max_x = max(xs) + padding
            max_y = max(ys) + padding

        w = max(100, int(max_x - min_x))
        h = max(100, int(max_y - min_y))

        title_elem = f'<title>{self.title}</title>\n' if self.title else ''

        svg_code = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="{int(min_x)} {int(min_y)} {w} {h}" width="{w}" height="{h}">
{title_elem}<style>
{CIRCUIT_STYLE}
</style>
<rect x="{int(min_x)}" y="{int(min_y)}" width="{w}" height="{h}" fill="#ffffff"/>
{"".join(elements)}
</svg>
'''
        COLOR_MAP = {
            'var(--wid)': '#16232b',
            'var(--text)': '#16232b',
            'var(--text2)': '#5a6b75',
            'var(--strom)': '#e07a2f',
            'var(--spannung)': '#2f6fe0',
            'var(--magnet)': '#d94f9a',
            'var(--ok)': '#2e8b57',
            'var(--gefahr)': '#d0392b',
            'var(--leiter-l)': '#8a3b14',
            'var(--leiter-n)': '#2f6fe0',
            'var(--leiter-pe)': '#2e8b57'
        }
        for var_name, hex_val in COLOR_MAP.items():
            svg_code = svg_code.replace(var_name, hex_val)

        return svg_code


# ----------------------------------------------------------------------
# Standard-Schaltungs-Presets
# ----------------------------------------------------------------------

def build_preset_grundstromkreis():
    """Einfacher geschlossener Grundstromkreis mit Messgeraeten und Zaehlpfeilen."""
    cb = CircuitBuilder("Grundstromkreis mit Messgeraeten")
    
    # 0,0: DC Quelle (senkrecht 90 Grad)
    cb.add_node('Q1', 'quelleDC', x=100, y=140, rot=90, label='U_q', wert='12 V', is_grid=False)
    # Schalter oben
    cb.add_node('S1', 'schalter', x=260, y=140, rot=0, label='S1', is_grid=False)
    # Amperemeter
    cb.add_node('P1', 'messer', x=420, y=140, rot=0, label='P1', wert='A', is_grid=False)
    # Lastwiderstand rechts senkrecht
    cb.add_node('R1', 'widerstand', x=580, y=140, rot=90, label='R1', wert='100 Ω', is_grid=False)
    
    # Leitungsfuehrung
    # Von Quelle oben nach Schalter links
    cb.add_wire((100, 140), (260, 140), routing='direct')
    # Von Schalter rechts nach Amperemeter links
    cb.add_wire((380, 140), (420, 140), routing='direct')
    # Von Amperemeter rechts nach R1 oben
    cb.add_wire((540, 140), (580, 140), routing='direct')
    # Von R1 unten zurueck nach Quelle unten
    cb.add_wire((580, 260), (100, 260), routing='direct')
    
    # Voltmeter parallel zu R1
    cb.add_node('P2', 'messer', x=720, y=140, rot=90, label='P2', wert='V', is_grid=False)
    cb.add_wire((580, 140), (720, 140), routing='direct')
    cb.add_wire((580, 260), (720, 260), routing='direct')
    cb.add_junction(580, 140)
    cb.add_junction(580, 260)
    
    # Zaehlpfeile
    cb.add_arrow_i(380, 140, 'r', 'I')
    cb.add_arrow_u(640, 150, 640, 250, 'U_R')
    
    return cb.render_svg()


def build_preset_graetz_bruecke():
    """Graetz-Brueckengleichrichter mit 4 Dioden, Trafo und Last."""
    cb = CircuitBuilder("Graetz-Brueckengleichrichter")
    
    # Trafo links
    cb.add_node('T1', 'trafo', x=80, y=180, rot=0, label='T1', wert='230V / 24V', is_grid=False)
    
    # 4 Dioden der Bruecke
    # Diode V1: links -> oben
    cb.add_node('V1', 'diode', x=300, y=120, rot=0, label='V1', wert='1N4007', is_grid=False)
    # Diode V2: links -> unten
    cb.add_node('V2', 'diode', x=300, y=240, rot=180, label='V2', is_grid=False)
    # Diode V3: oben -> rechts
    cb.add_node('V3', 'diode', x=440, y=120, rot=0, label='V3', is_grid=False)
    # Diode V4: unten -> rechts
    cb.add_node('V4', 'diode', x=440, y=240, rot=180, label='V4', is_grid=False)
    
    # Wechselstrom-Einspeisung der Bruecke
    # Sekundaerseite Trafo oben -> Brueckeneingang AC1 (zwischen V1 und V2)
    cb.add_wire((200, 140), (300, 140), routing='direct')
    cb.add_wire((300, 140), (300, 120), routing='direct')
    cb.add_wire((300, 140), (300, 240), routing='direct')
    cb.add_junction(300, 140)
    
    # Sekundaerseite Trafo unten -> Brueckeneingang AC2 (zwischen V3 und V4)
    cb.add_wire((200, 220), (560, 220), routing='direct')
    cb.add_wire((560, 220), (560, 120), routing='direct')
    cb.add_wire((560, 220), (560, 240), routing='direct')
    cb.add_junction(560, 220)
    
    # Gleichstromausgang (+) oben
    cb.add_wire((420, 120), (440, 120), routing='direct')
    cb.add_junction(430, 120)
    cb.add_wire((430, 120), (660, 120), routing='direct')
    
    # Gleichstromausgang (-) unten
    cb.add_wire((180, 240), (320, 240), routing='direct')
    cb.add_junction(310, 240)
    cb.add_wire((310, 240), (660, 240), routing='direct')
    
    # Glaettungskondensator C_1
    cb.add_node('C1', 'kondensatorPol', x=660, y=120, rot=90, label='C_1', wert='1000 µF', is_grid=False)
    cb.add_wire((660, 120), (660, 120), routing='direct')
    cb.add_junction(660, 120)
    cb.add_junction(660, 240)
    
    # Lastwiderstand R_L
    cb.add_node('RL', 'widerstand', x=780, y=120, rot=90, label='R_L', wert='470 Ω', is_grid=False)
    cb.add_wire((660, 120), (780, 120), routing='direct')
    cb.add_wire((660, 240), (780, 240), routing='direct')
    cb.add_junction(780, 120)
    cb.add_junction(780, 240)
    
    # Ausgangs-Plus und Minus Beschriftung
    cb.add_text("+ U_DC", 830, 115, cls="leiter", anchor="start")
    cb.add_text("- GND", 830, 255, cls="leiter", anchor="start")
    
    return cb.render_svg()


def build_preset_wendeschuetz_haupt():
    """Hauptstromkreis einer Wendeschuetzschaltung mit Phasentausch L1-L3."""
    cb = CircuitBuilder("Wendeschuetzschaltung — Hauptstromkreis (DIN EN 60617)")
    
    # Sammelschienen oben L1, L2, L3, PE
    cb.add_text("L1", 40, 35, cls="leiter")
    cb.add_text("L2", 40, 65, cls="leiter")
    cb.add_text("L3", 40, 95, cls="leiter")
    cb.add_text("PE", 40, 125, cls="leiter")
    
    cb.add_wire((80, 35), (600, 35), cls="wire-thick", farbe="var(--leiter-l)")
    cb.add_wire((80, 65), (600, 65), cls="wire-thick", farbe="var(--leiter-l)")
    cb.add_wire((80, 95), (600, 95), cls="wire-thick", farbe="var(--leiter-l)")
    cb.add_wire((80, 125), (600, 125), cls="wire-pe")
    
    # Hauptschalter / Motorschutzschalter Q1 (3-polig)
    cb.add_node('Q1_1', 'schliesser', x=140, y=170, rot=90, label='Q_1', wert='13-14', is_grid=False)
    cb.add_node('Q1_2', 'schliesser', x=200, y=170, rot=90, is_grid=False)
    cb.add_node('Q1_3', 'schliesser', x=260, y=170, rot=90, is_grid=False)
    
    # Zuleitung von Sammelschiene zu Q1
    cb.add_wire((140, 35), (140, 170))
    cb.add_junction(140, 35)
    cb.add_wire((200, 65), (200, 170))
    cb.add_junction(200, 65)
    cb.add_wire((260, 95), (260, 170))
    cb.add_junction(260, 95)
    
    # Richtungsschuetz K1 (Rechtslauf)
    cb.add_node('K1_1', 'schliesser', x=140, y=320, rot=90, label='K_1 (Rechts)', is_grid=False)
    cb.add_node('K1_2', 'schliesser', x=200, y=320, rot=90, is_grid=False)
    cb.add_node('K1_3', 'schliesser', x=260, y=320, rot=90, is_grid=False)
    
    cb.add_wire((140, 290), (140, 320))
    cb.add_wire((200, 290), (200, 320))
    cb.add_wire((260, 290), (260, 320))
    
    # Richtungsschuetz K2 (Linkslauf - Phasentausch L1 und L3)
    cb.add_node('K2_1', 'schliesser', x=380, y=320, rot=90, label='K_2 (Links)', is_grid=False)
    cb.add_node('K2_2', 'schliesser', x=440, y=320, rot=90, is_grid=False)
    cb.add_node('K2_3', 'schliesser', x=500, y=320, rot=90, is_grid=False)
    
    # Abzweig vor K1 zu K2 (Phasen L1, L2, L3)
    cb.add_wire((140, 305), (380, 305))
    cb.add_wire((380, 305), (380, 320))
    cb.add_junction(140, 305)
    
    cb.add_wire((200, 310), (440, 310))
    cb.add_wire((440, 310), (440, 320))
    cb.add_junction(200, 310)
    
    cb.add_wire((260, 315), (500, 315))
    cb.add_wire((500, 315), (500, 320))
    cb.add_junction(260, 315)
    
    # Rueckfuehrung hinter K2 mit Phasentausch:
    # K2 Ausgang 1 (L1) -> zu K1 Ausgang 3 (L3)
    cb.add_wire((380, 440), (380, 460))
    cb.add_wire((380, 460), (260, 460))
    cb.add_wire((260, 440), (260, 480))
    cb.add_junction(260, 460)
    
    # K2 Ausgang 2 (L2) -> zu K1 Ausgang 2 (L2 unvertauscht)
    cb.add_wire((440, 440), (440, 470))
    cb.add_wire((440, 470), (200, 470))
    cb.add_wire((200, 440), (200, 480))
    cb.add_junction(200, 470)
    
    # K2 Ausgang 3 (L3) -> zu K1 Ausgang 1 (L1)
    cb.add_wire((500, 440), (500, 480))
    cb.add_wire((500, 480), (140, 480))
    cb.add_wire((140, 440), (140, 480))
    cb.add_junction(140, 480)
    
    # Thermisches Ueberlastrelais F1
    cb.add_node('F1_1', 'widerstand', x=140, y=510, rot=90, label='F_1', is_grid=False)
    cb.add_node('F1_2', 'widerstand', x=200, y=510, rot=90, is_grid=False)
    cb.add_node('F1_3', 'widerstand', x=260, y=510, rot=90, is_grid=False)
    
    cb.add_wire((140, 480), (140, 510))
    cb.add_wire((200, 480), (200, 510))
    cb.add_wire((260, 480), (260, 510))
    
    # Drehstrommotor M1
    cb.add_node('M1', 'motor3', x=140, y=670, rot=0, label='M_1', wert='3~ 400 V / 1,5 kW', is_grid=False)
    cb.add_wire((140, 630), (140, 640))
    cb.add_wire((140, 640), (200, 640))
    cb.add_wire((200, 630), (200, 640))
    cb.add_wire((260, 630), (260, 640))
    cb.add_wire((260, 640), (200, 640))
    
    # PE Leitung zum Motor
    cb.add_wire((580, 125), (580, 670), cls="wire-pe")
    cb.add_wire((580, 670), (230, 670), cls="wire-pe")
    cb.add_junction(580, 125)
    
    return cb.render_svg()


def build_preset_wendeschuetz_steuer():
    """Steuerstromkreis einer Wendeschuetzschaltung mit gegenseitiger Verriegelung."""
    cb = CircuitBuilder("Wendeschuetzschaltung — Steuerstromkreis (230 V AC)")
    
    # Zuleitung L1 oben, N unten
    cb.add_text("L1 (230 V)", 40, 25, cls="leiter")
    cb.add_text("N", 40, 725, cls="leiter")
    cb.add_wire((100, 40), (520, 40), cls="wire-thick")
    cb.add_wire((100, 700), (520, 700), cls="wire-n")
    
    # Steuersicherung F0
    cb.add_node('F0', 'sicherung', x=120, y=50, rot=90, label='F_0', wert='6 A', is_grid=False)
    cb.add_wire((120, 40), (120, 50))
    cb.add_junction(120, 40)
    
    # Motorschutz-Oeffner F1 (95-96)
    cb.add_node('F1', 'oeffner', x=120, y=160, rot=90, label='F_1 (95-96)', is_grid=False)
    cb.add_wire((120, 150), (120, 160))
    
    # Aus-Taster S0
    cb.add_node('S0', 'oeffner', x=120, y=270, rot=90, label='S_0 (Aus)', is_grid=False)
    cb.add_wire((120, 260), (120, 270))
    
    # Verteilerpunkt nach S0
    cb.add_wire((120, 370), (120, 390))
    cb.add_junction(120, 390)
    cb.add_wire((120, 390), (420, 390))
    
    # Pfad 1: Rechtslauf K1
    # Ein-Taster S1 (Rechts) + Selbsthaltung K1 (13-14)
    cb.add_node('S1', 'schliesser', x=240, y=410, rot=90, label='S_1 (Ein I)', is_grid=False)
    cb.add_wire((240, 390), (240, 410))
    cb.add_junction(240, 390)
    
    cb.add_node('K1_sh', 'schliesser', x=310, y=410, rot=90, label='K_1 (13-14)', is_grid=False)
    cb.add_wire((240, 400), (310, 400))
    cb.add_wire((310, 400), (310, 410))
    cb.add_junction(240, 400)
    
    cb.add_wire((240, 510), (240, 530))
    cb.add_wire((310, 510), (310, 530))
    cb.add_wire((310, 530), (240, 530))
    cb.add_junction(240, 530)
    
    # Elektrische Verriegelung ueber K2 (21-22 Oeffner)
    cb.add_node('K2_v', 'oeffner', x=240, y=540, rot=90, label='K_2 (21-22)', is_grid=False)
    cb.add_wire((240, 530), (240, 540))
    
    # Schuetzspule K1
    cb.add_node('K1_sp', 'schuetzspule', x=240, y=635, rot=90, label='K_1 (A_1-A_2)', is_grid=False)
    cb.add_wire((240, 625), (240, 635))
    cb.add_wire((240, 695), (240, 700))
    cb.add_junction(240, 700)
    
    # Pfad 2: Linkslauf K2
    # Ein-Taster S2 (Links) + Selbsthaltung K2 (13-14)
    cb.add_node('S2', 'schliesser', x=420, y=410, rot=90, label='S_2 (Ein II)', is_grid=False)
    cb.add_wire((420, 390), (420, 410))
    cb.add_junction(420, 390)
    
    cb.add_node('K2_sh', 'schliesser', x=490, y=410, rot=90, label='K_2 (13-14)', is_grid=False)
    cb.add_wire((420, 400), (490, 400))
    cb.add_wire((490, 400), (490, 410))
    cb.add_junction(420, 400)
    
    cb.add_wire((420, 510), (420, 530))
    cb.add_wire((490, 510), (490, 530))
    cb.add_wire((490, 530), (420, 530))
    cb.add_junction(420, 530)
    
    # Elektrische Verriegelung ueber K1 (21-22 Oeffner)
    cb.add_node('K1_v', 'oeffner', x=420, y=540, rot=90, label='K_1 (21-22)', is_grid=False)
    cb.add_wire((420, 530), (420, 540))
    
    # Schuetzspule K2
    cb.add_node('K2_sp', 'schuetzspule', x=420, y=635, rot=90, label='K_2 (A_1-A_2)', is_grid=False)
    cb.add_wire((420, 625), (420, 635))
    cb.add_wire((420, 695), (420, 700))
    cb.add_junction(420, 700)
    
    return cb.render_svg()


def build_preset_sterndreieck_haupt():
    """Hauptstromkreis der Stern-Dreieck-Schaltung."""
    cb = CircuitBuilder("Stern-Dreieck-Schaltung — Hauptstromkreis")
    
    # Phasen L1, L2, L3
    cb.add_text("L1", 40, 50, cls="leiter")
    cb.add_text("L2", 40, 80, cls="leiter")
    cb.add_text("L3", 40, 110, cls="leiter")
    cb.add_wire((80, 45), (650, 45), cls="wire-thick", farbe="var(--leiter-l)")
    cb.add_wire((80, 75), (650, 75), cls="wire-thick", farbe="var(--leiter-l)")
    cb.add_wire((80, 105), (650, 105), cls="wire-thick", farbe="var(--leiter-l)")
    
    # Netzschuetz K1
    cb.add_node('K1_1', 'schliesser', x=140, y=160, rot=90, label='K1 (Netz)', is_grid=False)
    cb.add_node('K1_2', 'schliesser', x=200, y=160, rot=90, is_grid=False)
    cb.add_node('K1_3', 'schliesser', x=260, y=160, rot=90, is_grid=False)
    cb.add_wire((140, 45), (140, 160))
    cb.add_wire((200, 75), (200, 160))
    cb.add_wire((260, 105), (260, 160))
    cb.add_junction(140, 45)
    cb.add_junction(200, 75)
    cb.add_junction(260, 105)
    
    # Thermorelais F1
    cb.add_node('F1_1', 'widerstand', x=140, y=300, rot=90, label='F1', is_grid=False)
    cb.add_node('F1_2', 'widerstand', x=200, y=300, rot=90, is_grid=False)
    cb.add_node('F1_3', 'widerstand', x=260, y=300, rot=90, is_grid=False)
    cb.add_wire((140, 280), (140, 300))
    cb.add_wire((200, 280), (200, 300))
    cb.add_wire((260, 280), (260, 300))
    
    # Motor M1 mit 6 Klemmen
    cb.add_node('M1', 'motor3', x=200, y=470, rot=0, label='M1', wert='U1,V1,W1 / U2,V2,W2', is_grid=False)
    cb.add_wire((140, 420), (200, 470))
    cb.add_wire((200, 420), (200, 470))
    cb.add_wire((260, 420), (200, 470))
    
    # Dreieckschuetz K2
    cb.add_node('K2_1', 'schliesser', x=380, y=160, rot=90, label='K2 (Dreieck)', is_grid=False)
    cb.add_node('K2_2', 'schliesser', x=440, y=160, rot=90, is_grid=False)
    cb.add_node('K2_3', 'schliesser', x=500, y=160, rot=90, is_grid=False)
    
    # Sternschuetz K3
    cb.add_node('K3_1', 'schliesser', x=380, y=320, rot=90, label='K3 (Stern)', is_grid=False)
    cb.add_node('K3_2', 'schliesser', x=440, y=320, rot=90, is_grid=False)
    cb.add_node('K3_3', 'schliesser', x=500, y=320, rot=90, is_grid=False)
    
    # Sternbruecke unten an K3
    cb.add_wire((380, 440), (500, 440))
    cb.add_junction(380, 440)
    cb.add_junction(440, 440)
    cb.add_junction(500, 440)
    
    return cb.render_svg()


def build_from_dsl(dsl_dict):
    """Baut eine Schaltung aus einem vollstaendigen DSL-Dictionary."""
    circuit = dsl_dict.get('circuit', dsl_dict)
    title = circuit.get('title', 'Schaltplan')
    cb = CircuitBuilder(title)
    
    for n in circuit.get('nodes', []):
        cb.add_node(
            node_id=n['id'],
            symbol=n['symbol'],
            x=n['x'],
            y=n['y'],
            rot=n.get('rot', 0),
            label=n.get('label'),
            wert=n.get('wert'),
            pins=n.get('pins'),
            farbe=n.get('farbe'),
            cls=n.get('cls'),
            is_grid=n.get('grid', True)
        )
        
    for w in circuit.get('wires', []):
        cb.add_wire(
            p_from=w['from'],
            p_to=w['to'],
            routing=w.get('routing', 'direct'),
            waypoints=w.get('waypoints'),
            farbe=w.get('farbe'),
            cls=w.get('cls'),
            sw=w.get('sw')
        )
        
    for j in circuit.get('junctions', []):
        cb.add_junction(j['x'], j['y'], farbe=j.get('farbe'), is_grid=j.get('grid', False))
        
    for a in circuit.get('arrows', []):
        atype = a.get('type', 'I')
        if atype == 'I':
            cb.add_arrow_i(a['x'], a['y'], direction=a.get('dir', 'r'), label=a.get('label', 'I'), farbe=a.get('farbe'))
        elif atype == 'U':
            cb.add_arrow_u(a['x1'], a['y1'], a['x2'], a['y2'], label=a.get('label', 'U'), farbe=a.get('farbe'))
            
    for t in circuit.get('texts', []):
        cb.add_text(t['text'], t['x'], t['y'], cls=t.get('cls', 'tx'), anchor=t.get('anchor', 'start'), size=t.get('size', 24), weight=t.get('weight', 600))
        
    return cb.render_svg()


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Normgerechter Schaltplan-Generator nach DIN EN 60617.")
    parser.add_argument('input', nargs='?', help='Pfad zu einer DSL-JSON-Datei')
    parser.add_argument('-o', '--output', help='Ausgabe-SVG-Datei')
    parser.add_argument('--preset', choices=[
        'grundstromkreis', 'graetz_bruecke', 'wendeschuetz_haupt',
        'wendeschuetz_steuer', 'sterndreieck_haupt'
    ], help='Erzeugt ein Standard-Preset')
    parser.add_argument('--list-symbols', action='store_true', help='Listet alle 180 verfuegbaren Schaltzeichen auf')
    
    args = parser.parse_args()
    
    if args.list_symbols:
        if INDEX_FILE.exists():
            with open(INDEX_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
            print(f"Verfuegbare Schaltsymbole ({len(data.get('zeichen', {}))}):")
            for k, v in sorted(data.get('zeichen', {}).items()):
                print(f"  - {k:<25} ({v.get('gruppe', '')}): {v.get('norm', '')[:70]}...")
        else:
            print(f"Index-Datei nicht gefunden: {INDEX_FILE}")
        return 0
        
    svg_content = None
    
    if args.preset:
        presets = {
            'grundstromkreis': build_preset_grundstromkreis,
            'graetz_bruecke': build_preset_graetz_bruecke,
            'wendeschuetz_haupt': build_preset_wendeschuetz_haupt,
            'wendeschuetz_steuer': build_preset_wendeschuetz_steuer,
            'sterndreieck_haupt': build_preset_sterndreieck_haupt,
        }
        svg_content = presets[args.preset]()
    elif args.input:
        with open(args.input, 'r', encoding='utf-8') as f:
            dsl = json.load(f)
        svg_content = build_from_dsl(dsl)
    else:
        parser.print_help()
        return 1
        
    if args.output:
        out_p = Path(args.output)
        out_p.parent.mkdir(parents=True, exist_ok=True)
        with open(out_p, 'w', encoding='utf-8') as f:
            f.write(svg_content)
        print(f"Schaltplan erfolgreich generiert: {out_p}")
    else:
        print(svg_content)
        
    return 0


if __name__ == '__main__':
    sys.exit(main())
