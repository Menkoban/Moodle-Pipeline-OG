# shared — Hilfsmodule für den Curriculum-Abruf

Diese drei Module sind eine **Kopie** aus dem Repo
[`Menkoban/shared`](https://github.com/Menkoban/shared) (Stand `bd08eb0`,
23.08.2026). Sie werden in der Moodle-Pipeline nur von
`moodle-kurs-grill-me/scripts/fetch_curriculum.py` und dessen Tests gebraucht,
die diesen Ordner als Geschwisterordner (`../shared`) einbinden.

| Modul | Zweck |
|---|---|
| `pipeline_common.py` | `slugify` und weitere kleine Helfer |
| `retrieval.py` | Lehrpläne von amtlichen Quellen laden, Text extrahieren, Cache |
| `curriculum_parser.py` | Lernfelder aus dem Lehrplantext herauslesen |

`Menkoban/shared` selbst bleibt bestehen: Es ist die Bibliothek der
Unterrichtsplanungs-Pipeline und wird dort von 17 Skills und dem Orchestrator
genutzt. Änderungen an diesen drei Modulen gelten ab jetzt nur für die
Moodle-Pipeline.

Abgerufene Lehrpläne landen in `cache/` (nicht im Repo, siehe `.gitignore`).
