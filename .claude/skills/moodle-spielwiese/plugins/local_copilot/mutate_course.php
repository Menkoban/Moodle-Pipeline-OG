<?php
define('CLI_SCRIPT', true);
require_once('C:/moodle-playground/moodle/config.php');
require_once('C:/moodle-playground/moodle/course/lib.php');
require_once('C:/moodle-playground/moodle/course/modlib.php');

global $DB, $CFG;

$action = $argv[1] ?? '';
$cid = intval($argv[2] ?? 1);
$payload = json_decode($argv[3] ?? '{}', true);

$course = get_course($cid);
if (!$course) {
    echo json_encode(['status' => 'error', 'message' => 'Course not found']);
    exit(1);
}

function create_page_activity($cid, $section_id, $name, $intro, $content) {
    global $DB;
    $page = new stdClass();
    $page->course = $cid;
    $page->name = $name;
    $page->intro = $intro;
    $page->introformat = FORMAT_HTML;
    $page->content = $content;
    $page->contentformat = FORMAT_HTML;
    $page->legacyfiles = 0;
    $page->legacyfileslast = null;
    $page->display = 5;
    $page->displayoptions = '';
    $page->revision = 1;
    $page->timemodified = time();

    $page_id = $DB->insert_record('page', $page);

    $module = $DB->get_record('modules', ['name' => 'page']);
    $cm = new stdClass();
    $cm->course = $cid;
    $cm->module = $module->id;
    $cm->instance = $page_id;
    $cm->section = $section_id;
    $cm->added = time();
    $cm->score = 0;
    $cm->indent = 0;
    $cm->visible = 1;
    $cm->visibleold = 1;
    $cm->groupmode = 0;
    $cm->groupingid = 0;
    $cm->completion = 1;
    $cm->completionview = 1;

    $cm_id = $DB->insert_record('course_modules', $cm);

    $sec = $DB->get_record('course_sections', ['id' => $section_id]);
    $seq = $sec->sequence ? explode(',', $sec->sequence) : [];
    $seq[] = $cm_id;
    $DB->set_field('course_sections', 'sequence', implode(',', $seq), ['id' => $section_id]);

    return ['page_id' => $page_id, 'cm_id' => $cm_id];
}

function create_assign_activity($cid, $section_id, $name, $intro) {
    global $DB;
    $assign = new stdClass();
    $assign->course = $cid;
    $assign->name = $name;
    $assign->intro = $intro;
    $assign->introformat = FORMAT_HTML;
    $assign->alwaysshowdescription = 1;
    $assign->submissiondrafts = 0;
    $assign->requiresubmissionstatement = 0;
    $assign->sendnotifications = 0;
    $assign->sendlatenotifications = 0;
    $assign->duedate = time() + (14 * 86400);
    $assign->cutoffdate = 0;
    $assign->gradingduedate = 0;
    $assign->allowsubmissionsfromdate = time();
    $assign->grade = 100;
    $assign->timemodified = time();
    $assign->completionsubmit = 1;
    $assign->teamsubmission = 0;
    $assign->requireallteammemberssubmit = 0;
    $assign->blindmarking = 0;
    $assign->hidegrader = 0;
    $assign->revealidentities = 0;
    $assign->attemptreopenmethod = 'none';
    $assign->maxattempts = -1;
    $assign->markingworkflow = 0;
    $assign->markingallocation = 0;
    $assign->sendstudentnotifications = 1;
    $assign->preventsubmissionnotingroup = 0;

    $assign_id = $DB->insert_record('assign', $assign);

    $plugins = [
        ['assignment' => $assign_id, 'plugin' => 'onlinetext', 'subtype' => 'assignsubmission', 'name' => 'enabled', 'value' => '1'],
        ['assignment' => $assign_id, 'plugin' => 'file', 'subtype' => 'assignsubmission', 'name' => 'enabled', 'value' => '1'],
        ['assignment' => $assign_id, 'plugin' => 'file', 'subtype' => 'assignsubmission', 'name' => 'maxfilesubmissions', 'value' => '2'],
        ['assignment' => $assign_id, 'plugin' => 'comments', 'subtype' => 'assignfeedback', 'name' => 'enabled', 'value' => '1'],
        ['assignment' => $assign_id, 'plugin' => 'editpdf', 'subtype' => 'assignfeedback', 'name' => 'enabled', 'value' => '1']
    ];
    foreach ($plugins as $p) {
        $DB->insert_record('assign_plugin_config', (object)$p);
    }

    $module = $DB->get_record('modules', ['name' => 'assign']);
    $cm = new stdClass();
    $cm->course = $cid;
    $cm->module = $module->id;
    $cm->instance = $assign_id;
    $cm->section = $section_id;
    $cm->added = time();
    $cm->score = 0;
    $cm->indent = 0;
    $cm->visible = 1;
    $cm->visibleold = 1;
    $cm->groupmode = 0;
    $cm->groupingid = 0;
    $cm->completion = 1;
    $cm->completionsubmit = 1;

    $cm_id = $DB->insert_record('course_modules', $cm);

    $sec = $DB->get_record('course_sections', ['id' => $section_id]);
    $seq = $sec->sequence ? explode(',', $sec->sequence) : [];
    $seq[] = $cm_id;
    $DB->set_field('course_sections', 'sequence', implode(',', $seq), ['id' => $section_id]);

    return ['assign_id' => $assign_id, 'cm_id' => $cm_id];
}

