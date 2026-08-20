#!/usr/bin/env python3
"""Expand interactive-simulation activities in a course JSON into self-contained
HTML files wired in as Moodle **file resources**.

Use where a topic has a variable relationship worth exploring (Ohm's law,
series/parallel circuits, gear ratio, engine crank, dosage, interest, ...). Skip
where a topic has nothing to "drag" — a simulation there is noise, not value.

An activity opts in with:
    {"type": "simulation", "use": "reihenschaltung"}          # from SIM_LIBRARY
    {"type": "simulation", "name": "…", "spec": { … }}         # inline spec
For each such activity this tool renders the sim to `<dir>/<slug>.html` and
replaces the activity with a `resource` (single-file download) pointing at it, so
the JS actually runs (Moodle strips <script> from pages/book/database/labels; a
real file served from the file area runs it). Run BEFORE make_materials/build.

Usage:
    python build_simulation.py course.json -o course.sim.json
    python build_simulation.py --list
    python build_simulation.py --emit reihenschaltung -o sim.html
"""
import argparse, copy, json, os, re, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sim_engine  # noqa: E402
import form_engine  # noqa: E402
import hotspot_engine  # noqa: E402


def slugify(name):
    s = re.sub(r"[^a-zA-Z0-9]+", "_", (name or "simulation").strip()).strip("_").lower()
    return s or "simulation"


def resolve_spec(act):
    """Return the sim spec for a simulation activity (library name or inline)."""
    if act.get("spec"):
        return act["spec"]
    use = act.get("use") or act.get("sim")
    if use:
        if use not in sim_engine.SIM_LIBRARY:
            raise SystemExit(f"Unknown simulation '{use}'. Available: "
                             f"{', '.join(sorted(sim_engine.SIM_LIBRARY))}")
        return copy.deepcopy(sim_engine.SIM_LIBRARY[use])
    raise SystemExit("A 'simulation' activity needs either 'use' (library name) "
                     "or an inline 'spec'.")


def main():
    ap = argparse.ArgumentParser(description="Expand simulation activities into HTML file resources.")
    ap.add_argument("course_json", nargs="?")
    ap.add_argument("-o", "--output")
    ap.add_argument("--dir", default="sims", help="output subdir for generated .html (default: sims)")
    ap.add_argument("--list", action="store_true", help="list the built-in simulation library and exit")
    ap.add_argument("--emit", help="render one library simulation to a standalone file (needs -o)")
    args = ap.parse_args()

    if args.list:
        print("Built-in simulations (use with {\"type\":\"simulation\",\"use\":\"<name>\"}):")
        for name, spec in sorted(sim_engine.SIM_LIBRARY.items()):
            print(f"  - {name}: {spec.get('title','')}")
        return

    if args.emit:
        if args.emit not in sim_engine.SIM_LIBRARY:
            sys.exit(f"Unknown simulation '{args.emit}'. Available: "
                     f"{', '.join(sorted(sim_engine.SIM_LIBRARY))}")
        out = args.output or (args.emit + ".html")
        open(out, "w", encoding="utf-8").write(sim_engine.render(sim_engine.SIM_LIBRARY[args.emit]))
        print(f"Simulation geschrieben: {out}")
        return

    if not args.course_json:
        sys.exit("Provide a course JSON (or use --list / --emit).")

    base = os.path.dirname(os.path.abspath(args.course_json))
    outdir = os.path.join(base, args.dir)
    spec_course = json.load(open(args.course_json, encoding="utf-8"))

    count = 0
    sections = spec_course.get("course", {}).get("sections") if "course" in spec_course else spec_course.get("sections", [])
    for sec in sections:
        acts = []
        for act in sec.get("activities", []):
            if act.get("type") == "simulation":
                spec = resolve_spec(act)
                title = act.get("name") or spec.get("title", "Simulation")
                slug = slugify(act.get("name") or act.get("use") or spec.get("title"))
                os.makedirs(outdir, exist_ok=True)
                path = os.path.join(outdir, slug + ".html")
                open(path, "w", encoding="utf-8").write(sim_engine.render(spec))
                acts.append({
                    "type": "resource",
                    "name": title,
                    "intro": act.get("intro", "<p>Interaktive Simulation – Regler ziehen, Werte ändern sich sofort. Zum Öffnen anklicken.</p>"),
                    "file": path,
                    "completion": act.get("completion", 1),
                })
                count += 1
            elif act.get("type") == "formular":
                # Ausfüllbares Arbeitsblatt/Protokoll -> HTML-Datei-Ressource
                # (echte Eingabefelder + Autosave; siehe form_engine.py).
                fspec = act.get("spec") or {}
                title = act.get("name") or fspec.get("title", "Arbeitsblatt")
                fspec.setdefault("title", title)
                slug = slugify(act.get("name") or fspec.get("title"))
                os.makedirs(outdir, exist_ok=True)
                path = os.path.join(outdir, slug + ".html")
                open(path, "w", encoding="utf-8").write(form_engine.render(fspec))
                acts.append({
                    "type": "resource",
                    "name": title,
                    "intro": act.get("intro", "<p>Ausfüllbares Arbeitsblatt – deine Eingaben werden automatisch im Browser gespeichert; am Ende als Datei speichern oder drucken.</p>"),
                    "file": path,
                    "completion": act.get("completion", 1),
                })
                count += 1
            elif act.get("type") in ("hotspot", "hotspot_graphic"):
                # Interaktive Hotspot-Grafik (H5P-Stil) -> HTML-Datei-Ressource
                hspec = act.get("spec") or {}
                title = act.get("name") or hspec.get("title", "Interaktive Grafik")
                hspec.setdefault("title", title)
                if act.get("svg"):
                    hspec["svg"] = act["svg"]
                if act.get("hotspots"):
                    hspec["hotspots"] = act["hotspots"]
                slug = slugify(act.get("name") or hspec.get("title"))
                os.makedirs(outdir, exist_ok=True)
                path = os.path.join(outdir, slug + ".html")
                open(path, "w", encoding="utf-8").write(hotspot_engine.generate_hotspot_html(hspec))
                acts.append({
                    "type": "resource",
                    "name": title,
                    "intro": act.get("intro", "<p>Interaktive Grafik – klicke auf die pulsierenden Markierungen, um Bauteile, Messwerte und Details zu erkunden.</p>"),
                    "file": path,
                    "completion": act.get("completion", 1),
                })
                count += 1
            else:
                acts.append(act)
        sec["activities"] = acts

    out = args.output or (os.path.splitext(args.course_json)[0] + ".sim.json")
    json.dump(spec_course, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print(f"{count} Simulation(en) als Datei-Ressource eingebaut -> {outdir}")
    print(f"Kursdefinition mit Simulationen: {out}")


if __name__ == "__main__":
    main()
