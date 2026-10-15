# bettersorted – Social-Media-Tooling

Alles, um Reels, Karussells und Bilder im bettersorted-Design zu erzeugen, über Postiz einzuplanen und die Performance auszuwerten.

## Ordner
| Pfad | Inhalt |
|---|---|
| `render_reel.py` | Reel-Generator (1080×1920, 20 s, 30 fps, mit Sound). `CONTENT=<modul> python3 render_reel.py <nr,nr\|all> <ausgabe>` |
| `render_slides.py` | Karussell-/Bild-Generator (PNG je Slide + PDF). `python3 render_slides.py <spec.json> <ausgabe>` |
| `music.py` | Erzeugt den lizenzfreien Hausklang `assets/sound.wav` neu (nur bei Bedarf) |
| `assets/` | Logo (`logo.jpeg`), Sound (`sound.wav`) |
| `content/` | Inhalte: Reel-Serien als Python-Module (`serie1_loesungen.py`, `serie2_agenten.py`), Karussells als JSON |
| `posts/` | Posting-Texte und Titel der bisherigen Serien |
| `performance/redaktionsplan.csv` | Was wann wo läuft |
| `performance/kennzahlen.csv` | Kennzahlen je Post (wird bei jedem Review ergänzt) |
| `performance/learnings.md` | Erkenntnisse aus den Reviews – was funktioniert, was nicht |

## Voraussetzungen
Python 3 mit Pillow, NumPy, SciPy; ffmpeg; Schrift Inter (`/usr/share/fonts/opentype/inter/`).

## Medien veröffentlichen
Fertige Dateien nach `media/<datum>-<slug>/` committen und pushen. Postiz holt sie über
`https://raw.githubusercontent.com/muhamedalahmed/bettersorted-reels/main/<pfad>` (Repo muss dafür öffentlich sein).
