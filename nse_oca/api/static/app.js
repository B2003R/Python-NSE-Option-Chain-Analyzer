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
const analyzeBtn = document.getElementById("analyzeBtn");
const startBtn = document.getElementById("startBtn");
const stopBtn = document.getElementById("stopBtn");
const triggerBtn = document.getElementById("triggerBtn");

const messageBox = document.getElementById("messageBox");
const resultsContext = document.getElementById("resultsContext");

const statusRunning = document.getElementById("statusRunning");
const statusNextRun = document.getElementById("statusNextRun");
const statusLastRun = document.getElementById("statusLastRun");
const statusRuns = document.getElementById("statusRuns");
const statusError = document.getElementById("statusError");

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

const state = {
  symbols: { indices: [], stocks: [] },
  pollId: null,
  latestSnapshot: null,
};

function showMessage(text, type = "info") {
  messageBox.textContent = text;
  messageBox.className = `message ${type}`;
}

function hideMessage() {
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
  });

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

  resultsContext.textContent = `${payload.mode} | ${payload.symbol} | ${payload.expiry_date} | Strike ${payload.strike_price}`;
}

function setText(node, value) {
  node.textContent = value;
}

function setSignalClass(node, kind, value) {
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

  if (normalized === "yes") {
    node.classList.add("signal-positive");
  } else if (normalized === "no") {
    node.classList.add("signal-negative");
  } else {
    node.classList.add("signal-neutral");
  }
}

function clearSnapshotView() {
  summaryBody.innerHTML = '<tr><td colspan="9" class="placeholder">No snapshot data yet.</td></tr>';

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
  setSignalClass(signalCallExits, "yes-no", null);
  setSignalClass(signalPutExits, "yes-no", null);
  setSignalClass(signalCallItm, "yes-no", null);
  setSignalClass(signalPutItm, "yes-no", null);
}

function renderSummaryRow(snapshot) {
  if (!snapshot) {
    summaryBody.innerHTML = '<tr><td colspan="9" class="placeholder">No snapshot data yet.</td></tr>';
    return;
  }

  summaryBody.innerHTML = `
    <tr>
      <td>${snapshot.server_timestamp || "-"}</td>
      <td>${formatValue(snapshot.underlying_value, 2)}</td>
      <td>${formatValue(snapshot.call_sum, 1)}</td>
      <td>${formatValue(snapshot.put_sum, 1)}</td>
      <td>${formatValue(snapshot.difference, 1)}</td>
      <td>${formatValue(snapshot.call_boundary, 1)}</td>
      <td>${formatValue(snapshot.put_boundary, 1)}</td>
      <td>${formatValue(snapshot.call_itm_ratio, 1)}</td>
      <td>${formatValue(snapshot.put_itm_ratio, 1)}</td>
    </tr>
  `;
}