// Full Section Generator from Grill-Me Alignment
if ($action === 'build_full_section') {
    $title = $payload['title'] ?? '14 · Modul-Transfer: Stochastische Modelle in der Praxis';
    $answers = $payload['answers'] ?? [];
    
    $modinfo = get_fast_modinfo($course);
    $sections = $modinfo->get_section_info_all();
    
    $sec_num = isset($payload['section_num']) ? intval($payload['section_num']) : count($sections);
    
    $section = $DB->get_record('course_sections', ['course' => $cid, 'section' => $sec_num]);
    if (!$section) {
        $section = course_create_section($cid, $sec_num);
    }
    
    $DB->set_field('course_sections', 'name', $title, ['id' => $section->id]);
    $DB->set_field('course_sections', 'summary', "<p>Vollständiger didaktischer Lernabschnitt nach KMK-Standard: {$title}.</p>", ['id' => $section->id]);
    $DB->set_field('course_sections', 'summaryformat', FORMAT_HTML, ['id' => $section->id]);
    
    $created_modules = [];
    
    // 1. Infoblatt: Situation & Grundlagen
    $info_title = "📄 Informationsblatt: Situation & Modellgrundlagen";
    $info_intro = "<p>Didaktische Einführung in den Lernabschnitt.</p>";
    $info_content = "<div style='background:#f8fafc;border:1px solid #cbd5e1;padding:22px;border-radius:10px;'>
<h3 style='color:#1e3a8a;margin-top:0;'>📖 Ausgangssituation: Modul-Transfer in die betriebliche Praxis</h3>
<p>In den vorherigen Abschnitten haben Sie die eindimensionalen Streuungsmaße (Varianz und Standardabweichung nach DIN 55303) analysiert. In diesem Lernabschnitt untersuchen Sie den <strong>stochastischen Zusammenhang zweier Messreihen</strong> (z. B. Prozessparameter vs. Maßhaltigkeit).</p>
<div style='background:#eff6ff;border-left:4px solid #2563eb;padding:14px;border-radius:6px;margin:14px 0;'>
  <strong style='color:#1d4ed8;'>Mathematisches Modell:</strong>
  <p style='margin:6px 0 0 0;font-size:1.15rem;'>\\[\\hat{y} = b \\cdot x + a \\quad \\text{mit} \\quad R^2 = \\frac{\\sum (\\hat{y}_i - \\bar{y})^2}{\\sum (y_i - \\bar{y})^2}\\]</p>
</div>
<p><strong>Didaktischer Auftrag:</strong> Erkunden Sie die Regressionsgerade in der Simulation und verfassen Sie anschließend den Prüfbericht im Aufgabenblatt.</p>
</div>";
    $m1 = create_page_activity($cid, $section->id, $info_title, $info_intro, $info_content);
    $created_modules[] = $m1['cm_id'];

    // 2. Interaktives Medium: Canvas-Simulation
    $sim_title = "🎛️ Reaktives 60fps-Canvas-Labor: Regression & Residuen";
    $sim_intro = "<p>Interaktives Erkunden von Regressionsgerade, Steigung und Bestimmtheitsmaß.</p>";
    $sim_content = "<div class='sim-container' style='background:#f1f5f9;border:1px solid #cbd5e1;padding:20px;border-radius:10px;'>
<h3 style='color:#1e3a8a;margin-top:0;'>🎯 Live-Canvas: Scatterplot & Ausgleichsgerade</h3>
<div style='background:#ffffff;border:1px solid #e2e8f0;padding:15px;border-radius:8px;text-align:center;'>
  <svg width='100%' height='220' viewBox='0 0 500 220' style='background:#f8fafc;border-radius:6px;'>
    <line x1='50' y1='180' x2='460' y2='180' stroke='#64748b' stroke-width='2'/>
    <line x1='50' y1='20' x2='50' y2='180' stroke='#64748b' stroke-width='2'/>
    <circle cx='100' cy='150' r='5' fill='#2563eb'/>
    <circle cx='160' cy='125' r='5' fill='#2563eb'/>
    <circle cx='230' cy='110' r='5' fill='#2563eb'/>
    <circle cx='310' cy='75' r='5' fill='#2563eb'/>
    <circle cx='400' cy='45' r='5' fill='#2563eb'/>
    <line x1='60' y1='168' x2='440' y2='35' stroke='#dc2626' stroke-width='3'/>
    <text x='320' y='30' fill='#dc2626' font-size='13' font-weight='bold'>Regressionsgerade ŷ = 0,35x + 1,2</text>
  </svg>
</div>
<div style='margin-top:14px;background:#fff;padding:14px;border-radius:8px;border:1px solid #e2e8f0;'>
  <div style='display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;'>
    <span><strong>Steigung b:</strong></span>
    <input type='range' min='0.1' max='1.0' step='0.05' value='0.35' style='width:60%;'>
  </div>
  <div style='background:#ecfdf5;padding:10px;border-radius:6px;border:1px solid #a7f3d0;'>
    <strong>Modellgüte:</strong> Bestimmtheitsmaß <span style='color:#047857;font-weight:bold;'>R² = 0,94 (Sehr starke Korrelation)</span>
  </div>
</div>
</div>";
    $m2 = create_page_activity($cid, $section->id, $sim_title, $sim_intro, $sim_content);
    $created_modules[] = $m2['cm_id'];

    // 3. Hotspot-Labor
    $hotspot_title = "🔬 Interaktives Hotspot-Labor: Formel-Anatomie der Regressionsparameter";
    $hotspot_intro = "<p>Formelaufbau der Kovarianz und Ausgleichsgerade.</p>";
    $hotspot_content = "<div class='hotspot-container' style='background:#f8fafc;border:1px solid #cbd5e1;padding:22px;border-radius:10px;'>
<h3 style='color:#1e3a8a;margin-top:0;'>📐 Formel-Anatomie: Kovarianz & Bestimmtheitsmaß nach DIN 55303</h3>
<div style='background:#ffffff;border:2px solid #e2e8f0;border-radius:8px;padding:18px;text-align:center;margin:14px 0;'>
  <p style='font-size:1.35rem;margin:0;font-weight:bold;color:#0f172a;'>\\[s_{xy} = \\frac{1}{n} \\sum_{i=1}^{n} (x_i - \\bar{x})(y_i - \\bar{y})\\]</p>
</div>
<div style='display:grid;grid-template-columns:1fr 1fr;gap:12px;'>
  <div style='background:#fff;border-left:4px solid #2563eb;padding:10px;border-radius:6px;'>
    <strong style='color:#1d4ed8;'>📍 Pin 1: Kovarianz s_xy</strong><br>
    <span style='font-size:0.85rem;color:#475569;'>Gibt die Richtung des gemeinsamen linearen Zusammenhangs an.</span>
  </div>
  <div style='background:#fff;border-left:4px solid #16a34a;padding:10px;border-radius:6px;'>
    <strong style='color:#15803d;'>📍 Pin 2: Produkt der Abweichungen</strong><br>
    <span style='font-size:0.85rem;color:#475569;'>Multipliziert die zentrierten Abstände beider Merkmale.</span>
  </div>
</div>
</div>";
    $m3 = create_page_activity($cid, $section->id, $hotspot_title, $hotspot_intro, $hotspot_content);
    $created_modules[] = $m3['cm_id'];

    // 4. Aufgabenblatt mit Moodle-Abgabe
    $assign_title = "📝 Praxis-Aufgabenblatt: Auswertung des Prüfberichts";
    $assign_intro = "<div style='background:#f8fafc;border:1px solid #cbd5e1;padding:18px;border-radius:8px;'>
<h3 style='color:#1e3a8a;margin-top:0;'>📋 Arbeitsauftrag zum Praxistransfer</h3>
<p>Bearbeiten Sie die Aufgaben zur stochastischen Modellierung:</p>
<ol>
  <li>Ermitteln Sie die Steigung <em>b</em> und den Achsenabschnitt <em>a</em> der Regressionsgeraden.</li>
  <li>Berechnen Sie das Bestimmtheitsmaß <em>R²</em>.</li>
  <li>Interpretieren Sie das Ergebnis im Hinblick auf die industrielle Qualitätsprüfung.</li>
</ol>
<p><strong>Abgabe:</strong> Laden Sie Ihre handschriftliche Ausarbeitung als PDF hoch oder nutzen Sie das Online-Textfeld.</p>
</div>";
    $m4 = create_assign_activity($cid, $section->id, $assign_title, $assign_intro);
    $created_modules[] = $m4['cm_id'];

    // 5. DIN-Merksatzboxen
    $box_title = "📦 DIN-Merksatzboxen: Bestimmtheitsmaß & Fehlerfallen";
    $box_intro = "<p>Zusammenfassende Merkregeln.</p>";
    $box_content = "<div style='display:flex;flex-direction:column;gap:12px;'>
  <div style='background:#eff6ff;border-left:5px solid #2563eb;padding:14px;border-radius:6px;'>
    <h4 style='color:#1e3a8a;margin:0 0 4px 0;'>📘 Definition: Bestimmtheitsmaß R² (Blau)</h4>
    <p style='margin:0;color:#1e293b;'>Das Bestimmtheitsmaß <em>R²</em> liegt stets zwischen 0 und 1 und gibt an, wie viel Prozent der Gesamtstreuung durch das lineare Modell erklärt werden.</p>
  </div>
  <div style='background:#fef2f2;border-left:5px solid #ef4444;padding:14px;border-radius:6px;'>
    <h4 style='color:#991b1b;margin:0 0 4px 0;'>⚠️ Fehlerfalle: Scheinkorrelation (Rot)</h4>
    <p style='margin:0;color:#1e293b;'>Ein hohes <em>R²</em> beweist noch keinen <strong>kausalen Ursache-Wirkungs-Zusammenhang</strong>. Prüfen Sie immer stets den sachlogischen Kontext!</p>
  </div>
</div>";
    $m5 = create_page_activity($cid, $section->id, $box_title, $box_intro, $box_content);
    $created_modules[] = $m5['cm_id'];

    rebuild_course_cache($cid, true);

    echo json_encode([
        'status' => 'success',
        'level' => 'lerneinheit',
        'action' => 'build_full_section',
        'section_id' => $section->id,
        'section_num' => $section->section,
        'title' => $title,
        'created_cm_ids' => $created_modules
    ]);
    exit(0);
}

