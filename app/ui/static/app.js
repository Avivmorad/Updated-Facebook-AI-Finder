const state = {
  debugCursor: 0,
  debugRawLines: [],
  debugEvents: [],
  browserSteps: [],
  selectedResultId: null,
  selectedBrowserStepIndex: -1,
  detailById: new Map(),
  includeInfo: false,
  includeTechnical: false,
  report: null,
  runtime: buildEmptyRuntime(),
  postDecisions: new Map(),
  trackingEnabled: false,
  debugLogEnabled: false,
  browserVisibleEnabled: false,
  trackingCollapsed: false,
};

let statusBusy = false;
let reportBusy = false;
let historyBusy = false;
let debugBusy = false;
let browserStepsBusy = false;

function buildEmptyRuntime() {
  return {
    currentStage: "-",
    currentAction: "-",
    scannedPosts: 0,
    acceptedPosts: 0,
    rejectedPosts: 0,
    resolvedPosts: 0,
    currentPostIndex: 0,
    maxPosts: 0,
  };
}

function el(id) {
  return document.getElementById(id);
}

async function fetchJson(url, options = {}) {
  const response = await fetch(url, options);
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(data.error || `HTTP ${response.status}`);
  }
  return data;
}

function safeText(value, fallback = "-") {
  const text = String(value ?? "").trim();
  return text || fallback;
}

function safeNumber(value, fallback = 0) {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : fallback;
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function formatDateTime(value) {
  const iso = String(value || "").trim();
  if (!iso) {
    return "-";
  }
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) {
    return iso;
  }
  return date.toLocaleString("he-IL");
}

function toFixedNumber(value, digits = 0) {
  const parsed = Number(value);
  if (!Number.isFinite(parsed)) {
    return digits > 0 ? (0).toFixed(digits) : "0";
  }
  return parsed.toFixed(digits);
}

function setRunMessage(message, isError = false) {
  const node = el("run-message");
  node.textContent = message || "";
  node.classList.toggle("is-error", Boolean(isError));
}

function translateStatus(status) {
  const normalized = String(status || "").trim().toLowerCase();
  if (normalized === "running") {
    return "×¨×¥";
  }
  if (normalized === "completed") {
    return "×”×•×©×œ×";
  }
  if (normalized === "stopping") {
    return "עוצר";
  }
  if (normalized === "stopped") {
    return "נעצר";
  }
  if (normalized === "failed") {
    return "× ×›×©×œ";
  }
  if (normalized === "idle") {
    return "×ž×ž×ª×™×Ÿ";
  }
  return safeText(status);
}

function translateStage(stage) {
  const map = {
    run: "×”×ª×—×œ×”",
    startup: "×‘×“×™×§×•×ª ×¤×ª×™×—×”",
    pipeline: "Pipeline",
    input: "×§×œ×˜",
    search: "×¡×¨×™×§×ª ×¤×™×“",
    filters: "×¤×™×œ×˜×¨×™×",
    process_posts: "×¢×™×‘×•×“ ×¤×•×¡×˜×™×",
    post_open: "×¤×ª×™×—×ª ×¤×•×¡×˜",
    post_processing: "×—×™×œ×•×¥ × ×ª×•× ×™×",
    ai: "×‘×“×™×§×ª AI",
    ranking: "×“×™×¨×•×’",
    presentation: "×”×¦×’×ª ×ª×•×¦××•×ª",
    pipeline_done: "×¡×™×•×",
    result: "×ª×•×¦××”",
    error: "×©×’×™××”",
    general: "×›×œ×œ×™",
  };
  return map[String(stage || "").trim()] || safeText(stage);
}

function hasAnyDiagnosticsEnabled() {
  return state.trackingEnabled || state.debugLogEnabled;
}

function updateTrackingVisibility() {
  const panel = el("tracking-panel");
  const content = el("tracking-content");
  const collapseButton = el("tracking-collapse-button");
  const liveSections = el("tracking-live-sections");
  const logSections = el("tracking-log-sections");
  const shouldShow = hasAnyDiagnosticsEnabled();

  panel.classList.toggle("is-hidden", !shouldShow);
  content.classList.toggle("is-hidden", !shouldShow || state.trackingCollapsed);
  liveSections.classList.toggle("is-hidden", !state.trackingEnabled);
  logSections.classList.toggle("is-hidden", !state.debugLogEnabled);
  collapseButton.setAttribute("aria-expanded", String(shouldShow && !state.trackingCollapsed));
  collapseButton.textContent = state.trackingCollapsed ? "×”×¦×’ ×ž×¢×§×‘" : "×”×¡×ª×¨ ×ž×¢×§×‘";
}

