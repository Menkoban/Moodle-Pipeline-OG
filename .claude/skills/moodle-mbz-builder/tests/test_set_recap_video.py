import json
import os
import subprocess
import sys

SCRIPT = os.path.join(os.path.dirname(__file__), "..", "scripts", "set_recap_video.py")

SPEC = {"course": {"fullname": "Demo"}, "sections": [
    {"name": "5 Kurs-Recap", "activities": [
        {"type": "page", "name": "Das Wichtigste in Kürze", "content": "<p>...</p>"},
        {"type": "label", "name": "Videozusammenfassung (folgt)",
         "intro": "<p>Platzhalter – wird mit NotebookLM erstellt.</p>"}]}]}


def run(args, cwd):
    return subprocess.run([sys.executable, SCRIPT] + args, cwd=cwd,
                          capture_output=True, text=True)


def _write_spec(tmp_path):
    p = tmp_path / "course.json"
    p.write_text(json.dumps(SPEC, ensure_ascii=False), encoding="utf-8")
    return p


def test_url_replaces_placeholder(tmp_path):
    p = _write_spec(tmp_path)
    r = run([str(p), "--url", "https://notebooklm.google.com/notebook/abc"], tmp_path)
    assert r.returncode == 0, r.stderr
    spec = json.loads(p.read_text(encoding="utf-8"))
    acts = spec["sections"][0]["activities"]
    assert acts[1]["type"] == "url"
    assert acts[1]["externalurl"].startswith("https://notebooklm")
    assert acts[1]["name"] == "Videozusammenfassung"
    # Nachbar-Aktivitaet unangetastet
    assert acts[0]["name"] == "Das Wichtigste in Kürze"


def test_file_replaces_placeholder(tmp_path):
    p = _write_spec(tmp_path)
    mp4 = tmp_path / "recap.mp4"
    mp4.write_bytes(b"\x00fakevideo")
    r = run([str(p), "--file", str(mp4)], tmp_path)
    assert r.returncode == 0, r.stderr
    spec = json.loads(p.read_text(encoding="utf-8"))
    act = spec["sections"][0]["activities"][1]
    assert act["type"] == "resource" and act["file"] == str(mp4)


def test_missing_file_fails(tmp_path):
    p = _write_spec(tmp_path)
    r = run([str(p), "--file", str(tmp_path / "gibtsnicht.mp4")], tmp_path)
    assert r.returncode != 0


def test_no_placeholder_fails_cleanly(tmp_path):
    p = tmp_path / "leer.json"
    p.write_text(json.dumps({"course": {}, "sections": [
        {"name": "X", "activities": [{"type": "page", "name": "Nur Text"}]}]}),
        encoding="utf-8")
    r = run([str(p), "--url", "https://x"], tmp_path)
    assert r.returncode != 0
    assert "Kein" in (r.stderr + r.stdout)


def test_rerun_updates_video(tmp_path):
    p = _write_spec(tmp_path)
    run([str(p), "--url", "https://alt"], tmp_path)
    r = run([str(p), "--url", "https://neu"], tmp_path)
    assert r.returncode == 0, r.stderr
    spec = json.loads(p.read_text(encoding="utf-8"))
    assert spec["sections"][0]["activities"][1]["externalurl"] == "https://neu"
