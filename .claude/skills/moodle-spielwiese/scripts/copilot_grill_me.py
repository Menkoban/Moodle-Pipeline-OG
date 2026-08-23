# -*- coding: utf-8 -*-
"""copilot_grill_me.py — In-Overlay 6-Cluster Grill-Me Alignment Engine fuer Moodle."""
import json
import os
import re

CLUSTERS = [
    {
        "id": 1,
        "name": "Lerngruppe & Curriculares Profil",
        "question": "Für welche <strong>Lerngruppe und Schulform</strong> soll der neue Lernabschnitt konzipiert werden?",
        "options": [
            "(Empfohlen) BBS Meppen · Fachoberschule Wirtschaft & Technik (2. Ausbildungsjahr)",
            "Berufsschule Dual · Kaufleute für Groß- und Außenhandelsmanagement (Mittelstufe)",
            "Berufliches Gymnasium · Klasse 11 (MINT-Schwerpunkt)"
        ]
    },
    {
        "id": 2,
        "name": "Handlungssituation & Problemstellung",
        "question": "Wie soll die <strong>Handlungssituation (Continuous Narrative)</strong> gestaltet sein?",
        "options": [
            "(Empfohlen) Fortführung des Meppener Notenstreits (Vergleich zweier Abteilungen)",
            "Neues Industrieszenario: Qualitätsprüfung in der Serienfertigung (DIN 55303)",
            "Betriebswirtschaftliche Fallanalyse: Kundenbewertungen und Streuung"
        ]
    },
    {
        "id": 3,
        "name": "Fachinhalte, Berechnungen & Normen",
        "question": "Welche <strong>mathematischen Fachinhalte und Normen</strong> stehen im Mittelpunkt?",
        "options": [
            "(Empfohlen) Zweidimensionale Streuung: Kovarianz & Scatterplots nach DIN 55303",
            "Robuste Lage- & Streumaße: Median, Quartile, Interquartilsabstand (IQR) & Boxplots",
            "Lineare Regression: Regressionsgerade, Residuen & Bestimmtheitsmaß R²"
        ]
    },
    {
        "id": 4,
        "name": "Aufgaben-Architektur & Moodle-Aktivitäten",
        "question": "Welche <strong>Aufgaben-Architektur</strong> soll verankert werden?",
        "options": [
            "(Empfohlen) Inbox-Primat: Reales Aufgabenblatt mit Moodle-Abgabe (mod_assign) + Lehrer-Lösungsdossier",
            "Digitales Prüfprotokoll (type: formular) mit 6-Schritte-Rechner & Validierung",
            "Summatives ZDQ-Assessment: 10 kompetenzorientierte Prüffragen mit Feedback"
        ]
    },
    {
        "id": 5,
        "name": "Interaktive Medien-Trias",
        "question": "Welches <strong>interaktive Medium</strong> soll direkt eingebettet werden?",
        "options": [
            "(Empfohlen) 60fps-Canvas-Simulation + Hotspot-Formellabor (Pins in Safe-Zone y=14%)",
            "Nur Hotspot-Labor: Formel-Anatomie mit 4 farbcodierten Pins",
            "Nur Reaktive HTML5-Canvas-Simulation mit Schiebereglern und Challenge"
        ]
    },
    {
        "id": 6,
        "name": "Kachelstruktur & Deckblatt",
        "question": "Unter welchem <strong>Kacheltitel</strong> soll der Abschnitt angelegt werden?",
        "options": [
            "(Empfohlen) 14 · Vertiefung: Mehrdimensionale Streuungsvergleiche & Scatterplots",
            "14 · Praxisauftrag: Industrieller Qualitätsprüfbericht & Kovarianz",
            "14 · Modul-Transfer: Stochastische Modelle in der Praxis"
        ]
    }
]

# Session storage per course_id
sessions = {}

def extract_smart_skips(prompt: str) -> dict:
    """Extrahiert Vorab-Informationen aus dem Initial-Prompt (Smart Skip)."""
    p_lower = prompt.lower()
    answers = {}
    
    # Cluster 1: Lerngruppe
    if "meppen" in p_lower or "fachoberschule" in p_lower or "fos" in p_lower:
        answers[1] = "BBS Meppen · Fachoberschule"
    elif "berufsschule" in p_lower or "dual" in p_lower:
        answers[1] = "Berufsschule Dual"
    elif "gymnasium" in p_lower:
        answers[1] = "Berufliches Gymnasium"

    # Cluster 2: Handlungssituation
    if "notenstreit" in p_lower:
        answers[2] = "Fortführung des Meppener Notenstreits"
    elif "industrie" in p_lower or "qualität" in p_lower or "fertigung" in p_lower:
        answers[2] = "Industrieszenario: Qualitätsprüfung"

    # Cluster 3: Fachinhalte
    if "scatter" in p_lower or "mehrdimensional" in p_lower or "kovarianz" in p_lower:
        answers[3] = "Zweidimensionale Streuung & Scatterplots"
    elif "boxplot" in p_lower or "quartil" in p_lower or "iqr" in p_lower:
        answers[3] = "Boxplots & Interquartilsabstand"
    elif "regression" in p_lower:
        answers[3] = "Lineare Regression"

    # Cluster 4: Aufgaben
    if "abgabe" in p_lower or "assign" in p_lower or "aufgabenblatt" in p_lower:
        answers[4] = "Aufgabenblatt mit mod_assign + Lehrer-Dossier"
    elif "protokoll" in p_lower or "formular" in p_lower:
        answers[4] = "Digitales Prüfprotokoll"

    # Cluster 5: Medien
    if "simulation" in p_lower and "hotspot" in p_lower:
        answers[5] = "60fps-Canvas-Simulation + Hotspot-Labor"
    elif "simulation" in p_lower or "canvas" in p_lower:
        answers[5] = "Reaktive Canvas-Simulation"
    elif "hotspot" in p_lower:
        answers[5] = "Hotspot-Labor"

    # Cluster 6: Titel
    if prompt.strip().startswith("14 · ") or prompt.strip().startswith("15 · "):
        answers[6] = prompt.strip()
    elif ":" in prompt and ("kachel" in p_lower or "abschnitt" in p_lower):
        answers[6] = "14 · " + prompt.split(":", 1)[1].strip()

    return answers