function updateModeControls() {
  const slowMoInput = el("slow-mo-input");
  slowMoInput.disabled = !(state.trackingEnabled || state.browserVisibleEnabled);
  renderModeNote();
}

function updateRunButtons(statusPayload = {}) {
  const status = String(statusPayload.status || "").trim().toLowerCase();
  const canStop = Boolean(statusPayload.can_stop);
  el("run-button").disabled = status === "running" || status === "stopping";
  el("stop-button").disabled = !(canStop || status === "running" || status === "stopping");
}

function renderModeNote() {
  const note = el("run-modes-note");
  const parts = [];
  if (state.trackingEnabled) {
    parts.push("Tracking פעיל");
  }
  if (state.debugLogEnabled) {
    parts.push("לוג Debug פעיל");
  }
  if (state.browserVisibleEnabled) {
    parts.push("הדפדפן ייפתח");
  }
  if (parts.length === 0) {
    note.textContent = "אפשר להפעיל Tracking, לוג Debug, או פתיחת דפדפן לפי הצורך. Slow-mo יופעל רק כשיש במה להאט.";
    return;
  }
  const slowMoState = state.trackingEnabled || state.browserVisibleEnabled ? "Slow-mo זמין." : "Slow-mo כבוי.";
  note.textContent = `${parts.join(" · ")}. ${slowMoState}`;
}

function updateStatusBadge(status) {
  const node = el("status-label");
  const normalized = String(status || "idle").trim().toLowerCase();
  node.textContent = translateStatus(normalized);
  node.dataset.state = normalized;
}

function renderStatus(payload) {
  renderStatusTop(payload);
  renderProgress(payload);
  updateRunButtons(payload);
}

function renderStatusTop(payload) {
  const status = safeText(payload.status, "idle");
  updateStatusBadge(status);
  el("status-query").textContent = safeText(payload.query);
  el("status-run-id").textContent = safeText(payload.run_id);
  el("report-path").textContent = safeText(payload.output_json_path, "data/reports/latest.json");
  el("trace-path").textContent = safeText(payload.trace_file_path, "data/logs/debug_trace.txt");
}

function renderMetricsFromReport(report) {
  const runState = report?.run_state || {};
  const progress = runState.progress || {};
  const runtime = runState.runtime || {};
  const presented = report?.presented_results || {};

  el("metric-total-results").textContent = String(presented.total_results || 0);
  el("metric-processed-posts").textContent = String(progress.processed_posts || 0);
  el("metric-elapsed-seconds").textContent = toFixedNumber(runtime.elapsed_seconds || 0, 2);
  el("metric-stop-reason").textContent = safeText(runState.stop_reason, "-");
}

function renderProgress(statusPayload = {}) {
  const reportProgress = state.report?.run_state?.progress || {};
  const reportStatus = String(state.report?.run_state?.status || "").trim().toLowerCase();
  const status = String(statusPayload.status || "").trim().toLowerCase();
  const shouldUseReport = status !== "running" && ["completed", "failed", "stopped"].includes(reportStatus);

  const total = safeNumber(
    shouldUseReport ? reportProgress.max_posts : 0,
    safeNumber(state.runtime.maxPosts, safeNumber(statusPayload.max_posts, 0)),
  );

  let completed = 0;
  if (shouldUseReport) {
    completed = safeNumber(reportProgress.processed_posts, 0);
  } else {
    completed = Math.max(
      safeNumber(state.runtime.resolvedPosts, 0),
      safeNumber(statusPayload.status === "running" ? state.runtime.currentPostIndex - 1 : 0, 0),
    );
  }

  let percent = 0;
  if (total > 0) {
    percent = Math.max(0, Math.min(100, Math.round((completed / total) * 100)));
  } else if (status === "completed") {
    percent = 100;
  }

  el("progress-fill").style.width = `${percent}%`;
  el("progress-label").textContent = `${percent}%`;
  el("progress-detail").textContent = total > 0 ? `${completed} / ${total}` : "0 / 0";
}

