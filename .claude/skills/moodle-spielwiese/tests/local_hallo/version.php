<?php
// local_hallo — Wegwerf-Plugin, Vertragsartefakt der Stufe 4.
// Zweck: belegt den Kreislauf link -> upgrade -> installiert sowie den
// gratis Erstinstallationstest nach jedem reset.
defined('MOODLE_INTERNAL') || die();

$plugin->component = 'local_hallo';
$plugin->version   = 2026071800;
$plugin->requires  = 2024100100; // Moodle 4.5
$plugin->maturity  = MATURITY_ALPHA;
$plugin->release   = '0.1';