def start_or_advance_grill_me(course_id: int, user_input: str) -> tuple[str, bool, dict]:
    """
    Steuert den Grill-Me-Prozess fuer den Kurs.
    Gibt (html_reply, is_complete, payload) zurueck.
    """
    session = sessions.get(course_id)
    
    # Neue Session starten
    if not session or user_input.lower().strip() in ["neue kachel konzipieren", "+ lernabschnitt anfügen", "grill-me starten"]:
        pre_answers = extract_smart_skips(user_input)
        session = {
            "current_cluster": 1,
            "answers": pre_answers
        }
        sessions[course_id] = session

    # Wenn bereits eine Session laeuft und eine Antwort reinkommt
    elif session and session["current_cluster"] <= len(CLUSTERS):
        curr_id = session["current_cluster"]
        # Bereinige die Antwort (z. B. "(Empfohlen) " entfernen)
        clean_ans = user_input.replace("(Empfohlen) ", "").strip()
        session["answers"][curr_id] = clean_ans
        session["current_cluster"] += 1

    # Finde den naechsten offenen Cluster (Smart Skip)
    while session["current_cluster"] <= len(CLUSTERS):
        c_id = session["current_cluster"]
        if c_id in session["answers"]:
            session["current_cluster"] += 1
        else:
            break

    # Alle 6 Cluster beantwortet -> Bauen & Abschließen!
    if session["current_cluster"] > len(CLUSTERS):
        title = session["answers"].get(6, "14 · Vertiefung: Mehrdimensionale Streuungsvergleiche & Scatterplots")
        payload = {
            "title": title,
            "answers": session["answers"]
        }
        sessions.pop(course_id, None) # Session beenden
        
        reply_html = (
            "<span class='copilot-action-badge'>🎯 Grill-Me · 6-Cluster-Alignment abgeschlossen</span><br>"
            "✅ <strong>Didaktischer Kurs-Steckbrief erfolgreich abgestimmt & validiert!</strong><br><br>"
            f"• <strong>Lerngruppe:</strong> {session['answers'].get(1, 'BBS Meppen')}<br>"
            f"• <strong>Handlungssituation:</strong> {session['answers'].get(2, 'Continuous Narrative')}<br>"
            f"• <strong>Fachinhalte:</strong> {session['answers'].get(3, 'DIN 55303')}<br>"
            f"• <strong>Aufgaben:</strong> {session['answers'].get(4, 'mod_assign')}<br>"
            f"• <strong>Medien:</strong> {session['answers'].get(5, 'Medien-Trias')}<br>"
            f"• <strong>Kacheltitel:</strong> {title}<br><br>"
            "⚡ <em>Erstelle jetzt die Kachel samt interaktiven Aktivitäten und lade die Seite neu...</em>"
        )
        return reply_html, True, payload

    # Naechste Frage rendern
    cluster_idx = session["current_cluster"] - 1
    cluster = CLUSTERS[cluster_idx]
    
    options_html = ""
    for opt in cluster["options"]:
        is_rec = "(Empfohlen)" in opt
        bg = "#eff6ff" if is_rec else "#f8fafc"
        border = "#bfdbfe" if is_rec else "#e2e8f0"
        color = "#1e40af" if is_rec else "#334155"
        weight = "600" if is_rec else "500"
        
        options_html += f"""
        <button class='copilot-choice-btn' data-title='{opt}' style='background:{bg};border:1px solid {border};border-radius:6px;padding:8px 10px;text-align:left;font-size:0.80rem;cursor:pointer;color:{color};font-weight:{weight};'>
          {opt}
        </button>
        """

    reply_html = f"""
    <span class='copilot-action-badge'>🎯 Grill-Me · Schritt {cluster['id']} von 6</span><br>
    <strong style='color:#0f172a;'>Cluster {cluster['id']}: {cluster['name']}</strong><br><br>
    {cluster['question']}<br><br>
    <div style='display:flex; flex-direction:column; gap:6px;'>
      {options_html}
    </div><br>
    <span style='font-size:0.75rem; color:#64748b;'>💡 Du kannst eine Option anklicken oder frei per Spracheingabe antworten.</span>
    """

    return reply_html, False, {}