function renderResults(report) {
  const container = el("results-list");
  container.innerHTML = "";
  container.setAttribute("role", "listbox");
  container.setAttribute("aria-label", "רשימת תוצאות");
  state.detailById.clear();

  const presented = report?.presented_results || {};
  const list = Array.isArray(presented.results_list) ? presented.results_list : [];
  const details = Array.isArray(presented.result_details) ? presented.result_details : [];

  for (const item of details) {
    if (item?.result_id) {
      state.detailById.set(String(item.result_id), item);
    }
  }

  if (list.length === 0) {
    container.innerHTML = `<div class="empty-state">××™×Ÿ ×ª×•×¦××•×ª ×œ×”×¦×’×” ×›×¨×’×¢.</div>`;
    state.selectedResultId = null;
    renderResultDetail(null);
    return;
  }

  list.forEach((item, index) => {
    const resultId = String(item.result_id || `result_${index + 1}`);
    const button = document.createElement("button");
    button.type = "button";
    button.className = "result-card";
    button.setAttribute("role", "option");
    button.setAttribute("aria-selected", "false");
    button.setAttribute("aria-controls", "result-detail-card");
    button.dataset.resultId = resultId;
    button.innerHTML = `
      <div class="result-card-top">
        <span class="result-rank">#${index + 1}</span>
        <span class="result-score">${toFixedNumber(item.match_score, 1)}</span>
      </div>
      <p class="result-summary">${escapeHtml(safeText(item.short_summary, "×œ×œ× ×¡×™×›×•×"))}</p>
      <div class="result-meta">
        <span>${escapeHtml(safeText(item.publish_time, "-"))}</span>
        <span>${escapeHtml(safeText(item.extraction_status, "-"))}</span>
      </div>
    `;
    button.addEventListener("click", () => selectResult(resultId));
    container.appendChild(button);
  });

  const preferred = state.selectedResultId && state.detailById.has(state.selectedResultId)
    ? state.selectedResultId
    : String(list[0].result_id || "");
  selectResult(preferred);
}

function selectResult(resultId) {
  state.selectedResultId = resultId;
  for (const node of el("results-list").querySelectorAll(".result-card")) {
    const isSelected = node.dataset.resultId === resultId;
    node.classList.toggle("is-selected", isSelected);
    node.setAttribute("aria-selected", String(isSelected));
  }
  renderResultDetail(state.detailById.get(resultId) || null);
}

function renderResultDetail(detail) {
  const empty = el("result-detail-empty");
  const card = el("result-detail-card");

  if (!detail) {
    empty.classList.remove("is-hidden");
    card.classList.add("is-hidden");
    el("result-detail-json").textContent = "××™×Ÿ ×¤×¨×˜×™× ×œ×”×¦×’×”.";
    return;
  }

  empty.classList.add("is-hidden");
  card.classList.remove("is-hidden");

  const post = detail.post || {};
  const ai = detail.ai_match || {};

  el("detail-score").textContent = toFixedNumber(ai.match_score || detail.match_score || 0, 1);
  el("detail-time").textContent = safeText(post.publish_date || post.publish_date_normalized || post.publish_date_raw);
  el("detail-quality").textContent = safeText(post.extraction_quality);
  el("detail-summary").textContent = safeText(detail.short_summary || ai.detected_item || post.post_text, "×œ×œ× ×¡×™×›×•×");
  el("detail-reason").textContent = safeText(ai.match_reason, "××™×Ÿ × ×™×ž×•×§ ×ž×¤×•×¨×˜.");

  const link = String(post.post_link || "").trim();
  const linkNode = el("detail-link");
  if (link) {
    linkNode.href = link;
    linkNode.textContent = link;
  } else {
    linkNode.href = "#";
    linkNode.textContent = "-";
  }

  el("result-detail-json").textContent = JSON.stringify(detail, null, 2);
}

