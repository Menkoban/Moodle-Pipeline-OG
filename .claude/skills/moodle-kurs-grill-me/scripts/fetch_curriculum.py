import json
import os
import argparse
from pathlib import Path

# Base paths for both skills
BASE_PATHS = [
    Path(r"C:\Users\User\.gemini\config\skills\moodle-kurs-grill-me\references\curricula"),
    Path(r"C:\Users\User\.gemini\config\skills\moodle-mbz-builder\references\curricula")
]

def load_fachrichtung(fachrichtung_name, base_path):
    file_path = base_path / "fachrichtungen" / f"{fachrichtung_name.lower()}.json"
    if not file_path.exists():
        return None
    with open(file_path, "r", encoding="utf-8-sig") as f:
        return json.load(f)

def save_fachrichtung(fachrichtung_name, data):
    for base_path in BASE_PATHS:
        dir_path = base_path / "fachrichtungen"
        dir_path.mkdir(parents=True, exist_ok=True)
        file_path = dir_path / f"{fachrichtung_name.lower()}.json"
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
        print(f"Saved {fachrichtung_name} to {file_path}")

def search_and_cache_berufsfeld(fachrichtung_name, berufsfeld_name):
    print(f"Searching curriculum for '{berufsfeld_name}' in '{fachrichtung_name}'...")
    # Simulate API call / scraping
    # In a real scenario, this would fetch from a curriculum portal and parse the structure
    
    data = load_fachrichtung(fachrichtung_name, BASE_PATHS[0])
    if not data:
        data = {
            "fachrichtung": fachrichtung_name.capitalize(),
            "berufsfelder": []
        }
    
    if berufsfeld_name not in data.get("berufsfelder", []):
        data["berufsfelder"].append(berufsfeld_name)
        save_fachrichtung(fachrichtung_name, data)
        print(f"Successfully cached '{berufsfeld_name}' under '{fachrichtung_name}'.")
    else:
        print(f"'{berufsfeld_name}' already exists in '{fachrichtung_name}' cache.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Fetch and cache curriculum data.")
    parser.add_argument("--fachrichtung", type=str, required=True, help="Name of the Fachrichtung (e.g. Technik, Wirtschaft)")
    parser.add_argument("--berufsfeld", type=str, required=True, help="Name of the Berufsfeld/Lernfeld (e.g. Mechatronik, KFZ)")
    
    args = parser.parse_args()
    search_and_cache_berufsfeld(args.fachrichtung, args.berufsfeld)
