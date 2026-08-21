<?php
defined('MOODLE_INTERNAL') || die();

function local_copilot_before_standard_html_head() {
    global $PAGE, $COURSE;
    if ($COURSE && $COURSE->id > 1) {
        $PAGE->requires->css('/local/copilot/copilot.css');
        $PAGE->requires->js('/local/copilot/copilot.js', true);
    }
}