function renderHistory(runs) {
  const tbody = el("history-body");
  tbody.innerHTML = "";

  if (!Array.isArray(runs) || runs.length === 0) {
    tbody.innerHTML = `<tr><td colspan="5">××™×Ÿ ×”×™×¡×˜×•×¨×™×™×ª ×¨×™×¦×•×ª ×œ×”×¦×’×”.</td></tr>`;
    return;
  }

  for (const run of runs) {
    const row = document.createElement("tr");
    row.innerHTML = [
      `<td>${escapeHtml(formatDateTime(run.saved_at))}</td>`,
      `<td>${escapeHtml(translateStatus(run.status))}</td>`,
      `<td>${escapeHtml(safeText(run.query, ""))}</td>`,
      `<td>${escapeHtml(String(run.total_results || 0))}</td>`,
      `<td>${escapeHtml(`${run.processed_posts || 0}/${run.max_posts || 0}`)}</td>`,
    ].join("");
    tbody.appendChild(row);
  }
}

function clearDebugView() {
  state.debugCursor = 0;
  state.debugRawLines = [];
  state.debugEvents = [];
  state.runtime = buildEmptyRuntime();
  state.postDecisions = new Map();
  el("debug-timeline").innerHTML = "";
  el("debug-text-box").value = "";
  renderRuntimeStatus();
  renderWarnings();
}

function parsePostIndex(message) {
  const text = String(message || "");
  const slashMatch = text.match(/Post\s+(\d+)\/(\d+)/i);
  if (slashMatch) {
    return { index: Number(slashMatch[1]), total: Number(slashMatch[2]) };
  }
  const ofMatch = text.match(/Scanning post\s+(\d+)\s+of\s+(\d+)/i);
  if (ofMatch) {
    return { index: Number(ofMatch[1]), total: Number(ofMatch[2]) };
  }
  return null;
}

function setPostDecision(postIndex, value) {
  if (!Number.isFinite(postIndex) || postIndex <= 0) {
    return;
  }
  state.postDecisions.set(postIndex, value);
  let accepted = 0;
  let rejected = 0;
  for (const decision of state.postDecisions.values()) {
    if (decision === "accepted") {
      accepted += 1;
    } else if (decision === "rejected") {
      rejected += 1;
    }
  }
  state.runtime.acceptedPosts = accepted;
  state.runtime.rejectedPosts = rejected;
  state.runtime.resolvedPosts = accepted + rejected;
}

function incorporateDebugEvent(item) {
  state.runtime.currentStage = translateStage(item.stage);
  state.runtime.currentAction = item.message || "-";

  const progressMatch = parsePostIndex(item.message);
  if (progressMatch) {
    state.runtime.currentPostIndex = Math.max(state.runtime.currentPostIndex, progressMatch.index);
    state.runtime.maxPosts = Math.max(state.runtime.maxPosts, progressMatch.total);
    state.runtime.scannedPosts = Math.max(state.runtime.scannedPosts, progressMatch.index);
  }

  if (item.code === "DBG_SEARCH_RESULTS") {
    const match = String(item.message || "").match(/Found\s+(\d+)\s+candidate/i);
    if (match) {
      state.runtime.maxPosts = Math.max(state.runtime.maxPosts, Number(match[1]));
    }
  }

  if (item.code === "DBG_POST_AI_KEEP") {
    const parsed = parsePostIndex(item.message);
    setPostDecision(parsed?.index, "accepted");
  }

  if (item.code === "ERR_AI_MARKED_NOT_RELEVANT" || item.code === "ERR_AI_MARKED_NOT_RECENT") {
    const parsed = parsePostIndex(item.message);
    setPostDecision(parsed?.index, "rejected");
  }
}

