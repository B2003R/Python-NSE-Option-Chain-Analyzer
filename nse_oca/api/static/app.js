const configView = document.getElementById("configView");
const resultsView = document.getElementById("resultsView");

const modeSelect = document.getElementById("modeSelect");
const symbolSelect = document.getElementById("symbolSelect");
const expirySelect = document.getElementById("expirySelect");
const strikeInput = document.getElementById("strikeInput");
const intervalSelect = document.getElementById("intervalSelect");
const persistCheck = document.getElementById("persistCheck");

const loadSymbolsBtn = document.getElementById("loadSymbolsBtn");
const loadExpiriesBtn = document.getElementById("loadExpiriesBtn");
const openResultsBtn = document.getElementById("openResultsBtn");

const backBtn = document.getElementById("backBtn");
const refreshBtn = document.getElementById("refreshBtn");
const stopBtn = document.getElementById("stopBtn");

const messageBox = document.getElementById("messageBox");
const configHint = document.getElementById("configHint");
const resultsContext = document.getElementById("resultsContext");

const statusRunning = document.getElementById("statusRunning");
const statusNextRun = document.getElementById("statusNextRun");
const statusLastRun = document.getElementById("statusLastRun");
const statusRuns = document.getElementById("statusRuns");
const statusSync = document.getElementById("statusSync");

const summaryBody = document.getElementById("summaryBody");

const upperStrikeOne = document.getElementById("upperStrikeOne");
const upperOiOne = document.getElementById("upperOiOne");
const upperStrikeTwo = document.getElementById("upperStrikeTwo");
const upperOiTwo = document.getElementById("upperOiTwo");

const lowerStrikeOne = document.getElementById("lowerStrikeOne");
const lowerOiOne = document.getElementById("lowerOiOne");
const lowerStrikeTwo = document.getElementById("lowerStrikeTwo");
const lowerOiTwo = document.getElementById("lowerOiTwo");

const signalOi = document.getElementById("signalOi");
const signalPcr = document.getElementById("signalPcr");
const signalCallExits = document.getElementById("signalCallExits");
const signalPutExits = document.getElementById("signalPutExits");
const signalCallItm = document.getElementById("signalCallItm");
const signalPutItm = document.getElementById("signalPutItm");

const SNAPSHOT_ROW_LIMIT = 200;

const state = {
  symbols: { indices: [], stocks: [] },
  pollId: null,
  pollDelayMs: 9000,
  latestSnapshot: null,
  sessionSnapshots: [],
  activeRunStartedAt: null,
};

function showMessage(text, type = "info") {
  if (configHint) {
    configHint.textContent = text;
    configHint.className = `config-hint ${type}`;
  }
  if (!messageBox) {
    return;
  }
  messageBox.textContent = text;
  messageBox.className = `message ${type}`;
}

function hideMessage() {
  if (configHint) {
    configHint.textContent = "";
    configHint.className = "config-hint";
  }
  if (!messageBox) {
    return;
  }
  messageBox.textContent = "";
  messageBox.className = "message hidden";
}

async function apiRequest(path, options = {}) {
  const response = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });

  const body = await response.json().catch(() => ({}));

  if (!response.ok) {
    const detail = body.detail || `Request failed (${response.status})`;
    throw new Error(detail);
  }

  return body;
}

function populateSelect(selectNode, values, preferred = null) {
  const previous = preferred || selectNode.value;
  selectNode.innerHTML = "";

  if (!values.length) {
    const option = document.createElement("option");
    option.value = "";
    option.textContent = "No data";
    selectNode.appendChild(option);
    return;
  }

  values.forEach((value) => {
    const option = document.createElement("option");
    option.value = value;
    option.textContent = value;
    selectNode.appendChild(option);
  });

  if (values.includes(previous)) {
    selectNode.value = previous;
  } else {
    selectNode.value = values[0];
  }
}

function currentModeSymbols() {
  return modeSelect.value === "Index" ? state.symbols.indices : state.symbols.stocks;
}

function collectRunPayload() {
  return {
    mode: modeSelect.value,
    symbol: symbolSelect.value,
    expiry_date: expirySelect.value,
    strike_price: Number.parseInt(strikeInput.value, 10),
    interval_seconds: Number.parseInt(intervalSelect.value, 10),
    persist: persistCheck.checked,
  };
}

function hasValidContext(payload) {
  return (
    Boolean(payload.symbol) &&
    Boolean(payload.expiry_date) &&
    Number.isInteger(payload.strike_price) &&
    payload.strike_price > 0
  );
}

