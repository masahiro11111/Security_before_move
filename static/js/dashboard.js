/* ─── グローバル状態 ─────────────────────────────────── */
let G = null; // サーバーから取得した全データ
let crimeBarChart = null;

const isDark = matchMedia("(prefers-color-scheme:dark)").matches;
const gc = a => isDark ? `rgba(255,255,255,${a})` : `rgba(0,0,0,${a})`;
const TICK_COLOR = isDark ? "#9c9a92" : "#73726c";
const GRID_COLOR = gc(0.07);

/* ─── 初期化 ─────────────────────────────────────────── */
document.addEventListener("DOMContentLoaded", () => {
  setupTabs();
  loadData();
});

function setupTabs() {
  document.querySelectorAll(".tab").forEach(btn => {
    btn.addEventListener("click", () => {
      const id = btn.dataset.tab;
      document.querySelectorAll(".tab").forEach(t => t.classList.remove("active"));
      document.querySelectorAll(".section").forEach(s => s.classList.remove("active"));
      btn.classList.add("active");
      document.getElementById("tab-" + id).classList.add("active");
    });
  });
}

/* ─── データ取得 ──────────────────────────────────────── */
async function loadData() {
  document.getElementById("loading").style.display = "block";
  document.getElementById("error-msg").style.display = "none";
  try {
    const res = await fetch("/api/data");
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    G = await res.json();
    document.getElementById("loading").style.display = "none";
    document.getElementById("updated-at").textContent =
      new Date(G.updated_at).toLocaleString("ja-JP");
    renderAll();
  } catch (e) {
    document.getElementById("loading").style.display = "none";
    const el = document.getElementById("error-msg");
    el.style.display = "block";
    el.textContent = "データの読み込みに失敗しました: " + e.message;
  }
}

async function refreshData() {
  const btn = document.querySelector(".refresh-btn");
  btn.disabled = true;
  btn.textContent = "更新中…";
  try {
    const res = await fetch("/api/refresh", { method: "POST" });
    const json = await res.json();
    if (json.status === "ok") {
      await loadData();
    } else {
      alert("更新失敗: " + json.message);
    }
  } finally {
    btn.disabled = false;
    btn.textContent = "↺ 更新";
  }
}

/* ─── 全チャート描画 ──────────────────────────────────── */
function renderAll() {
  renderOverview();
  renderCrimeTrend();
  renderCrimeBar();
  renderCrimeType();
  renderForeignTrend();
  renderForeignBar();
  renderForeignPie();
  renderChildTrend();
  renderChildBar();
  renderRanking();
}

/* ─── ユーティリティ ─────────────────────────────────── */
Chart.defaults.font.family = "'Hiragino Kaku Gothic ProN', 'Noto Sans JP', sans-serif";
Chart.defaults.font.size = 12;
Chart.defaults.color = TICK_COLOR;

const baseOpts = {
  responsive: true, maintainAspectRatio: false,
  plugins: { legend: { display: false } },
  scales: {
    x: { grid: { color: GRID_COLOR }, ticks: { color: TICK_COLOR } },
    y: { grid: { color: GRID_COLOR }, ticks: { color: TICK_COLOR } },
  }
};

function mkLine(id, labels, datasets) {
  new Chart(document.getElementById(id), {
    type: "line", data: { labels, datasets },
    options: { ...baseOpts, plugins: { ...baseOpts.plugins } },
  });
}

function mkBar(id, labels, data, color, horiz = false) {
  return new Chart(document.getElementById(id), {
    type: "bar",
    data: { labels, datasets: [{ data, backgroundColor: color, borderRadius: 4, borderSkipped: false }] },
    options: {
      ...baseOpts,
      indexAxis: horiz ? "y" : "x",
      scales: {
        x: { grid: { color: GRID_COLOR }, ticks: { color: TICK_COLOR, autoSkip: false } },
        y: { grid: { color: GRID_COLOR }, ticks: { color: TICK_COLOR, autoSkip: false, font: { size: 11 } } },
      }
    }
  });
}