function renderDebugEvents(events) {
  if (!Array.isArray(events) || events.length === 0) {
    return;
  }

  const timeline = el("debug-timeline");
  const textBox = el("debug-text-box");
  const keepScrollBottom = timeline.scrollHeight - timeline.scrollTop - timeline.clientHeight < 80;
  const keepTextScrollBottom = textBox.scrollHeight - textBox.scrollTop - textBox.clientHeight < 80;

  for (const item of events) {
    state.debugEvents.push(item);
    incorporateDebugEvent(item);

    const kind = String(item.kind || "INFO").toLowerCase();
    const event = document.createElement("article");
    event.className = `event event-${kind}`;
    event.innerHTML = `
      <div class="event-head">
        <span class="event-time">${escapeHtml(String(item.clock || ""))}</span>
        <span class="event-stage">${escapeHtml(translateStage(String(item.stage || "")))}</span>
        <span class="badge kind-${kind}">${escapeHtml(String(item.kind || ""))}</span>
      </div>
      <p class="event-title">${escapeHtml(String(item.message || ""))}</p>
      <p class="event-code ltr-value">${escapeHtml(String(item.code || ""))}</p>
    `;
    timeline.appendChild(event);

    const rawLine = `[${String(item.clock || "")}] ${String(item.kind || "")} ${String(item.code || "")} | ${String(item.message || "")}`;
    state.debugRawLines.push(rawLine);
  }

  if (state.debugEvents.length > 800) {
    state.debugEvents = state.debugEvents.slice(-800);
  }
  if (state.debugRawLines.length > 800) {
    state.debugRawLines = state.debugRawLines.slice(-800);
  }
  while (timeline.children.length > 500) {
    timeline.removeChild(timeline.firstChild);
  }

  textBox.value = state.debugRawLines.join("\n");

  if (keepScrollBottom) {
    timeline.scrollTop = timeline.scrollHeight;
  }
  if (keepTextScrollBottom) {
    textBox.scrollTop = textBox.scrollHeight;
  }

  renderRuntimeStatus();
  renderWarnings();
}

function renderRuntimeStatus() {
  el("runtime-stage").textContent = safeText(state.runtime.currentStage, "-");
  el("runtime-action").textContent = safeText(state.runtime.currentAction, "-");
  el("runtime-scanned").textContent = String(state.runtime.scannedPosts || 0);
  el("runtime-accepted").textContent = String(state.runtime.acceptedPosts || 0);
  el("runtime-rejected").textContent = String(state.runtime.rejectedPosts || 0);
  el("metric-processed-posts").textContent = String(
    Math.max(state.runtime.scannedPosts || 0, state.runtime.resolvedPosts || 0),
  );
  el("metric-total-results").textContent = String(state.runtime.acceptedPosts || 0);
}

function renderWarnings() {
  const container = el("warnings-list");
  const warningEvents = state.debugEvents
    .filter((item) => ["warn", "missing", "error"].includes(String(item.kind || "").toLowerCase()))
    .slice(-50);

  if (warningEvents.length === 0) {
    container.innerHTML = `<div class="empty-state compact">××™×Ÿ ×›×¨×’×¢ ××–×”×¨×•×ª ××• ×©×’×™××•×ª.</div>`;
    return;
  }

  container.innerHTML = warningEvents
    .map(
      (item) => `
        <article class="warning-item warning-${String(item.kind || "").toLowerCase()}">
          <div class="warning-head">
            <strong>${escapeHtml(String(item.kind || ""))}</strong>
            <span>${escapeHtml(String(item.clock || ""))}</span>
          </div>
          <p>${escapeHtml(String(item.message || ""))}</p>
          <p class="ltr-value">${escapeHtml(String(item.code || ""))}</p>
        </article>
      `,
    )
    .join("");
}

function renderBrowserSteps(payload) {
  const events = Array.isArray(payload?.events) ? payload.events : [];
  state.browserSteps = events;

  const liveImage = el("browser-live-image");
  const liveEmpty = el("browser-live-empty");
  const liveStep = el("browser-live-step");
  const liveMessage = el("browser-live-message");
  const liveTime = el("browser-live-time");
  const liveUrl = el("browser-live-url");
  const strip = el("browser-steps-strip");

  strip.innerHTML = "";

  if (events.length === 0) {
    state.selectedBrowserStepIndex = -1;
    liveImage.classList.add("is-hidden");
    liveImage.removeAttribute("src");
    liveEmpty.classList.remove("is-hidden");
    liveStep.textContent = "×ž×ž×ª×™×Ÿ";
    liveMessage.textContent = "-";
    liveTime.textContent = "-";
    liveUrl.textContent = "-";
    return;
  }

  if (state.selectedBrowserStepIndex < 0 || state.selectedBrowserStepIndex >= events.length) {
    state.selectedBrowserStepIndex = events.length - 1;
  }

  events.forEach((item, index) => {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "step-thumb";
    button.classList.toggle("is-selected", index === state.selectedBrowserStepIndex);
    button.innerHTML = `
      <img src="${escapeHtml(String(item.image_url || ""))}" alt="${escapeHtml(String(item.step_code || "browser-step"))}" loading="lazy" />
      <span>${escapeHtml(String(item.step_code || ""))}</span>
    `;
    button.addEventListener("click", () => {
      state.selectedBrowserStepIndex = index;
      renderBrowserSteps({ events: state.browserSteps });
    });
    strip.appendChild(button);
  });

  const current = events[state.selectedBrowserStepIndex];
  liveImage.src = String(current.image_url || "");
  liveImage.classList.remove("is-hidden");
  liveEmpty.classList.add("is-hidden");
  liveStep.textContent = safeText(current.step_code, "STEP");
  liveMessage.textContent = safeText(current.message, "-");
  liveTime.textContent = formatDateTime(current.timestamp);
  liveUrl.textContent = safeText(current.url, "-");
}

