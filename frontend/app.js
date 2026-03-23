const API_BASE = "http://127.0.0.1:5000/api";
const USER_ID = "default";
let currentFile = null;
let lastResult = null;

const DISEASE_CATALOG = [
  { class: "Pepper__bell___Bacterial_spot", crop: "pepper", label: "Bell Pepper Bacterial Spot", healthy: false },
  { class: "Pepper__bell___healthy", crop: "pepper", label: "Bell Pepper Healthy", healthy: true },
  { class: "Potato___Early_blight", crop: "potato", label: "Potato Early Blight", healthy: false },
  { class: "Potato___Late_blight", crop: "potato", label: "Potato Late Blight", healthy: false },
  { class: "Potato___healthy", crop: "potato", label: "Potato Healthy", healthy: true },
  { class: "Tomato_Bacterial_spot", crop: "tomato", label: "Tomato Bacterial Spot", healthy: false },
  { class: "Tomato_Early_blight", crop: "tomato", label: "Tomato Early Blight", healthy: false },
  { class: "Tomato_Late_blight", crop: "tomato", label: "Tomato Late Blight", healthy: false },
  { class: "Tomato_Leaf_Mold", crop: "tomato", label: "Tomato Leaf Mold", healthy: false },
  { class: "Tomato_Septoria_leaf_spot", crop: "tomato", label: "Tomato Septoria Leaf Spot", healthy: false },
  { class: "Tomato_Spider_mites_Two_spotted_spider_mite", crop: "tomato", label: "Tomato Spider Mites", healthy: false },
  { class: "Tomato__Target_Spot", crop: "tomato", label: "Tomato Target Spot", healthy: false },
  { class: "Tomato__Tomato_YellowLeaf__Curl_Virus", crop: "tomato", label: "Tomato Yellow Leaf Curl Virus", healthy: false },
  { class: "Tomato__Tomato_mosaic_virus", crop: "tomato", label: "Tomato Mosaic Virus", healthy: false },
  { class: "Tomato_healthy", crop: "tomato", label: "Tomato Healthy", healthy: true }
];
const CROP_ICONS = { pepper: "🌶️", potato: "🥔", tomato: "🍅" };

// ─── DOM REFS ─────────────────────────────────
const $ = id => document.getElementById(id);
const uploadZone = $("uploadZone"), fileInput = $("fileInput"), browseBtn = $("browseBtn");
const clearBtn = $("clearBtn"), analyzeBtn = $("analyzeBtn"), suitabilityBtn = $("suitabilityBtn");
const imagePreviewPanel = $("imagePreviewPanel"), previewImg = $("previewImg"), previewMeta = $("previewMeta");
const emptyState = $("emptyState"), loadingState = $("loadingState"), resultsContent = $("resultsContent");
const resetBtn = $("resetBtn"), downloadBtn = $("downloadBtn");
const diseaseGrid = $("diseaseGrid"), navbar = $("navbar");
const toast = $("toast"), toastMsg = $("toastMsg");
const alertBtn = $("alertBtn"), alertPanel = $("alertPanel"), alertBadge = $("alertBadge");
const alertList = $("alertList"), closeAlertPanel = $("closeAlertPanel"), markAllReadBtn = $("markAllReadBtn");
const toggleMM = $("toggleMM"), mmBody = $("mmBody");

// ─── NAVBAR SCROLL ─────────────────────────────
window.addEventListener("scroll", () => navbar.classList.toggle("scrolled", window.scrollY > 40));

// ─── MULTI-MODAL TOGGLE ────────────────────────
toggleMM.addEventListener("click", (e) => {
  e.stopPropagation();
  mmBody.classList.toggle("collapsed");
  toggleMM.classList.toggle("rotated");
});
$("mmBody").parentElement.querySelector(".mm-header").addEventListener("click", () => {
  mmBody.classList.toggle("collapsed");
  toggleMM.classList.toggle("rotated");
});

// ─── ALERT PANEL ───────────────────────────────
alertBtn.addEventListener("click", () => {
  alertPanel.style.display = alertPanel.style.display === "none" ? "block" : "none";
  if (alertPanel.style.display === "block") loadAlerts();
});
closeAlertPanel.addEventListener("click", () => alertPanel.style.display = "none");
markAllReadBtn.addEventListener("click", async () => {
  try {
    await fetch(`${API_BASE}/alerts/${USER_ID}/read`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({}) });
    alertBadge.style.display = "none";
    alertList.innerHTML = '<div class="alert-empty">All caught up! ✅</div>';
  } catch (e) { console.error(e); }
});