function snapshotQueryString() {
  const payload = collectRunPayload();
  if (!hasValidContext(payload)) {
    return null;
  }

  const params = new URLSearchParams({
    mode: payload.mode,
    symbol: payload.symbol,
    expiry_date: payload.expiry_date,
    strike_price: String(payload.strike_price),
    limit: String(SNAPSHOT_ROW_LIMIT),
  });

  if (state.activeRunStartedAt) {
    params.set("since_created_at", state.activeRunStartedAt);
  }

  return params.toString();
}

function toNumber(value) {
  const numeric = Number(value);
  return Number.isFinite(numeric) ? numeric : null;
}

function formatValue(value, decimals = 1) {
  const numeric = toNumber(value);
  return numeric === null ? "-" : numeric.toFixed(decimals);
}

function normalizeSnapshot(raw) {
  if (!raw) {
    return null;
  }

  return {
    id: raw.id,
    created_at: raw.created_at || null,
    server_timestamp: raw.server_timestamp || raw.timestamp || null,
    underlying_value: toNumber(raw.underlying_value),
    call_sum: toNumber(raw.call_sum),
    put_sum: toNumber(raw.put_sum),
    difference: toNumber(raw.difference),
    call_boundary: toNumber(raw.call_boundary),
    put_boundary: toNumber(raw.put_boundary),
    call_itm_ratio: toNumber(raw.call_itm_ratio),
    put_itm_ratio: toNumber(raw.put_itm_ratio),
    put_call_ratio: toNumber(raw.put_call_ratio),
    max_call_oi_strike: toNumber(raw.max_call_oi_strike ?? raw.max_call_oi?.strike_price),
    max_call_oi_value: toNumber(raw.max_call_oi_value ?? raw.max_call_oi?.open_interest),
    max_call_oi_secondary_strike: toNumber(
      raw.max_call_oi_secondary_strike ?? raw.max_call_oi_secondary?.strike_price
    ),
    max_call_oi_secondary_value: toNumber(
      raw.max_call_oi_secondary_value ?? raw.max_call_oi_secondary?.open_interest
    ),
    max_put_oi_strike: toNumber(raw.max_put_oi_strike ?? raw.max_put_oi?.strike_price),
    max_put_oi_value: toNumber(raw.max_put_oi_value ?? raw.max_put_oi?.open_interest),
    max_put_oi_secondary_strike: toNumber(
      raw.max_put_oi_secondary_strike ?? raw.max_put_oi_secondary?.strike_price
    ),
    max_put_oi_secondary_value: toNumber(
      raw.max_put_oi_secondary_value ?? raw.max_put_oi_secondary?.open_interest
    ),
    oi_signal: raw.oi_signal || null,
    call_exits_signal: raw.call_exits_signal || null,
    put_exits_signal: raw.put_exits_signal || null,
    call_itm_signal: raw.call_itm_signal || null,
    put_itm_signal: raw.put_itm_signal || null,
  };
}

function showConfigView() {
  configView.classList.remove("hidden");
  resultsView.classList.add("hidden");
}

function showResultsView() {
  configView.classList.add("hidden");
  resultsView.classList.remove("hidden");
  syncResultsContext();
}

function syncResultsContext() {
  const payload = collectRunPayload();
  if (!hasValidContext(payload)) {
    resultsContext.textContent = "-";
    return;
  }

  resultsContext.textContent = `${payload.mode} | ${payload.symbol} | ${payload.expiry_date} | Strike ${payload.strike_price} | ${payload.interval_seconds}s`;
}

function setText(node, value) {
  if (!node) {
    return;
  }
  node.textContent = value;
}

function setSyncState(stateText, retrying = false) {
  if (!statusSync) {
    return;
  }
  statusSync.textContent = stateText;
  statusSync.classList.remove("sync-ok", "sync-retrying");
  if (stateText === "-") {
    return;
  }
  statusSync.classList.add(retrying ? "sync-retrying" : "sync-ok");
}

function syncStartButtonState() {
  if (!openResultsBtn) {
    return;
  }
  const isValid = hasValidContext(collectRunPayload());
  openResultsBtn.disabled = false;
  openResultsBtn.title = isValid ? "" : "Select symbol, expiry, and strike price.";
}

