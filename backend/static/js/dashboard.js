/* ═══════════════════════════════════════════════════════
   WaterWise ML v2 – Dashboard Charts & Live Refresh
   ═══════════════════════════════════════════════════════ */

// ── Palette ───────────────────────────────────────────────────
const C = {
  blue:       "#0ea5e9",
  teal:       "#14b8a6",
  red:        "#f43f5e",
  orange:     "#f97316",
  purple:     "#8b5cf6",
  blueFade:   "rgba(14,165,233,0.12)",
  tealFade:   "rgba(20,184,166,0.12)",
  redFade:    "rgba(244,63,94,0.12)",
  orangeFade: "rgba(249,115,22,0.12)",
};

function gridColor() {
  return document.documentElement.getAttribute("data-theme") === "dark"
    ? "rgba(30,60,100,0.45)"
    : "rgba(180,200,220,0.45)";
}

// ── Chart instances ───────────────────────────────────────────
let flowChart, pieChart, barChart, predChart;
let currentFlowZoneId = null;

// ── Init ──────────────────────────────────────────────────────
function initDashboard() {
  const sel = document.getElementById("flow-zone-sel");
  if (sel) currentFlowZoneId = sel.value;

  buildFlowChart();
  buildPieChart();
  buildBarChart();
  buildPredChart();
  refreshDashboard();
}

