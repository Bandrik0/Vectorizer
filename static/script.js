// Elements
// Backend base URL (for GitHub Pages → Render)
const API_BASE = (document.querySelector('meta[name="api-base"]')?.content || '').replace(/\/+$/, '');
function api(path) {
  path = String(path || '');
  if (!path.startsWith('/')) path = '/' + path;
  return API_BASE ? `${API_BASE}${path}` : path;
}
const fileInput   = document.getElementById("fileInput");
const startBtn    = document.getElementById("startBtn");
const bar         = document.getElementById("bar");
const logEl       = document.getElementById("log");
const downloads   = document.getElementById("downloads");
const dlSvg       = document.getElementById("dl-svg");
const dlPng       = document.getElementById("dl-png");
const dlPdf       = document.getElementById("dl-pdf");
// Advanced settings
const qualitySel  = document.getElementById("qualitySelect");
const pngWidth    = document.getElementById("pngWidth");
const pngWidthVal = document.getElementById("pngWidthVal");
const pngDpi      = document.getElementById("pngDpi");
const pngDpiVal   = document.getElementById("pngDpiVal");
const fillColor   = document.getElementById("fillColor");

// Helpers
function setWidthBadge() {
  if (!pngWidth || !pngWidthVal) return;
  const v = Number(pngWidth.value);
  pngWidthVal.textContent = v > 0 ? `${v}px` : "Auto";
}
function setDpiBadge() {
  if (!pngDpi || !pngDpiVal) return;
  pngDpiVal.textContent = `${Number(pngDpi.value)}`;
}
function appendLog(text) {
  const li = document.createElement("li");
  li.className = "list-group-item";
  li.textContent = text;
  logEl.appendChild(li);
  logEl.scrollTop = logEl.scrollHeight;
}
function resetUI() {
  bar.style.width = "0%";
  bar.textContent = "0%";
  logEl.innerHTML = "";
  downloads.classList.add("d-none");
  dlPng.classList.add("d-none");
  dlPdf.classList.add("d-none");
}
function setBusy(busy) {
  startBtn.disabled = busy;
  startBtn.textContent = busy ? "Processing…" : "Upload & Start";
}

// Init badges (only if elements exist on the page)
if (pngWidth && pngWidthVal) {
  setWidthBadge();
  pngWidth.addEventListener("input", setWidthBadge);
}
if (pngDpi && pngDpiVal) {
  setDpiBadge();
  pngDpi.addEventListener("input", setDpiBadge);
}

// Start
startBtn.addEventListener("click", async () => {
  if (!fileInput.files.length) { alert("Please select a file"); return; }

  resetUI();
  setBusy(true);

  const form = new FormData();
  form.append("file", fileInput.files[0]);
  // Advanced settings → backend
  if (qualitySel)  form.append("quality", qualitySel.value);
  if (pngWidth)    form.append("png_width_px", String(pngWidth.value)); // "0" = Auto
  if (pngDpi)      form.append("png_dpi", String(pngDpi.value));
  if (fillColor)   form.append("fill_color", String(fillColor.value || "#C59A52"));

  try {
    const res = await fetch(api("/upload"), { method: "POST", body: form, mode: "cors" });
    if (!res.ok) throw new Error(`Upload failed: ${res.status}`);
    poll(); // start progress polling
  } catch (e) {
    appendLog(`Error: ${e.message || e}`);
    setBusy(false);
  }
});

async function poll() {
  try {
    const res = await fetch(api("/progress"), { mode: "cors" });
    const data = await res.json();

    bar.style.width = data.percent + "%";
    bar.textContent = data.percent + "%";

    // Refresh logs
    logEl.innerHTML = "";
    (data.logs || []).forEach(appendLog);

    if (data.done) {
      downloads.classList.remove("d-none");
      if (data.files && data.files.svg) { dlSvg.href = api("/download/" + data.files.svg); }
      if (data.files && data.files.png) { dlPng.href = api("/download/" + data.files.png); dlPng.classList.remove("d-none"); }
      if (data.files && data.files.pdf) { dlPdf.href = api("/download/" + data.files.pdf); dlPdf.classList.remove("d-none"); }
      setBusy(false);
      return;
    }
    setTimeout(poll, 500);
  } catch (e) {
    appendLog(`Progress error: ${e.message || e}`);
    setTimeout(poll, 800);
  }
}