function setSignalClass(node, kind, value) {
  if (!node) {
    return;
  }
  node.classList.remove("signal-positive", "signal-negative", "signal-neutral");

  const normalized = String(value || "").trim().toLowerCase();
  if (!normalized) {
    node.classList.add("signal-neutral");
    return;
  }

  if (kind === "oi") {
    if (normalized === "bullish") {
      node.classList.add("signal-positive");
    } else if (normalized === "bearish") {
      node.classList.add("signal-negative");
    } else {
      node.classList.add("signal-neutral");
    }
    return;
  }

  if (kind === "pcr") {
    const numeric = toNumber(value);
    if (numeric === null) {
      node.classList.add("signal-neutral");
    } else if (numeric >= 1) {
      node.classList.add("signal-positive");
    } else {
      node.classList.add("signal-negative");
    }
    return;
  }

  if (kind === "call-yes") {
    node.classList.add(normalized === "yes" ? "signal-positive" : "signal-neutral");
    return;
  }

  if (kind === "put-yes") {
    node.classList.add(normalized === "yes" ? "signal-negative" : "signal-neutral");
    return;
  }

  node.classList.add("signal-neutral");
}

function clearTimelineTable() {
  summaryBody.innerHTML = '<tr><td colspan="9" class="placeholder">No snapshots in this session yet.</td></tr>';
}

function clearBoundaryPanels() {
  setText(upperStrikeOne, "-");
  setText(upperOiOne, "-");
  setText(upperStrikeTwo, "-");
  setText(upperOiTwo, "-");
  setText(lowerStrikeOne, "-");
  setText(lowerOiOne, "-");
  setText(lowerStrikeTwo, "-");
  setText(lowerOiTwo, "-");

  setText(signalOi, "-");
  setText(signalPcr, "-");
  setText(signalCallExits, "-");
  setText(signalPutExits, "-");
  setText(signalCallItm, "-");
  setText(signalPutItm, "-");

  setSignalClass(signalOi, "oi", null);
  setSignalClass(signalPcr, "pcr", null);
  setSignalClass(signalCallExits, "call-yes", null);
  setSignalClass(signalPutExits, "put-yes", null);
  setSignalClass(signalCallItm, "call-yes", null);
  setSignalClass(signalPutItm, "put-yes", null);
}

function clearSnapshotView() {
  clearTimelineTable();
  clearBoundaryPanels();
}

function getTrendClass(currentValue, previousValue, favorableDirection) {
  const current = toNumber(currentValue);
  const previous = toNumber(previousValue);

  if (current === null || previous === null || current === previous) {
    return "cell-trend-neutral";
  }

  const isIncrease = current > previous;
  const favorable = favorableDirection === "up" ? isIncrease : !isIncrease;
  return favorable ? "cell-trend-positive" : "cell-trend-negative";
}

function renderSnapshotTimeline(snapshots) {
  if (!snapshots.length) {
    clearTimelineTable();
    return;
  }

  const rows = snapshots.map((snapshot, index) => {
    const older = snapshots[index + 1] || null;
    const rowClass = index === 0 ? "timeline-row-latest" : "";

    return `
      <tr class="${rowClass}">
        <td>${snapshot.server_timestamp || "-"}</td>
        <td class="${getTrendClass(snapshot.underlying_value, older?.underlying_value, "up")}">${formatValue(snapshot.underlying_value, 2)}</td>
        <td class="${getTrendClass(snapshot.call_sum, older?.call_sum, "down")}">${formatValue(snapshot.call_sum, 1)}</td>
        <td class="${getTrendClass(snapshot.put_sum, older?.put_sum, "up")}">${formatValue(snapshot.put_sum, 1)}</td>
        <td class="${getTrendClass(snapshot.difference, older?.difference, "down")}">${formatValue(snapshot.difference, 1)}</td>
        <td class="${getTrendClass(snapshot.call_boundary, older?.call_boundary, "down")}">${formatValue(snapshot.call_boundary, 1)}</td>
        <td class="${getTrendClass(snapshot.put_boundary, older?.put_boundary, "up")}">${formatValue(snapshot.put_boundary, 1)}</td>
        <td class="${getTrendClass(snapshot.call_itm_ratio, older?.call_itm_ratio, "up")}">${formatValue(snapshot.call_itm_ratio, 1)}</td>
        <td class="${getTrendClass(snapshot.put_itm_ratio, older?.put_itm_ratio, "down")}">${formatValue(snapshot.put_itm_ratio, 1)}</td>
      </tr>
    `;
  });

  summaryBody.innerHTML = rows.join("");
}