function renderBoundaryPanels(snapshot) {
  if (!snapshot) {
    clearSnapshotView();
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
  setSignalClass(signalCallExits, "yes-no", callExitsValue);
  setSignalClass(signalPutExits, "yes-no", putExitsValue);
  setSignalClass(signalCallItm, "yes-no", callItmValue);
  setSignalClass(signalPutItm, "yes-no", putItmValue);
}

function renderSnapshot(snapshot) {
  if (!snapshot) {
    clearSnapshotView();
    return;
  }

  renderSummaryRow(snapshot);
  renderBoundaryPanels(snapshot);
}

function resetSnapshotState() {
  state.latestSnapshot = null;
  syncResultsContext();
  if (!resultsView.classList.contains("hidden")) {
    renderSnapshot(null);
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

async function refreshRunStatus() {
  const status = await apiRequest("/runs/status");
  statusRunning.textContent = status.running ? "Yes" : "No";
  statusNextRun.textContent = status.next_run_at || "-";
  statusLastRun.textContent = status.last_run_at || "-";
  statusRuns.textContent = String(status.total_runs || 0);
  statusError.textContent = status.last_error || "-";

  if (status.running) {
    startPolling();
  } else {
    stopPolling();
  }
}

async function refreshLatestSnapshot() {
  const query = snapshotQueryString();
  if (!query) {
    state.latestSnapshot = null;
    renderSnapshot(null);
    return;
  }

  let latest = null;

  try {
    const raw = await apiRequest(`/snapshots/latest?${query}`);
    latest = normalizeSnapshot(raw);
  } catch (err) {
    if (!String(err.message || "").includes("No snapshot found")) {
      throw err;
    }
  }

  if (latest) {
    state.latestSnapshot = latest;
  }

  renderSnapshot(state.latestSnapshot);
}

async function openResultsView() {
  const payload = collectRunPayload();
  if (!hasValidContext(payload)) {
    showMessage("Please provide mode, symbol, expiry date, and strike price.", "error");
    return;
  }

  showResultsView();
  await refreshRunStatus();
  await refreshLatestSnapshot();

  if (!state.latestSnapshot) {
    showMessage("No snapshot found yet. Use Analyze Once or Start Scheduled Run.", "info");
  } else {
    showMessage("Analyzer view ready.", "info");
  }
}

async function analyzeOnce() {
  const payload = collectRunPayload();
  if (!hasValidContext(payload)) {
    showMessage("Please provide mode, symbol, expiry date, and strike price.", "error");
    return;
  }

  const requestBody = {
    mode: payload.mode,
    symbol: payload.symbol,
    expiry_date: payload.expiry_date,
    strike_price: payload.strike_price,
  };

  const data = await apiRequest(`/analyze?persist=${payload.persist ? "true" : "false"}`, {
    method: "POST",
    body: JSON.stringify(requestBody),
  });

  state.latestSnapshot = normalizeSnapshot(data.snapshot || data.analysis || null);
  showResultsView();
  renderSnapshot(state.latestSnapshot);
  await refreshRunStatus();

  if (payload.persist) {
    await refreshLatestSnapshot();
  }

  showMessage("Analysis cycle completed.", "success");
}

async function startRun() {
  const payload = collectRunPayload();
  if (!hasValidContext(payload)) {
    showMessage("Please provide mode, symbol, expiry date, and strike price.", "error");
    return;
  }

  await apiRequest("/runs/start", {
    method: "POST",
    body: JSON.stringify(payload),
  });

  showResultsView();
  await refreshRunStatus();
  await refreshLatestSnapshot();
  showMessage("Scheduled run started.", "success");
  startPolling();
}

async function stopRun() {
  await apiRequest("/runs/stop", { method: "POST", body: "{}" });
  await refreshRunStatus();
  showMessage("Scheduled run stopped.", "info");
}

async function triggerRunNow() {
  await apiRequest("/runs/trigger", { method: "POST", body: "{}" });
  await refreshRunStatus();
  await refreshLatestSnapshot();
  showMessage("Immediate cycle executed.", "success");
}

async function refreshResults() {
  await refreshRunStatus();
  await refreshLatestSnapshot();
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
        await refreshLatestSnapshot();
      }
    } catch (err) {
      showMessage(err.message || "Polling error", "error");
    }
  }, 9000);
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
    } catch (err) {
      showMessage(err.message || "Failed to switch mode", "error");
    }
  });

  symbolSelect.addEventListener("change", async () => {
    try {
      await loadExpiries();
      resetSnapshotState();
    } catch (err) {
      showMessage(err.message || "Failed to load expiries", "error");
    }
  });

  expirySelect.addEventListener("change", () => {
    resetSnapshotState();
  });

  strikeInput.addEventListener("change", () => {
    resetSnapshotState();
  });

  loadSymbolsBtn.addEventListener("click", async () => {
    try {
      hideMessage();
      await loadSymbols();
      await loadExpiries();
      resetSnapshotState();
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
      showMessage("Expiries refreshed.", "success");
    } catch (err) {
      showMessage(err.message || "Failed to load expiries", "error");
    }
  });

  openResultsBtn.addEventListener("click", async () => {
    try {
      hideMessage();
      await openResultsView();
    } catch (err) {
      showMessage(err.message || "Failed to open results view", "error");
    }
  });

  backBtn.addEventListener("click", () => {
    showConfigView();
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

  analyzeBtn.addEventListener("click", async () => {
    try {
      hideMessage();
      await analyzeOnce();
    } catch (err) {
      showMessage(err.message || "Analyze failed", "error");
    }
  });

  startBtn.addEventListener("click", async () => {
    try {
      hideMessage();
      await startRun();
    } catch (err) {
      showMessage(err.message || "Failed to start run", "error");
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

  triggerBtn.addEventListener("click", async () => {
    try {
      hideMessage();
      await triggerRunNow();
    } catch (err) {
      showMessage(err.message || "Trigger failed", "error");
    }
  });
}

async function initialize() {
  bindEvents();
  showConfigView();
  renderSnapshot(null);
  syncResultsContext();

  try {
    await loadSymbols();
    await loadExpiries();
    await refreshRunStatus();
    showMessage("Ready. Configure the run and open results view.", "info");
  } catch (err) {
    showMessage(err.message || "Initialization failed", "error");
  }
}

initialize();
