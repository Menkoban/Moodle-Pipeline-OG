<?php
// Moodle local_copilot MBZ Download Handler
require_once(__DIR__ . '/../../config.php');
require_login();

$courseid = optional_param('id', 0, PARAM_INT);
$filename = optional_param('file', '', PARAM_TEXT);

// Default directory for Moodle courses
$courses_dir = 'C:/Users/User/OneDrive - HSOS/Desktop/Moodle-Kurse';

// Look for .mbz file matching the course or newest .mbz
$target_file = null;

if ($courseid > 0) {
    global $DB;
    $course = $DB->get_record('course', ['id' => $courseid]);
    if ($course) {
        $shortname = strtolower($course->shortname);
        // Remove trailing _X copy suffixes if any
        $base_shortname = preg_replace('/_[0-9]+$/', '', $shortname);
        
        // Search in workspace
        $all_mbz = glob($courses_dir . '/*/*.mbz');
        foreach ($all_mbz as $mbz) {
            $mbz_name = strtolower(basename($mbz));
            if (strpos($mbz_name, $base_shortname) !== false || strpos(strtolower($mbz), $base_shortname) !== false) {
                $target_file = $mbz;
                break;
            }
        }
    }
}

// Fallback to the latest statistik course or most recently modified .mbz
if (!$target_file || !file_exists($target_file)) {
    $stat_mbz = $courses_dir . '/statistik-beschreibend-streuungsmasse/sicherung-moodle2-statistik-beschreibend-bgt.mbz';
    if (file_exists($stat_mbz)) {
        $target_file = $stat_mbz;
    } else {
        $all_mbz = glob($courses_dir . '/*/*.mbz');
        if (!empty($all_mbz)) {
            usort($all_mbz, function($a, $b) { return filemtime($b) - filemtime($a); });
            $target_file = $all_mbz[0];
        }
    }
}

if ($target_file && file_exists($target_file)) {
    $download_name = basename($target_file);
    $filesize = filesize($target_file);
    
    header('Content-Description: File Transfer');
    header('Content-Type: application/vnd.moodle.backup');
    header('Content-Disposition: attachment; filename="' . $download_name . '"');
    header('Expires: 0');
    header('Cache-Control: must-revalidate');
    header('Pragma: public');
    header('Content-Length: ' . $filesize);
    
    // Clear output buffer
    while (ob_get_level()) {
        ob_end_clean();
    }
    readfile($target_file);
    exit;
} else {
    echo "<h1>Keine Kurssicherung (.mbz) gefunden</h1>";
    echo "<p>Unter <code>" . htmlspecialchars($courses_dir) . "</code> wurde keine passende .mbz-Datei gefunden.</p>";
    exit;
}