function renderBoundaryPanels(snapshot) {
  if (!snapshot) {
    clearBoundaryPanels();
    return;
  }

  setText(upperStrikeOne, formatValue(snapshot.max_call_oi_strike, 1));
  setText(upperOiOne, formatValue(snapshot.max_call_oi_value, 1));
  setText(upperStrikeTwo, formatValue(snapshot.max_call_oi_secondary_strike, 1));
  setText(upperOiTwo, formatValue(snapshot.max_call_oi_secondary_value, 1));
  setText(lowerStrikeOne, formatValue(snapshot.max_put_oi_strike, 1));
  setText(lowerOiOne, formatValue(snapshot.max_put_oi_value, 1));
  setText(lowerStrikeTwo, formatValue(snapshot.max_put_oi_secondary_strike, 1));
  setText(lowerOiTwo, formatValue(snapshot.max_put_oi_secondary_value, 1));

  const oiSignalValue = snapshot.oi_signal || "-";
  const pcrValue = formatValue(snapshot.put_call_ratio, 2);
  const callExitsValue = snapshot.call_exits_signal || "-";
  const putExitsValue = snapshot.put_exits_signal || "-";
  const callItmValue = snapshot.call_itm_signal || "-";
  const putItmValue = snapshot.put_itm_signal || "-";

  setText(signalOi, oiSignalValue);
  setText(signalPcr, pcrValue);
  setText(signalCallExits, callExitsValue);
  setText(signalPutExits, putExitsValue);
  setText(signalCallItm, callItmValue);
  setText(signalPutItm, putItmValue);

  setSignalClass(signalOi, "oi", oiSignalValue);
  setSignalClass(signalPcr, "pcr", snapshot.put_call_ratio);
  setSignalClass(signalCallExits, "call-yes", callExitsValue);
  setSignalClass(signalPutExits, "put-yes", putExitsValue);
  setSignalClass(signalCallItm, "call-yes", callItmValue);
  setSignalClass(signalPutItm, "put-yes", putItmValue);
}

function renderSnapshotView() {
  renderSnapshotTimeline(state.sessionSnapshots);
  renderBoundaryPanels(state.latestSnapshot);
}

function resetSnapshotState(clearRunContext = true) {
  state.latestSnapshot = null;
  state.sessionSnapshots = [];

  if (clearRunContext) {
    state.activeRunStartedAt = null;
  }

  syncResultsContext();
  if (!resultsView.classList.contains("hidden")) {
    renderSnapshotView();
  }
}

async function loadSymbols() {
  const data = await apiRequest("/symbols");
  state.symbols.indices = data.indices || [];
  state.symbols.stocks = data.stocks || [];
  populateSelect(symbolSelect, currentModeSymbols());
}

async function loadExpiries() {
  if (!symbolSelect.value) {
    populateSelect(expirySelect, []);
    return;
  }

  const data = await apiRequest(`/expiries?symbol=${encodeURIComponent(symbolSelect.value)}`);
  populateSelect(expirySelect, data.expiry_dates || []);
}

function restartPolling() {
  if (state.pollId !== null) {
    window.clearInterval(state.pollId);
    state.pollId = null;
  }
  startPolling();
}

function updatePollingDelay(status) {
  const intervalSeconds = Number.parseInt(status?.config?.interval_seconds, 10);
  const nextDelay = Number.isInteger(intervalSeconds) ? Math.max(intervalSeconds * 1000, 5000) : 9000;

  if (nextDelay !== state.pollDelayMs) {
    state.pollDelayMs = nextDelay;
    if (state.pollId !== null) {
      restartPolling();
    }
  }
}

async function refreshRunStatus() {
  const status = await apiRequest("/runs/status");
  setText(statusRunning, status.running ? "Yes" : "No");
  setText(statusNextRun, status.next_run_at || "-");
  setText(statusLastRun, status.last_run_at || "-");
  setText(statusRuns, String(status.total_runs || 0));
  setSyncState("OK");

  if (status.run_started_at) {
    state.activeRunStartedAt = status.run_started_at;
  }

  updatePollingDelay(status);

  const shouldPoll = status.running && !resultsView.classList.contains("hidden");
  if (shouldPoll) {
    startPolling();
  } else {
    stopPolling();
  }

  return status;
}

async function refreshSessionTimeline() {
  const query = snapshotQueryString();
  if (!query) {
    state.latestSnapshot = null;
    state.sessionSnapshots = [];
    renderSnapshotView();
    return;
  }

  const data = await apiRequest(`/snapshots/history?${query}`);
  const items = Array.isArray(data.items) ? data.items : [];
  const snapshots = items
    .map((item) => normalizeSnapshot(item))
    .filter((item) => item !== null)
    .slice(0, SNAPSHOT_ROW_LIMIT);

  state.sessionSnapshots = snapshots;
  state.latestSnapshot = snapshots.length ? snapshots[0] : null;
  renderSnapshotView();
}

