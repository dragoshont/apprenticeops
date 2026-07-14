"use strict";
// CEOps experiment runner console.
// Real client: every call hits the paired runner's HTTP API. Token is held in
// memory only (never localStorage/cookie/URL), matching the runner's contract.

const state = { base: "", token: null, challenge: null, pairingId: null, poll: null };

const $ = (id) => document.getElementById(id);
const CLIENT_VERSION = "console-0.1.0";
const SCOPES = ["runner:read", "experiment:execute"];

function log(msg) {
  const line = `[${new Date().toISOString().slice(11, 19)}] ${msg}\n`;
  $("log").textContent += line;
  $("log").scrollTop = $("log").scrollHeight;
}

function randHex(n) {
  const a = new Uint8Array(n);
  crypto.getRandomValues(a);
  return [...a].map((b) => b.toString(16).padStart(2, "0")).join("");
}

async function api(path, { method = "GET", json = null, token = false, challenge = false } = {}) {
  const url = (state.base || "") + path;
  const headers = {};
  const init = { method, headers, cache: "no-store", redirect: "error", credentials: "omit" };
  if (json !== null) {
    headers["content-type"] = "application/json";
    init.body = JSON.stringify(json);
  }
  if (token && state.token) headers["x-ceops-token"] = state.token;
  if (challenge && state.challenge) headers["x-ceops-pairing-challenge"] = state.challenge;
  // Chrome Local Network Access: flag an http LAN target reached from an https
  // page so the request is exempt from the mixed-content block (harmless elsewhere).
  if (url.startsWith("http://") && location.protocol === "https:") {
    init.targetAddressSpace = "local";
  }
  const resp = await fetch(url, init);
  const text = await resp.text();
  let data;
  try { data = JSON.parse(text); } catch { data = { raw: text }; }
  if (!resp.ok) {
    const err = new Error(`http_${resp.status}`);
    err.status = resp.status;
    err.data = data;
    throw err;
  }
  return data;
}

async function connect() {
  const raw = $("runnerUrl").value.trim();
  state.base = raw.replace(/\/+$/, "");
  $("connectStatus").textContent = "connecting…";
  try {
    const h = await api("/v1/health");
    $("connectStatus").innerHTML =
      `<span class="badge ok">connected</span> runner <b>${h.instance_id}</b> · v${h.runner_version} · api ${h.api_version}` +
      (h.lan_bound ? ' · <span class="badge warn">LAN bind</span>' : "");
    log(`connected to runner ${h.instance_id} (v${h.runner_version})`);
    $("pairPanel").hidden = false;
  } catch (e) {
    $("connectStatus").innerHTML = `<span class="badge bad">failed</span> ${describe(e)}`;
    log(`connect failed: ${describe(e)}`);
  }
}

async function requestPairing() {
  $("pairBtn").disabled = true;
  state.challenge = randHex(24);
  try {
    const p = await api("/v1/pairing/request", {
      method: "POST",
      json: { challenge: state.challenge, scopes: SCOPES, client_version: CLIENT_VERSION },
    });
    state.pairingId = p.pairing_id;
    $("pairId").textContent = p.pairing_id;
    $("pairPhrase").textContent = p.confirm_phrase;
    $("pairInfo").hidden = false;
    log(`pairing requested (${p.pairing_id}); phrase ${p.confirm_phrase}`);
    startPolling(p.expires_at);
  } catch (e) {
    $("pairState").textContent = `pairing request failed: ${describe(e)}`;
    $("pairBtn").disabled = false;
    log(`pairing request failed: ${describe(e)}`);
  }
}

function startPolling(expiresAt) {
  clearInterval(state.poll);
  state.poll = setInterval(async () => {
    if (expiresAt && Date.now() / 1000 > expiresAt) {
      clearInterval(state.poll);
      $("pairState").textContent = "pairing expired — request again.";
      $("pairBtn").disabled = false;
      return;
    }
    try {
      const r = await api(`/v1/pairing/${state.pairingId}`, { challenge: true });
      if (r.status === "confirmed" && r.token) {
        clearInterval(state.poll);
        state.token = r.token;
        $("pairState").innerHTML = '<span class="badge ok">paired</span> token held in memory';
        log("paired — token received");
        await loadModels();
        $("runPanel").hidden = false;
      } else if (r.status === "denied") {
        clearInterval(state.poll);
        $("pairState").textContent = "pairing denied on the runner host.";
        $("pairBtn").disabled = false;
      } else {
        $("pairState").textContent = `waiting for approval on the runner host… (${r.status})`;
      }
    } catch (e) {
      $("pairState").textContent = `poll error: ${describe(e)}`;
    }
  }, 2000);
}

async function loadModels() {
  try {
    const r = await api("/v1/models", { token: true });
    const sel = $("modelSelect");
    sel.innerHTML = "";
    const models = (r.models || []).slice().sort((a, b) => (a.size || 0) - (b.size || 0));
    for (const m of models) {
      const opt = document.createElement("option");
      opt.value = m.name;
      const gb = m.size ? ` (${(m.size / 1e9).toFixed(2)} GB)` : "";
      opt.textContent = m.name + gb;
      sel.appendChild(opt);
    }
    log(`loaded ${models.length} models`);
  } catch (e) {
    log(`model load failed: ${describe(e)}`);
  }
}

async function run() {
  const model = $("modelSelect").value;
  const prompt = $("prompt").value;
  $("runBtn").disabled = true;
  $("result").textContent = "running…";
  $("runMeta").textContent = "";
  const t0 = performance.now();
  try {
    const r = await api("/v1/infer", {
      method: "POST",
      token: true,
      json: { model, prompt, options: { num_predict: 200 } },
    });
    $("result").textContent = r.response || "(empty response)";
    const wall = Math.round(performance.now() - t0);
    const parts = [`model ${r.model}`, `${wall} ms wall`];
    if (r.tokens_per_second) parts.push(`${r.tokens_per_second} tok/s`);
    if (r.eval_count) parts.push(`${r.eval_count} tokens`);
    $("runMeta").textContent = parts.join(" · ");
    log(`inference ok: ${r.eval_count || "?"} tokens, ${r.tokens_per_second || "?"} tok/s`);
  } catch (e) {
    $("result").textContent = `run failed: ${describe(e)}`;
    log(`inference failed: ${describe(e)}`);
  } finally {
    $("runBtn").disabled = false;
  }
}

function describe(e) {
  if (e && e.data && e.data.detail) {
    return typeof e.data.detail === "string" ? e.data.detail : JSON.stringify(e.data.detail);
  }
  return (e && e.message) || String(e);
}

async function init() {
  $("connectBtn").addEventListener("click", connect);
  $("pairBtn").addEventListener("click", requestPairing);
  $("runBtn").addEventListener("click", run);

  // Runner-served mode: if same-origin health works, connect automatically.
  try {
    const h = await api("/v1/health");
    $("runnerUrl").value = location.origin;
    $("connectStatus").innerHTML =
      `<span class="badge ok">connected</span> runner <b>${h.instance_id}</b> · served locally`;
    $("pairPanel").hidden = false;
    log("runner-served console: connected to same-origin runner");
  } catch {
    // Hosted mode (e.g. experiment.ceops.org): prefill the demo runner address.
    $("runnerUrl").value = "http://192.168.1.200:8799";
    log("hosted console: enter your runner address and connect");
  }
}

init();