/* ─── 概要 ────────────────────────────────────────────── */
function renderOverview() {
  const t = G.trend;
  const years = Object.keys(t.crime_total).slice(-5);
  const crime = years.map(y => t.crime_total[y]);
  const foreign = years.map(y => t.foreign_total[y] ?? null);
  const child = years.map(y => t.child_total[y] ?? null);
  const idx = (arr, i) => arr.map(v => v ? Math.round(v / arr[i] * 100) : null);

  // メトリクスカード
  const latest = { crime: crime.at(-1), foreign: foreign.at(-1), child: child.at(-1) };
  document.getElementById("metrics-overview").innerHTML = `
    <div class="metric"><div class="metric-label">刑法犯認知件数（2023年）</div>
      <div class="metric-val">${latest.crime.toLocaleString()}</div>
      <div class="metric-trend up">▲ 前年比 +8.3%</div></div>
    <div class="metric"><div class="metric-label">外国人人口（2023年）</div>
      <div class="metric-val">${latest.foreign.toLocaleString()}</div>
      <div class="metric-trend up">▲ 前年比 +11.8%</div></div>
    <div class="metric"><div class="metric-label">14歳以下人口（2023年）</div>
      <div class="metric-val">${(latest.child / 10000).toFixed(0)}万人</div>
      <div class="metric-trend down">▼ 前年比 −0.8%</div></div>
    <div class="metric"><div class="metric-label">人口10万人あたり犯罪件数</div>
      <div class="metric-val">697</div>
      <div class="metric-trend up">2019年比 −12%</div></div>`;

  mkLine("c-overview", years, [
    { label: "犯罪", data: idx(crime, 0), borderColor: "#E24B4A", backgroundColor: "rgba(226,75,74,.1)", tension: .4, fill: true, pointRadius: 4 },
    { label: "外国人", data: idx(foreign, 0), borderColor: "#378ADD", backgroundColor: "rgba(55,138,221,.1)", tension: .4, fill: true, pointRadius: 4 },
    { label: "子供", data: idx(child, 0), borderColor: "#1D9E75", backgroundColor: "rgba(29,158,117,.1)", tension: .4, fill: true, pointRadius: 4 },
  ]);
}

/* ─── 犯罪 ────────────────────────────────────────────── */
function renderCrimeTrend() {
  const t = G.trend.crime_total;
  const years = Object.keys(t);
  const vals = years.map(y => t[y]);
  mkLine("c-crime-trend", years, [{
    label: "刑法犯認知件数", data: vals,
    borderColor: "#E24B4A", backgroundColor: "rgba(226,75,74,.1)", tension: .3, fill: true, pointRadius: 4
  }]);
}

function renderCrimeBar() {
  if (crimeBarChart) crimeBarChart.destroy();
  const mode = document.getElementById("crime-mode").value;
  const wards = [...G.wards]
    .sort((a, b) => (mode === "rate" ? b.crime_rate - a.crime_rate : b.crime - a.crime))
    .slice(0, 15);
  const data = wards.map(w => mode === "rate" ? w.crime_rate : w.crime);
  crimeBarChart = mkBar("c-crime-bar", wards.map(w => w.name), data, "#E24B4A", true);
}

function renderCrimeType() {
  const labels = Object.keys(G.crime_type);
  const data = Object.values(G.crime_type);
  new Chart(document.getElementById("c-crime-type"), {
    type: "doughnut",
    data: {
      labels,
      datasets: [{
        data, borderWidth: 2,
        borderColor: isDark ? "#242422" : "#fff",
        backgroundColor: ["#E24B4A","#EF9F27","#378ADD","#7F77DD","#D4537E","#888780"],
      }]
    },
    options: {
      responsive: true, maintainAspectRatio: false,
      plugins: { legend: { position: "right", labels: { color: TICK_COLOR, font: { size: 12 }, padding: 12 } } }
    }
  });
}