async function startLiveSession() {
  let payload = collectRunPayload();
  if (!payload.expiry_date && payload.symbol) {
    await loadExpiries();
    payload = collectRunPayload();
    syncStartButtonState();
  }

  if (!hasValidContext(payload)) {
    showMessage("Please select symbol, expiry, and valid strike price before starting.", "error");
    return;
  }

  state.activeRunStartedAt = null;

  await apiRequest("/runs/start", {
    method: "POST",
    body: JSON.stringify(payload),
  });

  showResultsView();
  await refreshRunStatus();
  await refreshSessionTimeline();

  if (!state.latestSnapshot) {
    showMessage("Scheduled run started. Waiting for first interval snapshot.", "info");
  } else {
    showMessage("Scheduled run started.", "success");
  }
}

async function stopRun() {
  await apiRequest("/runs/stop", { method: "POST", body: "{}" });
  await refreshRunStatus();
  await refreshSessionTimeline();
  showMessage("Scheduled run stopped.", "info");
}

async function refreshResults() {
  await refreshRunStatus();
  await refreshSessionTimeline();
  showMessage("Results refreshed.", "info");
}

function startPolling() {
  if (state.pollId !== null) {
    return;
  }

  state.pollId = window.setInterval(async () => {
    try {
      await refreshRunStatus();
      if (!resultsView.classList.contains("hidden")) {
        await refreshSessionTimeline();
      }
    } catch (err) {
      // Keep polling resilient without interrupting the dashboard with transient fetch errors.
      setSyncState("Retrying", true);
      console.debug("Polling error:", err);
    }
  }, state.pollDelayMs);
}

function stopPolling() {
  if (state.pollId !== null) {
    window.clearInterval(state.pollId);
    state.pollId = null;
  }
}

function bindEvents() {
  modeSelect.addEventListener("change", async () => {
    populateSelect(symbolSelect, currentModeSymbols());
    try {
      await loadExpiries();
      resetSnapshotState();
      syncStartButtonState();
    } catch (err) {
      showMessage(err.message || "Failed to switch mode", "error");
    }
  });

  symbolSelect.addEventListener("change", async () => {
    try {
      await loadExpiries();
      resetSnapshotState();
      syncStartButtonState();
    } catch (err) {
      showMessage(err.message || "Failed to load expiries", "error");
    }
  });

  expirySelect.addEventListener("change", () => {
    resetSnapshotState();
    syncStartButtonState();
  });

  strikeInput.addEventListener("change", () => {
    resetSnapshotState();
    syncStartButtonState();
  });

  intervalSelect.addEventListener("change", () => {
    syncResultsContext();
  });

  loadSymbolsBtn.addEventListener("click", async () => {
    try {
      hideMessage();
      await loadSymbols();
      await loadExpiries();
      resetSnapshotState();
      syncStartButtonState();
      showMessage("Symbols refreshed.", "success");
    } catch (err) {
      showMessage(err.message || "Failed to load symbols", "error");
    }
  });

  loadExpiriesBtn.addEventListener("click", async () => {
    try {
      hideMessage();
      await loadExpiries();
      resetSnapshotState();
      syncStartButtonState();
      showMessage("Expiries refreshed.", "success");
    } catch (err) {
      showMessage(err.message || "Failed to load expiries", "error");
    }
  });

  openResultsBtn.addEventListener("click", async () => {
    try {
      hideMessage();
      await startLiveSession();
    } catch (err) {
      showMessage(err.message || "Failed to start live session", "error");
    }
  });

  backBtn.addEventListener("click", () => {
    stopPolling();
    showConfigView();
    resetSnapshotState();
    showMessage("Configuration view active.", "info");
  });

  refreshBtn.addEventListener("click", async () => {
    try {
      hideMessage();
      await refreshResults();
    } catch (err) {
      showMessage(err.message || "Failed to refresh results", "error");
    }
  });

  stopBtn.addEventListener("click", async () => {
    try {
      hideMessage();
      await stopRun();
    } catch (err) {
      showMessage(err.message || "Failed to stop run", "error");
    }
  });
}

async function initialize() {
  bindEvents();
  showConfigView();
  clearSnapshotView();
  syncResultsContext();
  syncStartButtonState();
  setSyncState("-");

  try {
    await loadSymbols();
    await loadExpiries();
    syncStartButtonState();
    await refreshRunStatus();
    showMessage("Ready. Configure inputs and start live session.", "info");
  } catch (err) {
    showMessage(err.message || "Initialization failed", "error");
  }
}

initialize();