async function loadAlerts() {
  try {
    const r = await fetch(`${API_BASE}/alerts/${USER_ID}?unread_only=true`);
    const data = await r.json();
    if (data.alerts && data.alerts.length > 0) {
      alertBadge.textContent = data.unread_count;
      alertBadge.style.display = data.unread_count > 0 ? "flex" : "none";
      alertList.innerHTML = data.alerts.map(a => `
        <div class="alert-item ${a.severity}">
          <div class="alert-item-title">${a.title}</div>
          <div class="alert-item-msg">${a.message}</div>
          <div class="alert-item-time">${new Date(a.created_at).toLocaleString()}</div>
        </div>
      `).join("");
    } else {
      alertBadge.style.display = "none";
      alertList.innerHTML = '<div class="alert-empty">No alerts — looking good! 🌿</div>';
    }
  } catch (e) { alertList.innerHTML = '<div class="alert-empty">Could not load alerts</div>'; }
}

// ─── FILE UPLOAD ───────────────────────────────
uploadZone.addEventListener("dragover", e => { e.preventDefault(); uploadZone.classList.add("dragover"); });
uploadZone.addEventListener("dragleave", () => uploadZone.classList.remove("dragover"));
uploadZone.addEventListener("drop", e => { e.preventDefault(); uploadZone.classList.remove("dragover"); if (e.dataTransfer.files[0]) handleFile(e.dataTransfer.files[0]); });
uploadZone.addEventListener("click", () => fileInput.click());
browseBtn.addEventListener("click", e => { e.stopPropagation(); fileInput.click(); });
fileInput.addEventListener("change", () => { if (fileInput.files[0]) handleFile(fileInput.files[0]); });

function handleFile(file) {
  const allowed = ["image/jpeg", "image/png", "image/webp"];
  if (!allowed.includes(file.type)) { showToast("Please upload a JPG, PNG, or WEBP image."); return; }
  if (file.size > 20 * 1024 * 1024) { showToast("File size must be under 20MB."); return; }
  currentFile = file;
  previewImg.src = URL.createObjectURL(file);
  previewMeta.textContent = `${file.name} · ${(file.size / 1024).toFixed(1)} KB`;
  uploadZone.style.display = "none";
  imagePreviewPanel.style.display = "block";
}

clearBtn.addEventListener("click", () => {
  currentFile = null; fileInput.value = ""; previewImg.src = "";
  imagePreviewPanel.style.display = "none"; uploadZone.style.display = "block";
});

// ─── ANALYSIS ──────────────────────────────────
analyzeBtn.addEventListener("click", runAnalysis);