/* ─── 外国人 ───────────────────────────────────────────── */
function renderForeignTrend() {
  const t = G.trend.foreign_total;
  const years = Object.keys(t);
  mkLine("c-foreign-trend", years, [{
    data: years.map(y => t[y]),
    borderColor: "#378ADD", backgroundColor: "rgba(55,138,221,.1)", tension: .4, fill: true, pointRadius: 4
  }]);
}

function renderForeignBar() {
  const sorted = [...G.wards].sort((a, b) => b.foreign_pct - a.foreign_pct).slice(0, 15);
  mkBar("c-foreign-bar", sorted.map(w => w.name), sorted.map(w => w.foreign_pct), "#378ADD", true);
}

function renderForeignPie() {
  const labels = Object.keys(G.foreign_nationality);
  const data = Object.values(G.foreign_nationality);
  new Chart(document.getElementById("c-foreign-pie"), {
    type: "doughnut",
    data: {
      labels, datasets: [{
        data, borderWidth: 2,
        borderColor: isDark ? "#242422" : "#fff",
        backgroundColor: ["#E24B4A","#EF9F27","#378ADD","#1D9E75","#7F77DD","#D4537E","#888780"],
      }]
    },
    options: {
      responsive: true, maintainAspectRatio: false,
      plugins: { legend: { position: "right", labels: { color: TICK_COLOR, font: { size: 12 }, padding: 10 } } }
    }
  });
}

/* ─── 子供 ─────────────────────────────────────────────── */
function renderChildTrend() {
  const t = G.trend.child_total;
  const years = Object.keys(t);
  mkLine("c-child-trend", years, [{
    data: years.map(y => t[y]),
    borderColor: "#1D9E75", backgroundColor: "rgba(29,158,117,.1)", tension: .4, fill: true, pointRadius: 4
  }]);
}

function renderChildBar() {
  const sorted = [...G.wards].sort((a, b) => b.child - a.child).slice(0, 15);
  mkBar("c-child-bar", sorted.map(w => w.name), sorted.map(w => Math.round(w.child / 1000)), "#1D9E75", true);
}

/* ─── ランキング ─────────────────────────────────────────*/
function renderRanking() {
  const key = document.getElementById("rank-key").value;
  const filter = (document.getElementById("rank-filter").value || "").trim();
  const asc = key.endsWith("_asc");
  const sortKey = asc ? key.replace("_asc", "") : key;

  let wards = [...G.wards];
  if (filter) wards = wards.filter(w => w.name.includes(filter));
  wards.sort((a, b) => asc ? a[sortKey] - b[sortKey] : b[sortKey] - a[sortKey]);

  const maxCrime = Math.max(...G.wards.map(w => w.crime));
  const maxForeign = Math.max(...G.wards.map(w => w.foreign_pct));
  const maxChild = Math.max(...G.wards.map(w => w.child_pct));

  document.getElementById("rank-body").innerHTML = wards.map((w, i) => `
    <tr>
      <td style="color:var(--text-3);font-size:12px">${i + 1}</td>
      <td style="font-weight:600">${w.name}</td>
      <td>${w.population.toLocaleString()}</td>
      <td>${w.crime.toLocaleString()}
        <span class="bar-mini" style="width:${Math.round(w.crime/maxCrime*50)}px;background:#E24B4A88"></span></td>
      <td>${w.crime_rate}</td>
      <td>${w.foreign.toLocaleString()}</td>
      <td>${w.foreign_pct}%
        <span class="bar-mini" style="width:${Math.round(w.foreign_pct/maxForeign*50)}px;background:#378ADD88"></span></td>
      <td>${w.child.toLocaleString()}</td>
      <td>${w.child_pct}%
        <span class="bar-mini" style="width:${Math.round(w.child_pct/maxChild*50)}px;background:#1D9E7588"></span></td>
    </tr>`).join("");
}
