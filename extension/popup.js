async function refreshAuthView() {
  const user = await SakanAPI.me();
  const loginView = document.getElementById("login-view");
  const accountView = document.getElementById("account-view");

  if (user) {
    loginView.hidden = true;
    accountView.hidden = false;
    document.getElementById("account-email").textContent = user.email;
  } else {
    loginView.hidden = false;
    accountView.hidden = true;
  }
}

async function handleLogin(e) {
  e.preventDefault();
  const email = document.getElementById("login-email").value;
  const password = document.getElementById("login-password").value;
  const errorEl = document.getElementById("login-error");
  errorEl.hidden = true;

  try {
    await SakanAPI.login(email, password);
    await refreshAuthView();
  } catch (err) {
    errorEl.textContent = err instanceof Error ? err.message : "Sign-in failed.";
    errorEl.hidden = false;
  }
}

async function handleLogout() {
  await SakanAPI.clearToken();
  await refreshAuthView();
}

async function handleCompsSearch(e) {
  e.preventDefault();
  const community = document.getElementById("comps-community").value.trim();
  const bedrooms = document.getElementById("comps-bedrooms").value;
  const resultsEl = document.getElementById("comps-results");
  resultsEl.textContent = "Searching…";

  try {
    const comps = await SakanAPI.fetchComps({ community, bedrooms, limit: 10 });
    if (!comps.length) {
      resultsEl.textContent = "No matching transactions in the seeded dataset.";
      return;
    }
    resultsEl.innerHTML = "";
    for (const c of comps) {
      const row = document.createElement("div");
      row.className = "comp-row";
      row.innerHTML = `<span>${c.bedrooms ?? "?"}BR ${c.property_type ?? ""} — ${c.community ?? ""}</span><span class="price">AED ${Math.round(c.price ?? 0).toLocaleString()}</span>`;
      resultsEl.appendChild(row);
    }
  } catch (err) {
    resultsEl.textContent = err instanceof Error ? err.message : "Comps search failed.";
  }
}

async function handleDealSubmit(e) {
  e.preventDefault();
  const query = document.getElementById("deal-query").value.trim();
  const statusEl = document.getElementById("deal-status");
  statusEl.hidden = false;
  if (!query) {
    statusEl.textContent = "Type a deal question first.";
    return;
  }

  statusEl.textContent = "Submitting…";
  try {
    const queryId = await SakanAPI.submitDealQuery(query);
    const base = await SakanAPI.getBackendUrl();
    const url = SakanAPI.dealUrl(base, queryId);
    statusEl.textContent = "Submitted — opening the full result in a new tab.";
    chrome.tabs.create({ url });
  } catch (err) {
    statusEl.textContent = err instanceof Error ? err.message : "Could not submit the query.";
  }
}

const PENDING_QUERY_KEY = "sakan_ext_pending_query";

async function loadPendingSelection() {
  // Picks up text the user right-clicked -> "Check with Sakan AI" on
  // (see background.js's context menu), so a listing description copied
  // from a page shows up pre-filled here instead of being retyped.
  const { [PENDING_QUERY_KEY]: pending } = await chrome.storage.local.get(PENDING_QUERY_KEY);
  if (pending) {
    document.getElementById("deal-query").value = pending;
    await chrome.storage.local.remove(PENDING_QUERY_KEY);
    chrome.action.setBadgeText({ text: "" });
  }
}

async function init() {
  const backendUrl = await SakanAPI.getBackendUrl();
  document.getElementById("backend-url-label").textContent = backendUrl;

  document.getElementById("login-form").addEventListener("submit", handleLogin);
  document.getElementById("logout-btn").addEventListener("click", handleLogout);
  document.getElementById("comps-form").addEventListener("submit", handleCompsSearch);
  document.getElementById("deal-form").addEventListener("submit", handleDealSubmit);
  document.getElementById("settings-btn").addEventListener("click", () => chrome.runtime.openOptionsPage());

  await refreshAuthView();
  await loadPendingSelection();
}

document.addEventListener("DOMContentLoaded", init);