suitabilityBtn.addEventListener("click", async () => {
  const cropType = $("inputCropType").value;
  if (!cropType) return showToast("Please select a Crop Type first.");

  const payload = {
    crop_type: cropType,
    temperature: $("inputTemp").value || 25,
    humidity: $("inputHumidity").value || 60,
    rainfall: $("inputRainfall").value || 0,
    soil_moisture: $("inputSoilMoisture").value || 50,
    soil_ph: $("inputSoilPH").value || 6.5,
    growth_stage: $("inputGrowthStage").value || "vegetative"
  };

  suitabilityBtn.classList.add("loading");
  try {
    const res = await fetch(`${API_BASE}/suitability`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    const data = await res.json();
    suitabilityBtn.classList.remove("loading");
    
    if (data.error) return showToast("Error: " + data.error);

    // Populate modal
    const body = $("suitabilityBody");
    const suitableSymbol = data.is_suitable ? "✅" : "⚠️";
    const suitableColor = data.is_suitable ? "var(--green-400)" : "var(--amber-400)";
    
    body.innerHTML = `
      <div class="suit-card" style="border-left: 4px solid ${suitableColor}">
        <h3 style="color:${suitableColor}">${suitableSymbol} Suitability: ${data.is_suitable ? "Favorable" : "Requires Interventions"}</h3>
        <p>${data.condition_analysis}</p>
      </div>

      ${data.issues.length > 0 ? `
      <div class="suit-card">
        <h3 class="red">🔴 Identified Risk Factors</h3>
        <ul class="suit-list red">
          ${data.issues.map(i => `<li>${i}</li>`).join("")}
        </ul>
      </div>` : ''}

      <div class="suit-card">
        <h3 class="blue">⚡ Actionable Changes to Maximize Yield</h3>
        <ul class="suit-list blue">
          ${data.changes_needed.map(c => `<li>${c}</li>`).join("")}
        </ul>
      </div>

      <div class="suit-card">
        <h3 class="green">📅 Farming & Plucking Schedule</h3>
        <p><strong>Current Phase:</strong> ${data.farming_time}</p>
        <p><strong>Harvest Schedule:</strong> ${data.harvest_time}</p>
      </div>
    `;

    $("suitabilityModal").style.display = "flex";
  } catch (err) {
    suitabilityBtn.classList.remove("loading");
    showToast("Error connecting to Suitability Engine.");
  }
});

$("closeSuitability").addEventListener("click", () => {
  $("suitabilityModal").style.display = "none";
});

async function runAnalysis() {
  if (!currentFile) { showToast("Please select an image first."); return; }
  emptyState.style.display = "none"; resultsContent.style.display = "none"; loadingState.style.display = "flex";

  const steps = ["ls1", "ls2", "ls3", "ls4", "ls5"];
  let stepIdx = 0;
  const stepTimer = setInterval(() => {
    if (stepIdx > 0) { const prev = $(steps[stepIdx - 1]); prev.classList.remove("active"); prev.classList.add("done"); }
    if (stepIdx < steps.length) { $(steps[stepIdx]).classList.add("active"); stepIdx++; }
    else clearInterval(stepTimer);
  }, 600);

  try {
    const formData = new FormData();
    formData.append("file", currentFile);
    formData.append("user_id", USER_ID);

    // Multi-modal data
    const mmFields = { temperature: "inputTemp", humidity: "inputHumidity", rainfall: "inputRainfall",
      soil_moisture: "inputSoilMoisture", soil_ph: "inputSoilPH" };
    for (const [key, id] of Object.entries(mmFields)) {
      const val = $(id).value;
      if (val) formData.append(key, val);
    }
    const cropType = $("inputCropType").value;
    const growthStage = $("inputGrowthStage").value;
    if (cropType) formData.append("crop_type", cropType);
    if (growthStage) formData.append("growth_stage", growthStage);

    const resp = await fetch(`${API_BASE}/predict`, { method: "POST", body: formData });
    clearInterval(stepTimer);
    if (!resp.ok) { const err = await resp.json(); throw new Error(err.error || "Server error"); }
    const data = await resp.json();
    if (!data.success) throw new Error(data.error || "Analysis failed");
    lastResult = data;
    displayResults(data);
    // Refresh dashboard and tracking after new prediction
    loadDashboard(); loadTracking(); loadAlerts();
  } catch (err) {
    clearInterval(stepTimer); loadingState.style.display = "none"; emptyState.style.display = "flex";
    showToast(`Error: ${err.message}`);
  }
}

// ─── DISPLAY RESULTS ───────────────────────────
function displayResults(data) {
  const { prediction, severity, images, recommendation, health_score, risk_level, ai_assistant, future_prediction, environmental_data } = data;
  const isHealthy = prediction.is_healthy;

  // Health Score Ring
  const maxDash = 326.7;
  const scorePercent = health_score / 100;
  setTimeout(() => {
    $("healthRing").style.strokeDashoffset = maxDash - (maxDash * scorePercent);
    $("healthScoreText").textContent = health_score;
  }, 100);

  // Risk badge
  const riskBadge = $("riskBadge");
  riskBadge.textContent = risk_level.toUpperCase() + " RISK";
  riskBadge.className = `risk-badge risk-${risk_level}`;

  // Recovery time
  const recoveryDays = recommendation.recovery_days || 0;
  $("recoveryTime").textContent = recoveryDays > 0 ? `~${recoveryDays} days recovery` : "No treatment needed";

  // Disease Card
  $("diseaseIconWrap").textContent = isHealthy ? "✅" : "🔬";
  $("diseaseBadge").textContent = isHealthy ? "Healthy Plant" : "Disease Detected";
  $("diseaseBadge").className = `disease-badge ${isHealthy ? "healthy" : "diseased"}`;
  $("diseaseName").textContent = prediction.label;
  $("diseaseDesc").textContent = recommendation.description;

  const confFill = $("confidenceFill");
  confFill.style.width = "0%";
  $("confValue").textContent = `${prediction.confidence.toFixed(1)}%`;
  setTimeout(() => { confFill.style.width = `${prediction.confidence}%`; }, 100);

  // Severity
  const sevLevel = $("sevLevel");
  sevLevel.textContent = isHealthy ? "None" : severity.level;
  sevLevel.style.color = isHealthy ? "var(--green-400)" : severity.color;
  $("sevPercent").textContent = isHealthy ? "No infected area detected" : `${severity.percentage.toFixed(1)}% infected area`;

  const sevInfoEl = $("sevInfo");
  const sevInfoMap = { "Mild": { text: "Early stage — act quickly" }, "Moderate": { text: "Significant spread — treat now" }, "Severe": { text: "Critical — immediate action!" } };
  if (isHealthy) { sevInfoEl.textContent = "Plant is in great shape!"; sevInfoEl.style.background = "rgba(34,197,94,0.1)"; sevInfoEl.style.color = "var(--green-400)"; }
  else { const info = sevInfoMap[severity.level] || {}; sevInfoEl.textContent = info.text || severity.level; sevInfoEl.style.background = severity.level === "Severe" ? "rgba(239,68,68,0.12)" : severity.level === "Moderate" ? "rgba(251,191,36,0.12)" : "rgba(34,197,94,0.12)"; sevInfoEl.style.color = severity.color; }

  // Gauge
  const pct = isHealthy ? 0 : Math.min(severity.percentage, 100);
  setTimeout(() => { $("gaugeArc").style.strokeDashoffset = 157 - (157 * pct / 100); $("gaugeText").textContent = `${pct.toFixed(0)}%`; }, 100);

  // Top predictions
  const topPredsEl = $("topPreds");
  topPredsEl.innerHTML = prediction.top5.map(p => `
    <div class="tp-item">
      <span class="tp-name" title="${p.class}">${truncate(p.class, 22)}</span>
      <div class="tp-bar-wrap"><div class="tp-bar-fill" style="width:0%" data-w="${p.confidence}"></div></div>
      <span class="tp-pct">${p.confidence.toFixed(1)}%</span>
    </div>
  `).join("");
  setTimeout(() => { topPredsEl.querySelectorAll(".tp-bar-fill").forEach(el => { el.style.width = `${el.dataset.w}%`; }); }, 150);

  // Images
  $("originalImg").src = `data:image/jpeg;base64,${images.original}`;
  $("gradcamImg").src = `data:image/jpeg;base64,${images.gradcam}`;

  // AI Assistant
  const aiMsgs = $("aiMessages");
  const aiWarns = $("aiWarnings");
  const aiSteps = $("aiNextSteps");
  if (ai_assistant) {
    aiMsgs.innerHTML = (ai_assistant.messages || []).map(m => `<div class="ai-msg">${m}</div>`).join("");
    aiWarns.innerHTML = (ai_assistant.warnings || []).map(w => `<div class="ai-warn">⚠️ ${w}</div>`).join("");
    aiSteps.innerHTML = (ai_assistant.next_steps || []).map(s => `<div class="ai-step">→ ${s}</div>`).join("");
  }

  // Future Prediction
  const aiFuture = $("aiFuture");
  if (future_prediction) {
    aiFuture.style.display = "block";
    const trendColors = { rapidly_increasing: "#ef4444", increasing: "#f59e0b", stable: "#60a5fa", decreasing: "#22c55e", rapidly_decreasing: "#22c55e" };
    const trendLabels = { rapidly_increasing: "⚠️ Rapidly Increasing", increasing: "↗ Increasing", stable: "→ Stable", decreasing: "↘ Decreasing", rapidly_decreasing: "✅ Rapidly Decreasing" };
    $("futureContent").innerHTML = `
      <p><strong>Predicted severity in ${future_prediction.days_ahead} days:</strong> <span style="color:${trendColors[future_prediction.trend] || '#fff'}; font-weight:700">${future_prediction.predicted_severity}%</span></p>
      <p><strong>Trend:</strong> ${trendLabels[future_prediction.trend] || future_prediction.trend}</p>
      <p style="font-size:0.78rem; opacity:0.7">Prediction confidence: ${future_prediction.confidence || 'N/A'}%</p>
    `;
  } else { aiFuture.style.display = "none"; }

  // Environmental Data Display
  const envCard = $("envCard");
  if (environmental_data && Object.keys(environmental_data).length > 0) {
    envCard.style.display = "block";
    const envIcons = { temperature: "🌡️", humidity: "💧", rainfall: "🌧️", soil_moisture: "🌱", soil_ph: "⚗️" };
    const envLabels = { temperature: "Temperature", humidity: "Humidity", rainfall: "Rainfall", soil_moisture: "Soil Moisture", soil_ph: "Soil pH" };
    const envUnits = { temperature: "°C", humidity: "%", rainfall: "mm", soil_moisture: "%", soil_ph: "" };
    $("envGrid").innerHTML = Object.entries(environmental_data).map(([key, val]) => `
      <div class="env-item">
        <div class="env-item-icon">${envIcons[key] || "📊"}</div>
        <div class="env-item-value">${val}${envUnits[key] || ""}</div>
        <div class="env-item-label">${envLabels[key] || key}</div>
      </div>
    `).join("");
  } else { envCard.style.display = "none"; }

  // Recommendations
  const urgencyBadge = $("urgencyBadge");
  urgencyBadge.textContent = recommendation.urgency.toUpperCase();
  urgencyBadge.className = `urgency-badge urgency-${recommendation.urgency}`;
  renderList("immediateList", recommendation.immediate_actions);
  renderList("treatmentList", recommendation.treatments);
  renderList("preventionList", recommendation.prevention);
  $("fertText").textContent = recommendation.fertilizer;

  loadingState.style.display = "none"; resultsContent.style.display = "block";
  setTimeout(() => { $("resultsPanel").scrollIntoView({ behavior: "smooth", block: "start" }); }, 200);
}

function renderList(id, items) { $(id).innerHTML = items.map(item => `<li>${item}</li>`).join(""); }
function truncate(str, n) { return str.length > n ? str.slice(0, n) + "…" : str; }

// ─── RESET ─────────────────────────────────────
resetBtn.addEventListener("click", () => {
  currentFile = null; lastResult = null; fileInput.value = ""; previewImg.src = "";
  imagePreviewPanel.style.display = "none"; uploadZone.style.display = "block";
  resultsContent.style.display = "none"; emptyState.style.display = "flex";
  ["ls1","ls2","ls3","ls4","ls5"].forEach(id => { $(id).classList.remove("active", "done"); });
  $("analyzer").scrollIntoView({ behavior: "smooth" });
});

// ─── DOWNLOAD REPORT ───────────────────────────
downloadBtn.addEventListener("click", () => {
  if (!lastResult) return;
  const d = lastResult, rec = d.recommendation, ai = d.ai_assistant;
  const clean = s => typeof s === "string" ? s.replace(/\u2014/g, "&mdash;").replace(/\u2013/g, "&ndash;") : s;
  const label = clean(d.prediction.label);
  const statusText = d.prediction.is_healthy ? "Healthy Plant" : "Disease Detected";
  const html = `<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8"/><title>CropSense AI Report - ${label}</title>
<style>body{font-family:'Inter',system-ui,sans-serif;background:#f8fafc;color:#1e293b;line-height:1.6;margin:0;padding:40px 20px}.rc{max-width:850px;margin:0 auto;background:#fff;border-radius:16px;box-shadow:0 10px 25px rgba(0,0,0,.05);overflow:hidden}.hd{background:linear-gradient(135deg,#16a34a,#15803d);color:#fff;padding:40px;text-align:center}.hd h1{margin:0;font-size:2em}.hd p{margin:10px 0 0;opacity:.9}.ct{padding:40px}.gs{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:16px;margin-bottom:30px}.sc{background:#f1f5f9;border:1px solid #e2e8f0;padding:20px;border-radius:12px;text-align:center}.sc .l{display:block;color:#64748b;font-size:.8em;font-weight:600;text-transform:uppercase;margin-bottom:6px}.sc .v{font-size:1.2em;font-weight:700}.s2{margin-top:30px}.s2 h2{font-size:1.3em;border-bottom:2px solid #dcfce7;padding-bottom:8px;margin-bottom:16px}.db{background:#f1f5f9;border-left:4px solid #16a34a;padding:14px 18px;border-radius:0 8px 8px 0;margin-bottom:16px}.al{list-style:none;padding:0}.al li{padding-left:24px;margin-bottom:10px;position:relative}.al li::before{content:"→";position:absolute;left:0;color:#16a34a;font-weight:bold}.ai-s{background:#f0fdf4;border:1px solid #bbf7d0;border-radius:8px;padding:14px;margin-bottom:10px;font-size:.9em}.ai-w{background:#fef3c7;border:1px solid #fde68a;border-radius:8px;padding:14px;margin-bottom:10px;font-size:.9em;color:#92400e}.ft{text-align:center;margin-top:40px;padding-top:20px;border-top:1px solid #e2e8f0;color:#64748b;font-size:.8em}</style></head>
<body><div class="rc"><div class="hd"><h1>🌿 CropSense AI Report</h1><p>Generated: ${new Date().toLocaleString()}</p></div>
<div class="ct"><div class="gs"><div class="sc"><span class="l">Disease</span><span class="v">${label}</span></div>
<div class="sc"><span class="l">Status</span><span class="v">${statusText}</span></div>
<div class="sc"><span class="l">Confidence</span><span class="v">${d.prediction.confidence.toFixed(1)}%</span></div>
<div class="sc"><span class="l">Severity</span><span class="v">${d.prediction.is_healthy ? "None" : d.severity.level} (${d.severity.percentage.toFixed(1)}%)</span></div>
<div class="sc"><span class="l">Health Score</span><span class="v">${d.health_score}/100</span></div>
<div class="sc"><span class="l">Risk Level</span><span class="v">${d.risk_level.toUpperCase()}</span></div></div>
<div class="db">${clean(rec.description)}</div>
${ai ? `<div class="s2"><h2>🤖 AI Decision Support</h2>${(ai.messages||[]).map(m=>`<div class="ai-s">${clean(m)}</div>`).join("")}${(ai.warnings||[]).map(w=>`<div class="ai-w">⚠️ ${clean(w)}</div>`).join("")}${(ai.next_steps||[]).map(s=>`<div class="ai-s">→ ${clean(s)}</div>`).join("")}</div>` : ""}
<div class="s2"><h2>⚡ Immediate Actions</h2><ul class="al">${rec.immediate_actions.map(a=>`<li>${clean(a)}</li>`).join("")}</ul></div>
<div class="s2"><h2>💊 Treatments</h2><ul class="al">${rec.treatments.map(t=>`<li>${clean(t)}</li>`).join("")}</ul></div>
<div class="s2"><h2>🛡️ Prevention</h2><ul class="al">${rec.prevention.map(p=>`<li>${clean(p)}</li>`).join("")}</ul></div>
<div class="s2"><h2>🌱 Fertilizer</h2><p style="margin-left:10px">${clean(rec.fertilizer)}</p></div>
<div class="ft"><strong>CropSense AI v2.0</strong> — Multi-Task MobileNetV2 — Smart Crop Disease Monitoring & Decision Support</div></div></div></body></html>`;
  const blob = new Blob([html], { type: "text/html;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a"); 
  a.style.display = "none";
  a.href = url; 
  a.download = `cropsense-report-${Date.now()}.html`; 
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  setTimeout(() => URL.revokeObjectURL(url), 100);
});

let dashboardProgressionData = [];
let trackingProgressionData = [];

// ─── DASHBOARD ─────────────────────────────────
async function loadDashboard() {
  try {
    const r = await fetch(`${API_BASE}/dashboard/${USER_ID}`);
    const data = await r.json();

    $("dashTotalAnalyses").textContent = data.stats.total_analyses;
    $("dashDiseasesFound").textContent = data.stats.diseases_found;
    $("dashHealthyCount").textContent = data.stats.healthy_count;
    $("dashAvgHealth").textContent = data.stats.avg_health_score;

    // Recent predictions
    const rpList = $("recentPredictionsList");
    if (data.recent_predictions.length > 0) {
      rpList.innerHTML = data.recent_predictions.map(p => {
        const dotColor = p.is_healthy ? "var(--green-400)" : p.risk_level === "critical" ? "var(--red-400)" : p.risk_level === "high" ? "var(--amber-400)" : "var(--blue-400)";
        const scoreColor = p.health_score >= 70 ? "var(--green-400)" : p.health_score >= 40 ? "var(--amber-400)" : "var(--red-400)";
        return `<div class="rp-item"><div class="rp-dot" style="background:${dotColor}"></div><div class="rp-info"><div class="rp-name">${p.disease_label}</div><div class="rp-meta">${new Date(p.created_at).toLocaleDateString()} · ${p.severity_level || 'N/A'}</div></div><div class="rp-score" style="color:${scoreColor}">${p.health_score}</div></div>`;
      }).join("");
    } else { rpList.innerHTML = '<div class="dash-empty">No analyses yet. Upload a leaf to get started!</div>'; }

    // Disease distribution
    const ddList = $("diseaseDistList");
    if (data.disease_distribution.length > 0) {
      const maxCount = Math.max(...data.disease_distribution.map(d => d.count));
      ddList.innerHTML = data.disease_distribution.map(d => `
        <div class="dd-item"><span class="dd-name">${d.disease}</span><div class="dd-bar-wrap"><div class="dd-bar-fill" style="width:${(d.count/maxCount)*100}%"></div></div><span class="dd-count">${d.count}</span></div>
      `).join("");
    } else { ddList.innerHTML = '<div class="dash-empty">No disease data yet</div>'; }

    // Progression Chart
    dashboardProgressionData = data.progression || [];
    populateFilter($("progressionFilter"), dashboardProgressionData, drawDashboardProgression);
    drawDashboardProgression();
  } catch (e) { console.error("Dashboard load error:", e); }
}

function populateFilter(selectEl, dataPoints, reDrawFn) {
  if (!dataPoints || dataPoints.length === 0) return;
  const diseaseSet = new Set(dataPoints.map(p => p.disease_label));
  const diseases = Array.from(diseaseSet);
  let html = `<option value="all">All Scans (Mixed)</option>`;
  diseases.forEach(d => {
    html += `<option value="${d}">${d}</option>`;
  });
  selectEl.innerHTML = html;
  
  if (diseases.length > 0) {
    const lastDisease = dataPoints[dataPoints.length - 1].disease_label;
    selectEl.value = lastDisease;
  }
  selectEl.onchange = () => reDrawFn();
}

function drawDashboardProgression() {
  const val = $("progressionFilter").value;
  const filtered = val === "all" ? dashboardProgressionData : dashboardProgressionData.filter(d => d.disease_label === val);
  drawProgressionChart(filtered);
}

function drawProgressionChart(progression) {
  const canvas = $("progressionCanvas");
  const empty = $("chartEmpty");
  const ctx = canvas.getContext("2d");
  if (!progression || progression.length < 2) { 
    empty.classList.remove("hidden"); 
    if(ctx) ctx.clearRect(0, 0, canvas.width, canvas.height);
    return; 
  }
  empty.classList.add("hidden");
  const dpr = window.devicePixelRatio || 1;
  const rect = canvas.parentElement.getBoundingClientRect();
  canvas.width = rect.width * dpr; canvas.height = 220 * dpr;
  canvas.style.width = rect.width + "px"; canvas.style.height = "220px";
  ctx.scale(dpr, dpr);
  const W = rect.width, H = 220, pad = { t: 20, r: 30, b: 45, l: 50 };
  const plotW = W - pad.l - pad.r, plotH = H - pad.t - pad.b;

  ctx.clearRect(0, 0, W, H);

  // Draw severity line
  const sevData = progression.map(p => p.severity_percent || 0);
  const healthData = progression.map(p => p.health_score || 100);
  const n = sevData.length;

  // Grid lines
  ctx.strokeStyle = "rgba(255,255,255,0.06)"; ctx.lineWidth = 1;
  for (let i = 0; i <= 4; i++) {
    const y = pad.t + (plotH / 4) * i;
    ctx.beginPath(); ctx.moveTo(pad.l, y); ctx.lineTo(W - pad.r, y); ctx.stroke();
    ctx.fillStyle = "rgba(255,255,255,0.3)"; ctx.font = "10px Inter"; ctx.textAlign = "right";
    ctx.fillText((100 - i * 25) + "%", pad.l - 6, y + 4);
  }

  // Severity line (red-ish)
  drawLine(ctx, sevData, n, pad, plotW, plotH, "rgba(239,68,68,0.8)", "rgba(239,68,68,0.1)");
  // Health line (green)
  drawLine(ctx, healthData, n, pad, plotW, plotH, "rgba(74,222,128,0.8)", "rgba(74,222,128,0.08)");

  // Legend
  ctx.font = "12px Inter";
  ctx.textBaseline = "middle";
  ctx.textAlign = "left";
  ctx.fillStyle = "rgba(239,68,68,0.8)"; ctx.fillRect(pad.l, H - 20, 12, 4); ctx.fillText("Severity %", pad.l + 18, H - 18);
  ctx.fillStyle = "rgba(74,222,128,0.8)"; ctx.fillRect(pad.l + 100, H - 20, 12, 4); ctx.fillText("Health Score", pad.l + 118, H - 18);
}

function drawLine(ctx, data, n, pad, plotW, plotH, color, fillColor) {
  ctx.beginPath();
  for (let i = 0; i < n; i++) {
    const x = pad.l + (plotW / (n - 1)) * i;
    const y = pad.t + plotH - (data[i] / 100) * plotH;
    if (i === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y);
  }
  ctx.strokeStyle = color; ctx.lineWidth = 2; ctx.stroke();

  // Fill area
  const lastX = pad.l + plotW; const baseY = pad.t + plotH;
  ctx.lineTo(lastX, baseY); ctx.lineTo(pad.l, baseY); ctx.closePath();
  ctx.fillStyle = fillColor; ctx.fill();

  // Dots
  for (let i = 0; i < n; i++) {
    const x = pad.l + (plotW / (n - 1)) * i;
    const y = pad.t + plotH - (data[i] / 100) * plotH;
    ctx.beginPath(); ctx.arc(x, y, 3, 0, Math.PI * 2); ctx.fillStyle = color; ctx.fill();
  }
}

// ─── TRACKING ──────────────────────────────────
async function loadTracking() {
  try {
    const r = await fetch(`${API_BASE}/progression/${USER_ID}`);
    const data = await r.json();

    // Tracking chart
    trackingProgressionData = data.data_points || [];
    populateFilter($("trackingFilter"), trackingProgressionData, drawTrackingProgression);
    drawTrackingProgression();

    // Future Risk
    const frContent = $("futureRiskContent");
    if (data.future_prediction) {
      const fp = data.future_prediction;
      const trendColors = { rapidly_increasing: "#ef4444", increasing: "#f59e0b", stable: "#60a5fa", decreasing: "#22c55e", rapidly_decreasing: "#22c55e" };
      const trendBg = { rapidly_increasing: "rgba(239,68,68,0.1)", increasing: "rgba(251,191,36,0.1)", stable: "rgba(96,165,250,0.1)", decreasing: "rgba(34,197,94,0.1)", rapidly_decreasing: "rgba(34,197,94,0.1)" };
      frContent.innerHTML = `
        <div class="fr-prediction">
          <div class="fr-value" style="color:${trendColors[fp.trend]||'#fff'}">${fp.predicted_severity}%</div>
          <div class="fr-label">Predicted severity in ${fp.days_ahead} days</div>
          <div class="fr-trend" style="background:${trendBg[fp.trend]||'transparent'};color:${trendColors[fp.trend]||'#fff'}">${fp.trend.replace(/_/g, " ").toUpperCase()}</div>
        </div>
        <div style="font-size:0.82rem;color:var(--text-3)">Prediction confidence: ${fp.confidence || "N/A"}%</div>
      `;
    }

    // Timeline
    const tlContent = $("timelineContent");
    if (data.data_points && data.data_points.length > 0) {
      tlContent.innerHTML = data.data_points.slice(-10).reverse().map(p => {
        const dotColor = (p.severity_percent || 0) > 50 ? "var(--red-400)" : (p.severity_percent || 0) > 20 ? "var(--amber-400)" : "var(--green-400)";
        return `<div class="tl-item"><div class="tl-dot-line"><div class="tl-dot" style="background:${dotColor}"></div><div class="tl-line"></div></div><div class="tl-info"><div class="tl-disease">${p.disease_label}</div><div class="tl-meta">Severity: ${(p.severity_percent||0).toFixed(1)}% · Health: ${p.health_score} · ${new Date(p.timestamp).toLocaleDateString()}</div></div></div>`;
      }).join("");
    }
  } catch (e) { console.error("Tracking load error:", e); }
}

function drawTrackingProgression() {
  const val = $("trackingFilter").value;
  const filtered = val === "all" ? trackingProgressionData : trackingProgressionData.filter(d => d.disease_label === val);
  
  const canvas = $("trackingCanvas");
  const empty = $("trackingChartEmpty");
  const ctx = canvas.getContext("2d");
  
  if (filtered && filtered.length >= 2) {
    empty.classList.add("hidden");
    drawTrackingChart(canvas, filtered);
  } else { 
    empty.classList.remove("hidden"); 
    ctx.clearRect(0, 0, canvas.width, canvas.height);
  }
}

function drawTrackingChart(canvas, dataPoints) {
  const ctx = canvas.getContext("2d");
  const dpr = window.devicePixelRatio || 1;
  const rect = canvas.parentElement.getBoundingClientRect();
  canvas.width = rect.width * dpr; canvas.height = 220 * dpr;
  canvas.style.width = rect.width + "px"; canvas.style.height = "220px";
  ctx.scale(dpr, dpr);
  const W = rect.width, H = 220, pad = { t: 20, r: 30, b: 45, l: 50 };
  const plotW = W - pad.l - pad.r, plotH = H - pad.t - pad.b;
  ctx.clearRect(0, 0, W, H);

  const sevData = dataPoints.map(p => p.severity_percent || 0);
  const n = sevData.length;

  // Grid
  ctx.strokeStyle = "rgba(255,255,255,0.06)"; ctx.lineWidth = 1;
  for (let i = 0; i <= 4; i++) {
    const y = pad.t + (plotH / 4) * i;
    ctx.beginPath(); ctx.moveTo(pad.l, y); ctx.lineTo(W - pad.r, y); ctx.stroke();
    ctx.fillStyle = "rgba(255,255,255,0.3)"; ctx.font = "10px Inter"; ctx.textAlign = "right";
    ctx.fillText((100 - i * 25) + "%", pad.l - 6, y + 4);
  }

  drawLine(ctx, sevData, n, pad, plotW, plotH, "rgba(239,68,68,0.9)", "rgba(239,68,68,0.1)");

  ctx.font = "12px Inter"; 
  ctx.textBaseline = "middle";
  ctx.textAlign = "left";
  ctx.fillStyle = "rgba(239,68,68,0.8)";
  ctx.fillRect(pad.l, H - 20, 12, 4); ctx.fillText("Severity Progress %", pad.l + 18, H - 18);
}

// ─── DISEASE GRID ──────────────────────────────
function renderDiseaseGrid(filter = "all") {
  const items = filter === "all" ? DISEASE_CATALOG : DISEASE_CATALOG.filter(d => d.crop === filter);
  diseaseGrid.innerHTML = items.map((d, i) => `
    <div class="disease-item glass-card" style="animation-delay:${i * 0.04}s">
      <div class="di-crop">${CROP_ICONS[d.crop]} ${d.crop}</div>
      <div class="di-name">${d.label}</div>
      <span class="di-status ${d.healthy ? "healthy" : "disease"}">${d.healthy ? "✓ Healthy" : "⚠ Disease"}</span>
    </div>
  `).join("");
}
document.querySelectorAll(".tab-btn").forEach(btn => {
  btn.addEventListener("click", () => {
    document.querySelectorAll(".tab-btn").forEach(b => b.classList.remove("active"));
    btn.classList.add("active"); renderDiseaseGrid(btn.dataset.crop);
  });
});

// ─── API STATUS ────────────────────────────────
async function checkApiStatus() {
  const navStatus = $("navStatus");
  try {
    const r = await fetch(`${API_BASE}/health`, { signal: AbortSignal.timeout(5000) });
    if (!r.ok) throw new Error();
    const data = await r.json();
    navStatus.innerHTML = `<div class="status-dot"></div><span>v${data.version} · ${data.classes} classes</span>`;
    navStatus.style.color = "var(--green-400)";
  } catch {
    navStatus.innerHTML = `<div class="status-dot" style="background:var(--red-400);animation:none"></div><span style="color:var(--red-400)">Offline</span>`;
  }
}

// ─── TOAST ─────────────────────────────────────
let toastTimer = null;
function showToast(msg) { toastMsg.textContent = msg; toast.style.display = "flex"; clearTimeout(toastTimer); toastTimer = setTimeout(() => { toast.style.display = "none"; }, 4000); }

// ─── SMOOTH SCROLL ─────────────────────────────
document.querySelectorAll("a[href^='#']").forEach(a => {
  a.addEventListener("click", e => {
    const target = document.querySelector(a.getAttribute("href"));
    if (target) { e.preventDefault(); target.scrollIntoView({ behavior: "smooth" }); }
  });
});

// ─── INIT ──────────────────────────────────────
renderDiseaseGrid();
checkApiStatus();
setInterval(checkApiStatus, 30000);
loadDashboard();
loadTracking();
loadAlerts();