// ══════════════════════════════════════════════════════════════
// FLOW LINE CHART
// ══════════════════════════════════════════════════════════════
function buildFlowChart() {
  const ctx = document.getElementById("flowChart");
  if (!ctx) return;

  flowChart = new Chart(ctx, {
    type: "line",
    data: {
      labels: [],
      datasets: [
        {
          label: "Flow Rate (L/s)",
          data: [],
          borderColor: C.blue,
          backgroundColor: C.blueFade,
          fill: true,
          tension: 0.4,
          pointRadius: 3,
          pointHoverRadius: 6,
          pointBackgroundColor: C.blue,
          borderWidth: 2,
        },
        {
          label: "Baseline",
          data: [],
          borderColor: C.teal,
          borderDash: [6, 4],
          borderWidth: 1.5,
          pointRadius: 0,
          fill: false,
        },
        {
          label: "Anomaly",
          data: [],
          borderColor: "transparent",
          backgroundColor: C.red,
          pointRadius: 7,
          pointHoverRadius: 10,
          showLine: false,
          pointStyle: "triangle",
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      interaction: { mode: "index", intersect: false },
      plugins: {
        legend: { labels: { boxWidth: 12, padding: 16, usePointStyle: true } },
        tooltip: {
          backgroundColor: "rgba(11,21,36,0.95)",
          borderColor: "rgba(40,80,130,0.5)",
          borderWidth: 1,
          padding: 10,
          callbacks: {
            label: (ctx) =>
              `  ${ctx.dataset.label}: ${ctx.parsed.y != null ? ctx.parsed.y.toFixed(3) + " L/s" : "—"}`,
          },
        },
      },
      scales: {
        x: {
          grid: { color: gridColor() },
          ticks: { maxTicksLimit: 10, maxRotation: 0 },
        },
        y: {
          grid: { color: gridColor() },
          title: { display: true, text: "L/s", color: "#6b8fb5" },
          beginAtZero: true,
        },
      },
      animation: { duration: 350 },
    },
  });
}

async function refreshFlowChart(zoneId) {
  if (!zoneId) return;
  currentFlowZoneId = zoneId;

  let readings;
  try {
    readings = await fetch(`/api/flow/${zoneId}?limit=60`).then((r) => r.json());
  } catch (_) { return; }
  if (!readings.length) return;

  // Get baseline from /api/flow/all
  let baseline = 1;
  try {
    const all = await fetch("/api/flow/all").then((r) => r.json());
    const z   = all.find((x) => String(x.zone_id) === String(zoneId));
    if (z) baseline = z.baseline;
  } catch (_) {}

  const labels   = readings.map((r) => r.timestamp.slice(11, 19));
  const flows    = readings.map((r) => r.flow_rate);
  const baselines= readings.map(() => baseline);
  const anomalies= readings.map((r) => (r.is_anomaly ? r.flow_rate : null));

  flowChart.data.labels             = labels;
  flowChart.data.datasets[0].data   = flows;
  flowChart.data.datasets[1].data   = baselines;
  flowChart.data.datasets[2].data   = anomalies;
  flowChart.options.scales.x.grid.color = gridColor();
  flowChart.options.scales.y.grid.color = gridColor();
  flowChart.update("none");
}

// ══════════════════════════════════════════════════════════════
// PIE / DOUGHNUT CHART
// ══════════════════════════════════════════════════════════════
function buildPieChart() {
  const ctx = document.getElementById("pieChart");
  if (!ctx) return;

  pieChart = new Chart(ctx, {
    type: "doughnut",
    data: {
      labels: ["Normal", "Anomaly", "Leak Risk"],
      datasets: [{
        data: [1, 0, 0],
        backgroundColor: [C.teal, C.orange, C.red],
        borderColor: "transparent",
        hoverOffset: 8,
        borderWidth: 0,
      }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      cutout: "68%",
      plugins: {
        legend: {
          position: "bottom",
          labels: { padding: 16, boxWidth: 12, usePointStyle: true },
        },
        tooltip: {
          backgroundColor: "rgba(11,21,36,0.95)",
          borderColor: "rgba(40,80,130,0.5)",
          borderWidth: 1,
          callbacks: {
            label: (ctx) => `  ${ctx.label}: ${ctx.parsed.toLocaleString()}`,
          },
        },
      },
      animation: { animateRotate: true, duration: 500 },
    },
  });
}

async function refreshPieChart() {
  try {
    const s = await fetch("/api/stats").then((r) => r.json());
    const leak = Math.round(s.anomaly_count * 0.28);
    const anom = s.anomaly_count - leak;

    pieChart.data.datasets[0].data = [s.normal_count, anom, leak];
    pieChart.update("none");

    // KPI cards
    _setText("kpi-zones",       s.total_zones);
    _setText("kpi-alerts",      s.active_alerts);
    _setText("kpi-consumption", s.total_consumption_kl + " kL");
    const total = s.normal_count + s.anomaly_count;
    const pct   = total ? (s.anomaly_count / total * 100).toFixed(1) : 0;
    _setText("kpi-anomaly",   pct + "%");
    _setText("alert-badge",   s.active_alerts);
  } catch (_) {}
}

// ══════════════════════════════════════════════════════════════
// BAR CHART – zone consumption
// ══════════════════════════════════════════════════════════════
function buildBarChart() {
  const ctx = document.getElementById("barChart");
  if (!ctx) return;

  barChart = new Chart(ctx, {
    type: "bar",
    data: {
      labels: [],
      datasets: [
        {
          label: "Normal (L)",
          data: [],
          backgroundColor: C.tealFade,
          borderColor: C.teal,
          borderWidth: 1.5,
          borderRadius: 5,
        },
        {
          label: "Anomalous (L)",
          data: [],
          backgroundColor: C.redFade,
          borderColor: C.red,
          borderWidth: 1.5,
          borderRadius: 5,
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { labels: { boxWidth: 12, usePointStyle: true } },
        tooltip: {
          backgroundColor: "rgba(11,21,36,0.95)",
          borderColor: "rgba(40,80,130,0.5)",
          borderWidth: 1,
        },
      },
      scales: {
        x: { grid: { color: gridColor() } },
        y: {
          grid: { color: gridColor() },
          title: { display: true, text: "Litres", color: "#6b8fb5" },
          beginAtZero: true,
        },
      },
      animation: { duration: 400 },
    },
  });
}

async function refreshBarChart() {
  try {
    const data = await fetch("/api/consumption/zones").then((r) => r.json());
    barChart.data.labels             = data.map((d) => _shortName(d.zone_name));
    barChart.data.datasets[0].data   = data.map((d) => Math.max(0, d.consumption_l - d.anomaly_count * 5));
    barChart.data.datasets[1].data   = data.map((d) => d.anomaly_count * 5);
    barChart.options.scales.x.grid.color = gridColor();
    barChart.options.scales.y.grid.color = gridColor();
    barChart.update("none");
  } catch (_) {}
}

// ══════════════════════════════════════════════════════════════
// PREDICTION CHART
// ══════════════════════════════════════════════════════════════
function buildPredChart() {
  const ctx = document.getElementById("predChart");
  if (!ctx) return;

  predChart = new Chart(ctx, {
    type: "bar",
    data: {
      labels: [],
      datasets: [
        {
          label: "Next Hour (L)",
          data: [],
          backgroundColor: C.orangeFade,
          borderColor: C.orange,
          borderWidth: 1.5,
          borderRadius: 5,
          order: 2,
        },
        {
          label: "Day / 24h avg (L)",
          data: [],
          type: "line",
          borderColor: C.purple,
          backgroundColor: "transparent",
          borderWidth: 2,
          tension: 0.4,
          pointRadius: 4,
          pointBackgroundColor: C.purple,
          order: 1,
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { labels: { boxWidth: 12, usePointStyle: true } },
        tooltip: {
          backgroundColor: "rgba(11,21,36,0.95)",
          borderColor: "rgba(40,80,130,0.5)",
          borderWidth: 1,
        },
      },
      scales: {
        x: { grid: { color: gridColor() } },
        y: {
          grid: { color: gridColor() },
          title: { display: true, text: "Litres", color: "#6b8fb5" },
          beginAtZero: true,
        },
      },
      animation: { duration: 400 },
    },
  });
}

async function refreshPredChart() {
  try {
    const data = await fetch("/api/prediction/all").then((r) => r.json());
    predChart.data.labels           = data.map((d) => _shortName(d.zone_name));
    predChart.data.datasets[0].data = data.map((d) => d.predicted_hour_usage);
    predChart.data.datasets[1].data = data.map((d) =>
      +(d.predicted_day_usage / 24).toFixed(2)
    );
    predChart.options.scales.x.grid.color = gridColor();
    predChart.options.scales.y.grid.color = gridColor();
    predChart.update("none");
  } catch (_) {}
}

// ══════════════════════════════════════════════════════════════
// ZONE TILES
// ══════════════════════════════════════════════════════════════
async function refreshZoneTiles() {
  let zones, health;
  try {
    [zones, health] = await Promise.all([
      fetch("/api/flow/all").then((r) => r.json()),
      fetch("/api/health").then((r) => r.json()),
    ]);
  } catch (_) { return; }

  const healthMap = {};
  health.forEach((h) => (healthMap[h.zone_id] = h));

  zones.forEach((z) => {
    const tile  = document.getElementById(`zt-${z.zone_id}`);
    const flowEl= document.getElementById(`ztf-${z.zone_id}`);
    const gradeEl=document.getElementById(`ztg-${z.zone_id}`);
    if (!tile || !flowEl) return;

    flowEl.textContent = `${z.flow_rate.toFixed(3)} L/s`;

    if (gradeEl && healthMap[z.zone_id]) {
      const h = healthMap[z.zone_id];
      gradeEl.textContent = `Health: ${h.score} · Grade ${h.grade}`;
    }

    const ratio  = z.flow_rate / (z.baseline || 1);
    const badgeEl= tile.querySelector(".zt-status");

    tile.classList.remove("zt-safe", "zt-warning", "zt-danger");
    if (badgeEl) badgeEl.classList.remove("st-safe", "st-warning", "st-danger");

    let st;
    if (z.label === "Leak Risk" || ratio > 1.8) st = "danger";
    else if (z.label === "Anomaly" || ratio > 1.4) st = "warning";
    else st = "safe";

    tile.classList.add(`zt-${st}`);
    if (badgeEl) {
      badgeEl.classList.add(`st-${st}`);
      badgeEl.textContent = st === "danger" ? "DANGER" : st === "warning" ? "WARN" : "OK";
    }
  });
}

// ══════════════════════════════════════════════════════════════
// ALERTS TABLE
// ══════════════════════════════════════════════════════════════
async function refreshAlertsTable() {
  let alerts;
  try {
    alerts = await fetch("/api/alerts?limit=10").then((r) => r.json());
  } catch (_) { return; }

  const tbody = document.getElementById("alerts-tbody");
  if (!tbody) return;

  if (!alerts.length) {
    tbody.innerHTML = `<tr><td colspan="6" class="text-center text-muted py-3">No active alerts 🎉</td></tr>`;
    return;
  }

  tbody.innerHTML = alerts
    .map(
      (a) => `
    <tr>
      <td class="mono">${a.timestamp.slice(11, 19)}</td>
      <td>${_esc(a.zone_name)}</td>
      <td><span class="atype at-${a.alert_type.toLowerCase().replace(/ /g, "-")}">${a.alert_type}</span></td>
      <td><span class="sev sev-${a.severity.toLowerCase()}">${a.severity}</span></td>
      <td class="msg-cell" title="${_esc(a.message)}">${_esc(a.message)}</td>
      <td><button class="resolve-btn" onclick="resolveAlert(${a.id},this)"><i class="bi bi-check2"></i></button></td>
    </tr>`
    )
    .join("");
}

// ══════════════════════════════════════════════════════════════
// BUDGET BARS (dashboard mini-view)
// ══════════════════════════════════════════════════════════════
async function refreshBudgetBars() {
  let data;
  try {
    data = await fetch("/api/budget").then((r) => r.json());
  } catch (_) { return; }

  const el = document.getElementById("budget-bars");
  if (!el) return;

  if (!data.length) {
    el.innerHTML = '<div class="text-muted small p-3">No budgets configured. <a href="/budget" class="text-primary">Set budgets →</a></div>';
    return;
  }

  el.innerHTML = data
    .map((b) => {
      const col =
        b.pct >= 100
          ? "var(--red)"
          : b.pct >= 85
          ? "var(--orange)"
          : "var(--teal)";
      return `
      <div class="bitem">
        <div class="bitem-label">${b.zone_name}</div>
        <div class="bitem-bar"><div class="bitem-fill" style="width:${b.pct}%;background:${col}"></div></div>
        <div class="bitem-pct" style="color:${col}">${b.pct}% used &nbsp;·&nbsp; ${b.used_l.toLocaleString()} / ${b.budget_l.toLocaleString()} L</div>
      </div>`;
    })
    .join("");
}

// ══════════════════════════════════════════════════════════════
// MASTER REFRESH (called every 5 s)
// ══════════════════════════════════════════════════════════════
async function refreshDashboard() {
  await Promise.allSettled([
    refreshFlowChart(currentFlowZoneId),
    refreshPieChart(),
    refreshBarChart(),
    refreshPredChart(),
    refreshZoneTiles(),
    refreshAlertsTable(),
    refreshBudgetBars(),
  ]);
}

// ── Helpers ───────────────────────────────────────────────────
function _setText(id, val) {
  const el = document.getElementById(id);
  if (el) el.textContent = val;
}

function _shortName(name) {
  const parts = name.split(" ");
  return parts.length > 2 ? parts.slice(0, 2).join(" ") : name;
}

function _esc(s) {
  return String(s)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}