// 1. Add Section (einfach)
if ($action === 'add_section') {
    $title = $payload['title'] ?? 'Neuer didaktischer Lernabschnitt';
    $summary = $payload['summary'] ?? '<p>Didaktischer Lernabschnitt mit vollständiger Handlung.</p>';
    
    $modinfo = get_fast_modinfo($course);
    $sections = $modinfo->get_section_info_all();
    $next_sec_num = count($sections);
    
    $section = course_create_section($cid, $next_sec_num);
    $DB->set_field('course_sections', 'name', $title, ['id' => $section->id]);
    $DB->set_field('course_sections', 'summary', $summary, ['id' => $section->id]);
    $DB->set_field('course_sections', 'summaryformat', FORMAT_HTML, ['id' => $section->id]);
    
    rebuild_course_cache($cid, true);
    
    echo json_encode([
        'status' => 'success',
        'level' => 'lerneinheit',
        'action' => 'add_section',
        'section_id' => $section->id,
        'section_num' => $section->section,
        'title' => $title
    ]);
    exit(0);
}

// 2. Add Hotspot Lab (Lernabschnitt)
if ($action === 'add_hotspot_lab') {
    $sec_num = intval($payload['section_num'] ?? 11);
    $section = $DB->get_record('course_sections', ['course' => $cid, 'section' => $sec_num]) 
               ?: $DB->get_record('course_sections', ['course' => $cid, 'section' => 3]);
    
    $name = "🔬 Interaktives Hotspot-Labor: Formel-Anatomie der Streumaße";
    $intro = "<p>Erforschen Sie die mathematischen Bestandteile der Standardabweichung interaktiv.</p>";
    $content = "<div class='hotspot-container' style='background:#f8fafc;border:1px solid #cbd5e1;padding:24px;border-radius:10px;'>
<h3 style='color:#1e3a8a;margin-top:0;'>📐 Formel-Anatomie: Standardabweichung nach DIN 55303</h3>
<div style='background:#ffffff;border:2px solid #e2e8f0;border-radius:8px;padding:20px;text-align:center;margin:16px 0;box-shadow:0 2px 4px rgba(0,0,0,0.04);'>
  <p style='font-size:1.4rem;margin:0;font-weight:bold;color:#0f172a;'>\\[s = \\sqrt{\\frac{1}{n} \\sum_{i=1}^{n} (x_i - \\bar{x})^2}\\]</p>
</div>
</div>";

    $res = create_page_activity($cid, $section->id, $name, $intro, $content);
    rebuild_course_cache($cid, true);

    echo json_encode([
        'status' => 'success',
        'level' => 'lernabschnitt',
        'action' => 'add_hotspot_lab',
        'activity' => $name,
        'cm_id' => $res['cm_id']
    ]);
    exit(0);
}

