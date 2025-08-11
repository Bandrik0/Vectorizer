import os, threading, time, tempfile
from flask import Flask, render_template, request, jsonify, send_from_directory
from flask_cors import CORS
from werkzeug.utils import secure_filename
from vectorizer import vectorize_image, svg_to_png, svg_to_pdf

# ---- Default quality settings (can be overridden per-request from Advanced Settings) ----
QUALITY_PRESET = "print"   # "fast" | "print" | "ultra"
PNG_DPI = 600              # DPI when width is Auto
PNG_WIDTH_PX = 0           # 0 = Auto; >0 forces pixel width for crisper PNG

APP_ROOT = os.path.dirname(os.path.abspath(__file__))
UPLOAD_DIR = os.path.join(APP_ROOT, "uploads")
OUTPUT_DIR = os.path.join(APP_ROOT, "outputs")
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)

app = Flask(__name__, template_folder="templates", static_folder="static")
# Allow frontend (e.g., GitHub Pages) to call this backend
CORS(app, resources={r"/*": {"origins": "*"}})
@app.route("/healthz")
def healthz():
    return jsonify({"status": "ok"}), 200


# Shared progress state
PROG = {"percent": 0, "status": "Ready", "logs": [], "done": False, "files": {}}

def log(msg, pct=None):
    if pct is not None:
        PROG["percent"] = int(max(0, min(100, pct)))
    PROG["status"] = msg
    PROG["logs"].append(msg)
    print(msg, flush=True)

def process_file(src_path, stem, quality=None, png_dpi=None, png_width_px=None, fill_color=None):
    try:
        PROG.update({"done": False, "files": {}})
        # Resolve per-request overrides (fallback to global defaults)
        quality = (quality or QUALITY_PRESET).lower()
        png_dpi = int(png_dpi or PNG_DPI)
        png_width_px = int(png_width_px or PNG_WIDTH_PX)
        fill_color = fill_color or "#C59A52"
        log("📂 File received. Preprocessing…", 5)

        # 1) SVG üret
        svg_path = os.path.join(OUTPUT_DIR, f"{stem}.svg")
        def cb(*args):
            msg = args[0] if len(args) >= 1 else ""
            pct = args[1] if len(args) >= 2 else None
            log(msg, pct)
        # Choose tracing quality profile
        if quality == "fast":
            vec_kwargs = dict(scale_up=6,  alphamax=1.25, opttolerance=0.18, turdsize=2, turnpolicy="minority")
        elif quality == "ultra":
            vec_kwargs = dict(scale_up=12, alphamax=1.38, opttolerance=0.15, turdsize=1, turnpolicy="minority")
        else:  # print (default)
            vec_kwargs = dict(scale_up=8,  alphamax=1.35, opttolerance=0.16, turdsize=1, turnpolicy="minority")
        # Run vectorization (reports up to ~70%)
        vectorize_image(src_path, svg_path, report=cb, fill_color=fill_color, **vec_kwargs)

        # 2) Export PNG / PDF (with smart fallback to available tools)
        log("🖼️ Creating PNG…", 80)
        png_path = os.path.join(OUTPUT_DIR, f"{stem}.png")
        ok_png = svg_to_png(
            svg_path, png_path,
            dpi=png_dpi,
            width_px=(png_width_px or None),
            report=cb
        )

        log("📄 Creating PDF…", 90)
        pdf_path = os.path.join(OUTPUT_DIR, f"{stem}.pdf")
        ok_pdf = svg_to_pdf(svg_path, pdf_path, report=cb)

        files = {"svg": os.path.basename(svg_path)}
        if ok_png: files["png"] = os.path.basename(png_path)
        if ok_pdf: files["pdf"] = os.path.basename(pdf_path)
        PROG["files"] = files

        log("✅ Done.", 100)
        PROG["done"] = True
    except Exception as e:
        log(f"❌ Hata: {e}", 100)
        PROG["done"] = True

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/upload", methods=["POST"])
def upload():
    file = request.files.get("file")
    if not file:
        return jsonify({"error": "Dosya yok"}), 400

    filename = secure_filename(file.filename) or "image.png"
    stem, _ = os.path.splitext(filename)
    path = os.path.join(UPLOAD_DIR, filename)
    file.save(path)

    # Read Advanced Settings from form (fallback to defaults)
    quality = (request.form.get("quality") or QUALITY_PRESET).lower()
    png_width_str = request.form.get("png_width_px") or ""
    png_dpi_str   = request.form.get("png_dpi") or ""
    fill_color    = request.form.get("fill_color") or "#C59A52"
    try:
        png_width_px = int(png_width_str) if png_width_str.strip() != "" else PNG_WIDTH_PX
    except ValueError:
        png_width_px = PNG_WIDTH_PX
    try:
        png_dpi = int(png_dpi_str) if png_dpi_str.strip() != "" else PNG_DPI
    except ValueError:
        png_dpi = PNG_DPI

    # progress reset
    PROG.update({"percent": 0, "status": "Starting…", "logs": [], "done": False, "files": {}})

    # start processing in background
    threading.Thread(
        target=process_file,
        args=(path, stem, quality, png_dpi, png_width_px, fill_color),
        daemon=True
    ).start()
    return jsonify({"ok": True})

@app.route("/progress")
def progress():
    return jsonify(PROG)

@app.route("/download/<name>")
def download(name):
    return send_from_directory(OUTPUT_DIR, name, as_attachment=True)

if __name__ == "__main__":
    PORT = int(os.environ.get("PORT", "5000"))
    app.run(host="0.0.0.0", port=PORT, debug=True)
