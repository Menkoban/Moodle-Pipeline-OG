import os
import json
from scripts.hotspot_engine import generate_hotspot_html

def build(spec, output_path, base_dir="."):
    """
    Builds the hotspot HTML and saves it to output_path.
    """
    html_content = generate_hotspot_html(spec)
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html_content)
    print(f"Hotspot built successfully at: {output_path}")
    return output_path

if __name__ == "__main__":
    # Test execution
    test_spec = {
        "type": "hotspot",
        "title": "Interaktiver Schaltschrank: Bauteile erkunden",
        "subtitle": "Klicke auf die Komponenten...",
        "svg": "assets/schaltschrank.svg",
        "hotspots": [
            {
                "id": "q1",
                "x": 35.0, "y": 42.5,
                "title": "Motorschutzschalter Q1",
                "category": "Schutzorgan",
                "content": "Schützt den Antrieb vor thermischer Überlastung. Formel: \\( I^2t \\)",
                "details": {"Norm": "DIN EN 60947-4-1", "Einstellbereich": "1,0 - 1,6 A"}
            },
            {
                "id": "k1",
                "x": 50.0, "y": 62.5,
                "title": "Schütz K1",
                "category": "Schaltgerät",
                "content": "Schaltet den Hauptstromkreis.",
                "details": {"Norm": "DIN EN 60947-4-1"}
            }
        ]
    }
    
    # Create dummy SVG for testing
    os.makedirs("assets", exist_ok=True)
    dummy_svg = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 400" style="background:#ddd;">
        <rect id="q1" x="120" y="150" width="40" height="40" fill="#999" />
        <rect id="k1" x="180" y="230" width="40" height="40" fill="#777" />
    </svg>"""
    
    if not os.path.exists("assets/schaltschrank.svg"):
        with open("assets/schaltschrank.svg", "w", encoding="utf-8") as f:
            f.write(dummy_svg)
            
    build(test_spec, "assets/test_hotspot.html")