async function refreshStatus() {
  if (statusBusy) {
    return;
  }
  statusBusy = true;
  try {
    const data = await fetchJson("/api/run/status");
    renderStatus(data);
  } catch (error) {
    setRunMessage(`×©×’×™××ª ×¡×˜×˜×•×¡: ${error.message}`, true);
  } finally {
    statusBusy = false;
  }
}

async function refreshLatestReport() {
  if (reportBusy) {
    return;
  }
  reportBusy = true;
  try {
    const data = await fetchJson("/api/report/latest");
    state.report = data.report || null;
    renderMetricsFromReport(state.report);
    renderResults(state.report);
    renderProgress();
  } catch (_error) {
    state.report = null;
    renderMetricsFromReport(null);
    renderResults(null);
    renderProgress();
  } finally {
    reportBusy = false;
  }
}

async function refreshHistory() {
  if (historyBusy) {
    return;
  }
  historyBusy = true;
  try {
    const data = await fetchJson("/api/runs?limit=15");
    renderHistory(data.runs || []);
  } catch (_error) {
    renderHistory([]);
  } finally {
    historyBusy = false;
  }
}

async function pollDebug() {
  if (!hasAnyDiagnosticsEnabled()) {
    return;
  }
  if (debugBusy) {
    return;
  }
  debugBusy = true;
  try {
    const params = new URLSearchParams({
      cursor: String(state.debugCursor),
      include_info: String(state.includeInfo),
      include_technical: String(state.includeTechnical),
      limit: "300",
    });
    const data = await fetchJson(`/api/debug?${params.toString()}`);
    renderDebugEvents(data.events || []);
    state.debugCursor = Number(data.next_cursor || 0);
    if (data.status) {
      renderStatus(data.status);
    }
  } catch (_error) {
    // Poll silently to keep live UI responsive.
  } finally {
    debugBusy = false;
  }
}

async function refreshBrowserSteps() {
  if (!state.trackingEnabled) {
    renderBrowserSteps({ events: [] });
    return;
  }
  if (browserStepsBusy) {
    return;
  }
  browserStepsBusy = true;
  try {
    const data = await fetchJson("/api/browser-steps?limit=30");
    renderBrowserSteps(data);
  } catch (_error) {
    renderBrowserSteps({ events: [] });
  } finally {
    browserStepsBusy = false;
  }
}

