
---
title: Vectorizer Pro
emoji: 🖼️
colorFrom: blue
colorTo: purple
sdk: docker
app_port: 7860
---

<div align="center">

<h1>Vectorizer Pro 🖼️➡️🧩</h1>

<p><b>Wandle Logos/Grafiken in saubere, hochqualitative SVGs um — mit Live‑Fortschritt, Advanced Settings und 1‑Klick PNG/PDF‑Export.</b></p>

<p>
  <a href="#-quick-start"><img alt="Quick Start" src="https://img.shields.io/badge/Quick%20Start-1%20Minute-brightgreen?style=for-the-badge"/></a>
  <a href="#-deploy"><img alt="Deploy" src="https://img.shields.io/badge/Deploy-Hugging%20Face%20Spaces-blue?style=for-the-badge&logo=huggingface"/></a>
  <a href="#-license"><img alt="License" src="https://img.shields.io/badge/License-MIT-black?style=for-the-badge"/></a>
  <a href="https://github.com/Bandrik0/Vectorizer"><img alt="Repo" src="https://img.shields.io/badge/GitHub-Vectorizer-black?style=for-the-badge&logo=github"/></a>
 </p>

</div>

---

## ✨ Highlights

---

## ✨ Highlights
- **Pixel‑perfect vectorization** powered by **Potrace** (smooth Bézier curves, inner holes preserved)
- **Transparent background** by default; no stray borders
- **Live progress & activity log** (no more “stuck at 86%” vibes)
- **Advanced Settings**: quality presets, PNG pixel width & DPI, fill color
- **Smart exports**: SVG + high‑DPI **PNG** + vector **PDF** (Inkscape → librsvg → CairoSVG fallback)
- **Modern UI** (Bootstrap), drag‑free simple upload, instant download links

---

## 🧠 How it works
1. Your image (PNG/JPG with or without alpha) is uploaded.  
2. We build a **smart mask** (alpha or K‑means if no alpha), clean tiny components, remove border hairlines.  
3. The mask is upscaled and traced by **Potrace** into smooth vector paths (fill rule: even‑odd).  
4. SVG is produced in your chosen **fill color**.  
5. Optional **PNG** (transparent, cropped to drawing) and **PDF** are exported with the best available tool on your system.

---

## 🚀 Quick Start

### 1) System dependencies
You need **Potrace** (required) and *optionally* Inkscape or librsvg for top‑quality exports.

**macOS (Homebrew)**
```bash
brew install potrace
# optional, recommended for best PNG/PDF:
brew install inkscape
# optional alternative:
brew install librsvg
```

**Linux (Debian/Ubuntu)**
```bash
sudo apt-get update
sudo apt-get install -y potrace
# optional:
sudo apt-get install -y inkscape
# or:
sudo apt-get install -y librsvg2-bin
```

**Windows**
- Potrace: https://potrace.sourceforge.net/#downloading  
- Inkscape: https://inkscape.org/  
- (Optional) rsvg-convert via MSYS2 (advanced)

### 2) Python setup
```bash
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 3) Run the app
```bash
python3 app.py
# open http://127.0.0.1:5000
```

---

## 🛠️ Advanced Settings (UI)
- **Quality**: `Fast | Print | Ultra`  
  Controls Potrace fidelity and curve smoothing.
- **PNG Width (px)**: `0 = Auto` (uses DPI).  
  Set **4000–8000 px** for ultra‑crisp PNGs.
- **PNG DPI**: Used when width is Auto (e.g., **1200 DPI** for print).
- **Fill Color**: Applies to SVG paths (default `#C59A52`).

All values are sent to the backend and applied per‑request. Defaults live at the top of `app.py`.

---

## 🧪 Quality Presets

| Preset | scale_up | alphamax | opttolerance | turdsize | turnpolicy |
|:------:|:--------:|:--------:|:------------:|:--------:|:----------:|
| **Fast**  | 6  | 1.25 | 0.18 | 2 | minority |
| **Print** | 8  | 1.35 | 0.16 | 1 | minority |
| **Ultra** | 12 | 1.38 | 0.15 | 1 | minority |

> Tip: Increase **PNG Width (px)** to 5000–8000 for razor‑sharp raster exports. DPI matters only when width is Auto.

---

## 📤 Exports
- **SVG** — vector paths, transparent background, even‑odd holes, fill color configurable  
- **PNG** — transparent, cropped to drawing area, exact px width or DPI  
- **PDF** — vector, cropped to drawing area

Export tool order: **Inkscape → rsvg‑convert → CairoSVG** (automatic fallback).

---

## 📁 Project Structure
```
projekt/
├─ app.py                    # Flask server + progress & threading
├─ vectorizer.py             # Potrace-based vectorization + exports
├─ requirements.txt
├─ templates/
│  └─ index.html             # UI + Advanced Settings
├─ static/
│  ├─ script.js              # Progress polling, form submission
│  └─ style.css
├─ uploads/                  # (gitignored) incoming files
└─ outputs/                  # (gitignored) generated SVG/PNG/PDF
```

---

## 🔌 API (internal)
- `POST /upload` – multipart form with:
  - `file` (required)
  - `quality` (`fast|print|ultra`)
  - `png_width_px` (int; 0=Auto)
  - `png_dpi` (int)
  - `fill_color` (hex)
- `GET /progress` – JSON progress: `{ percent, status, logs[], done, files{} }`
- `GET /download/<filename>` – download generated file

---

## 🧰 Troubleshooting

**“potrace not found”**  
Install Potrace and ensure it’s on PATH:  
`brew install potrace` (macOS) or `sudo apt-get install potrace` (Linux).  
Windows: install Potrace and add its folder to PATH.

**PNG looks soft / “unscharf”**  
Set **PNG Width (px)** to **5000–8000** instead of relying on DPI.  
Inkscape export uses `--export-area-drawing` + transparent background.

**Progress stuck at 86%**  
That’s the PNG export phase. We now stream progress (86→92) until the tool finishes.

**Thin lines at top/left edges**  
We erase a small border in the mask to avoid hairlines. If you still see them, increase the border from 2→3 px in `vectorizer.py` (`_smart_mask`).

**PDF/PNG missing**  
Install Inkscape or librsvg. CairoSVG is used as a fallback (`pip install cairosvg`) but may need system Cairo libs on some distros.

---

## 🧪 Local Development
- App runs on **Flask** with **threaded** background processing.
- Live logs are streamed to UI via periodic polling (`/progress`).
- All vectorization parameters are passed per request for easy tuning.

---

## 🤝 Contributing
PRs welcome! Ideas:
- Multi‑color tracing (per‑cluster fill), palette quantization
- Batch processing / drag‑drop multiple files
- CLI mode (headless, no UI)
- Dockerfile

---

## 🚀 Deploy

### Hugging Face Spaces (Docker)

1. Neues Space anlegen: Typ „Docker“ wählen
2. Diese Dateien hochladen: `app.py`, `vectorizer.py`, `requirements.txt`, `Dockerfile`, `templates/`, `static/`, `render.yaml` (optional)
3. Build startet automatisch. Die App läuft auf Port `7860`.

> Hinweis: Der `Dockerfile` installiert `potrace` und `librsvg2-bin` für hochwertige Exports (PNG/PDF). Export-Port ist via Umgebungsvariable `PORT` konfiguriert.

### Render/Andere Hoster

Setze eine Health‑Route auf `/healthz` und stelle sicher, dass `gunicorn` mit `app:app` gestartet wird.

---

## 📄 License
MIT © 2025 Beit Khalaf