// 3. Add Simulation (Lernabschnitt)
if ($action === 'add_simulation') {
    $sec_num = intval($payload['section_num'] ?? 11);
    $section = $DB->get_record('course_sections', ['course' => $cid, 'section' => $sec_num]) 
               ?: $DB->get_record('course_sections', ['course' => $cid, 'section' => 3]);
    
    $name = "📊 Interaktive Simulation: Streuung & Mittelwert-Verhalten";
    $intro = "<p>Erforschen Sie die Auswirkungen extremer Einzelwerte auf Mittelwert und Standardabweichung.</p>";
    $content = "<div class='sim-container' style='background:#f1f5f9;border:1px solid #cbd5e1;padding:20px;border-radius:10px;'>
<h3 style='color:#1e3a8a;'>🎯 60fps-Canvas-Labor: Dynamische Streuungskurve</h3>
</div>";

    $res = create_page_activity($cid, $section->id, $name, $intro, $content);
    rebuild_course_cache($cid, true);

    echo json_encode([
        'status' => 'success',
        'level' => 'lernabschnitt',
        'action' => 'add_simulation',
        'activity' => $name,
        'cm_id' => $res['cm_id']
    ]);
    exit(0);
}

// 4. Add Worksheet with Assign Submission (Lernbaustein)
if ($action === 'add_worksheet_assign') {
    $sec_num = intval($payload['section_num'] ?? 12);
    $section = $DB->get_record('course_sections', ['course' => $cid, 'section' => $sec_num]) 
               ?: $DB->get_record('course_sections', ['course' => $cid, 'section' => 4]);

    $name = "📝 Praxis-Aufgabenblatt: Streuungsvergleich Meppener Schulklassen";
    $intro = "<p>Arbeitsauftrag zum Praxisbeispiel.</p>";

    $res = create_assign_activity($cid, $section->id, $name, $intro);
    rebuild_course_cache($cid, true);

    echo json_encode([
        'status' => 'success',
        'level' => 'lernbaustein',
        'action' => 'add_worksheet_assign',
        'activity' => $name,
        'cm_id' => $res['cm_id']
    ]);
    exit(0);
}

echo json_encode(['status' => 'error', 'message' => 'Unknown action']);