async function startRun(event) {
  event.preventDefault();

  const query = el("query-input").value.trim();
  const maxPosts = safeNumber(el("max-posts-input").value, 0);
  const slowMoMs = safeNumber(el("slow-mo-input").value, 0);
  const trackingMode = Boolean(el("tracking-mode-input").checked);
  const debugLogMode = Boolean(el("debug-log-input").checked);
  const browserVisibleMode = Boolean(el("browser-visible-input").checked);

  if (!query) {
    setRunMessage("×™×© ×œ×”×–×™×Ÿ ×—×™×¤×•×© ×œ×¤× ×™ ×ª×—×™×œ×ª ×¨×™×¦×”.", true);
    return;
  }
  if (!Number.isFinite(maxPosts) || maxPosts <= 0) {
    setRunMessage("×ž×§×¡×™×ž×•× ×¤×•×¡×˜×™× ×—×™×™×‘ ×œ×”×™×•×ª ×ž×¡×¤×¨ ×—×™×•×‘×™.", true);
    return;
  }
  if (!Number.isFinite(slowMoMs) || slowMoMs < 0) {
    setRunMessage("Slow-mo ×—×™×™×‘ ×œ×”×™×•×ª 0 ××• ×™×•×ª×¨.", true);
    return;
  }

  state.trackingEnabled = trackingMode;
  state.debugLogEnabled = debugLogMode;
  state.browserVisibleEnabled = browserVisibleMode;
  state.trackingCollapsed = false;
  updateModeControls();
  updateTrackingVisibility();
  updateRunButtons({ status: "running", can_stop: true });
  setRunMessage("×”×¨×™×¦×” ×ž×ª×—×™×œ×”â€¦");
  clearDebugView();
  state.report = null;
  renderMetricsFromReport(null);
  renderResults(null);
  renderProgress({ status: "running", max_posts: Math.floor(maxPosts) });
  renderBrowserSteps({ events: [] });

  try {
    const payload = {
      query,
      max_posts: Math.floor(maxPosts),
      tracking_enabled: trackingMode,
      debug_log_enabled: debugLogMode,
      browser_watch: browserVisibleMode,
      slow_mo_ms: Math.floor(slowMoMs),
    };
    const data = await fetchJson("/api/run", {
      method: "POST",
      headers: { "Content-Type": "application/json; charset=utf-8" },
      body: JSON.stringify(payload),
    });
    setRunMessage(data.message || "×”×¨×™×¦×” ×”×ª×—×™×œ×”.");
    if (data.status) {
      renderStatus(data.status);
    }
  } catch (error) {
    setRunMessage(`×œ× × ×™×ª×Ÿ ×œ×”×ª×—×™×œ ×¨×™×¦×”: ${error.message}`, true);
    updateRunButtons({ status: "idle", can_stop: false });
  }
}

async function stopRun() {
  try {
    const data = await fetchJson("/api/run/stop", {
      method: "POST",
      headers: { "Content-Type": "application/json; charset=utf-8" },
      body: JSON.stringify({}),
    });
    setRunMessage(data.message || "בקשת עצירה נשלחה.");
    if (data.status) {
      renderStatus(data.status);
    }
  } catch (error) {
    setRunMessage(`לא ניתן לעצור את הריצה: ${error.message}`, true);
  }
}

function wireEvents() {
  el("run-form").addEventListener("submit", startRun);

  el("tracking-mode-input").addEventListener("change", (event) => {
    state.trackingEnabled = Boolean(event.target.checked);
    if (!state.trackingEnabled) {
      state.trackingCollapsed = false;
    }
    updateModeControls();
    updateTrackingVisibility();
  });

  el("debug-log-input").addEventListener("change", (event) => {
    state.debugLogEnabled = Boolean(event.target.checked);
    if (!state.debugLogEnabled) {
      clearDebugView();
    }
    updateTrackingVisibility();
  });

  el("browser-visible-input").addEventListener("change", (event) => {
    state.browserVisibleEnabled = Boolean(event.target.checked);
    updateModeControls();
    updateTrackingVisibility();
  });

  el("tracking-collapse-button").addEventListener("click", () => {
    state.trackingCollapsed = !state.trackingCollapsed;
    updateTrackingVisibility();
  });

  el("debug-include-info").addEventListener("change", (event) => {
    state.includeInfo = Boolean(event.target.checked);
    clearDebugView();
  });

  el("debug-include-technical").addEventListener("change", (event) => {
    state.includeTechnical = Boolean(event.target.checked);
    clearDebugView();
  });

  el("debug-clear").addEventListener("click", () => clearDebugView());
  el("stop-button").addEventListener("click", stopRun);
}

async function bootstrap() {
  state.trackingEnabled = Boolean(el("tracking-mode-input").checked);
  state.debugLogEnabled = Boolean(el("debug-log-input").checked);
  state.browserVisibleEnabled = Boolean(el("browser-visible-input").checked);
  updateModeControls();
  updateTrackingVisibility();
  renderRuntimeStatus();
  renderWarnings();

  wireEvents();
  await Promise.all([refreshStatus(), refreshLatestReport(), refreshHistory(), refreshBrowserSteps()]);
  await pollDebug();

  window.setInterval(refreshStatus, 2000);
  window.setInterval(refreshLatestReport, 5000);
  window.setInterval(refreshHistory, 9000);
  window.setInterval(pollDebug, 1200);
  window.setInterval(refreshBrowserSteps, 3000);
}

bootstrap().catch((error) => {
  setRunMessage(`×©×’×™××ª ××ª×—×•×œ UI: ${error.message}`, true);
});

