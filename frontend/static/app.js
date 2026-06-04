/* ═══════════════════════════════════════════════════════
   WaterWise ML v2 – Global App JS
   Theme · Sidebar · Clock · Toast · SSE
   ═══════════════════════════════════════════════════════ */

// ── Theme ─────────────────────────────────────────────────────
(function () {
  const saved = localStorage.getItem("ww_theme") || "dark";
  document.documentElement.setAttribute("data-theme", saved);
  updateThemeUI(saved);
})();

function toggleTheme() {
  const cur  = document.documentElement.getAttribute("data-theme");
  const next = cur === "dark" ? "light" : "dark";
  document.documentElement.setAttribute("data-theme", next);
  localStorage.setItem("ww_theme", next);
  updateThemeUI(next);
}

function updateThemeUI(theme) {
  const icon  = document.getElementById("theme-icon");
  const label = document.getElementById("theme-label");
  if (!icon) return;
  if (theme === "dark") {
    icon.className  = "bi bi-sun";
    label.textContent = "Light Mode";
  } else {
    icon.className  = "bi bi-moon-stars";
    label.textContent = "Dark Mode";
  }
}

// ── Live Clock ────────────────────────────────────────────────
function _tick() {
  const el = document.getElementById("clock");
  if (el) el.textContent = new Date().toLocaleTimeString();
}
setInterval(_tick, 1000);
_tick();

// ── Sidebar ───────────────────────────────────────────────────
function toggleSidebar() {
  const sb   = document.getElementById("sidebar");
  const main = document.getElementById("main-wrap");
  if (window.innerWidth <= 768) {
    sb.classList.toggle("open");
  } else {
    sb.classList.toggle("collapsed");
    if (sb.classList.contains("collapsed")) {
      main.style.marginLeft = "64px";
      sb.style.width = "64px";
    } else {
      main.style.marginLeft = "";
      sb.style.width = "";
    }
  }
}

// ── Toast Notifications ───────────────────────────────────────
const _ICONS = {
  success: "check-circle-fill",
  danger:  "x-octagon-fill",
  warning: "exclamation-triangle-fill",
  info:    "info-circle-fill",
};
const _COLORS = {
  success: "var(--teal)",
  danger:  "var(--red)",
  warning: "var(--orange)",
  info:    "var(--blue)",
};

function showToast(message, type = "info", duration = 4500) {
  const container = document.getElementById("toasts");
  if (!container) return;
  const id   = "toast_" + Date.now();
  const icon = _ICONS[type]  || _ICONS.info;
  const col  = _COLORS[type] || _COLORS.info;

  const el   = document.createElement("div");
  el.id        = id;
  el.className = "toast-item";
  el.innerHTML = `
    <i class="bi bi-${icon}" style="color:${col};font-size:1.1rem;flex-shrink:0"></i>
    <span style="flex:1">${message}</span>
    <button class="toast-dismiss" onclick="document.getElementById('${id}').remove()">
      <i class="bi bi-x"></i>
    </button>`;
  container.appendChild(el);
  setTimeout(() => el?.remove(), duration);
}

// ── SSE – Server-Sent Events ──────────────────────────────────
// Subscribe once; push critical-alert toasts automatically
(function initSSE() {
  if (!window.EventSource) return;
  try {
    const es = new EventSource("/api/sse/live");

    es.addEventListener("alerts", (e) => {
      try {
        const alerts = JSON.parse(e.data);
        alerts.forEach((a) => {
          const key = "sse_seen_" + a.id;
          if (sessionStorage.getItem(key)) return;
          sessionStorage.setItem(key, "1");
          if (a.severity === "Critical") {
            showToast(`🚨 <strong>${a.alert_type}</strong> – ${a.zone_name}`, "danger", 8000);
          }
        });
      } catch (_) {}
    });

    es.addEventListener("error", () => {
      // silently reconnect – browser handles it
    });
  } catch (_) {}
})();

// ── Utility: CSS variable reader ──────────────────────────────
function cssVar(name) {
  return getComputedStyle(document.documentElement).getPropertyValue(name).trim();
}

// ── Chart.js global defaults ──────────────────────────────────
if (window.Chart) {
  Chart.defaults.font.family = "'JetBrains Mono', monospace";
  Chart.defaults.font.size   = 11;
  Chart.defaults.color       = "#6b8fb5";
}