# -*- coding: utf-8 -*-
"""validate_section_completeness.py — Automatischer Prüffaktor fuer Moodle-Kacheln und Aktivitaeten."""
import json
import os
import subprocess
import sys

def validate_course_sections(course_id: int = 32) -> dict:
    php_exe = r"C:\moodle-playground\php\php.exe"
    check_script = r"""
    define('CLI_SCRIPT', true);
    require_once('C:/moodle-playground/moodle/config.php');
    global $DB;
    
    $cid = intval($argv[1]);
    $sections = $DB->get_records('course_sections', ['course' => $cid], 'section ASC');
    
    $results = [];
    foreach ($sections as $s) {
        $cms = $DB->get_records('course_modules', ['course' => $cid, 'section' => $s->id]);
        $modules_info = [];
        foreach ($cms as $cm) {
            $mod = $DB->get_record('modules', ['id' => $cm->module]);
            $modules_info[] = [
                'cm_id' => intval($cm->id),
                'module' => $mod->name,
                'visible' => intval($cm->visible)
            ];
        }
        $results[] = [
            'section_num' => intval($s->section),
            'section_id' => intval($s->id),
            'name' => $s->name,
            'activity_count' => count($cms),
            'activities' => $modules_info
        ];
    }
    echo json_encode($results);
    """
    
    cmd = [php_exe, "-r", check_script, str(course_id)]
    res = subprocess.run(cmd, capture_output=True, text=True)
    
    try:
        sections_data = json.loads(res.stdout)
    except Exception as e:
        return {"status": "error", "message": f"Parsing error: {e}", "raw": res.stdout}
        
    errors = []
    warnings = []
    
    for sec in sections_data:
        num = int(sec["section_num"])
        count = int(sec["activity_count"])
        name = sec["name"] or f"Section {num}"
        
        # Section 0 is general introduction
        if num > 0:
            if count == 0:
                errors.append(f"❌ FEHLER: Sektion #{num} ('{name}') ist VOLLSTÄNDIG LEER (0 Aktivitäten)!")
            elif count < 2 and num not in [6, 10]:
                warnings.append(f"⚠️ WARNUNG: Sektion #{num} ('{name}') hat nur {count} Aktivität (unter Mindeststandard von 2-4 Aktivitäten).")
                
    is_valid = len(errors) == 0
    return {
        "status": "success" if is_valid else "failed",
        "valid": is_valid,
        "total_sections": len(sections_data),
        "errors": errors,
        "warnings": warnings,
        "data": sections_data
    }

if __name__ == "__main__":
    cid = int(sys.argv[1]) if len(sys.argv) > 1 else 32
    res = validate_course_sections(cid)
    print(json.dumps(res, indent=2, ensure_ascii=False))
