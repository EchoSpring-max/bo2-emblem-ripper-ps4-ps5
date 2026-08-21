const modeHints = {
  off: "The proxy is transparent. Nothing is captured or changed.",
  capture: "Open a player's profile or channel on your PS5. The emblem is saved automatically when the console downloads it.",
  inject: "Open your own emblem editor on the PS5. The selected emblem will be injected into the requested slot.",
};

let currentStatus = null;
let currentEmblems = [];
let showProfileOnly = false;

async function getJSON(url) {
  const response = await fetch(url);
  return response.json();
}

async function postJSON(url, body) {
  const response = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body || {}),
  });
  return response.json();
}

function getTargetSlotValue() {
  const input = document.getElementById("targetSlotInput");
  const value = input.value.trim();
  if (!value) return null;
  const parsed = Number.parseInt(value, 10);
  return Number.isNaN(parsed) ? null : parsed;
}

async function loadNetworkInfo() {
  const info = await getJSON("/api/network-info");
  const el = document.getElementById("setupValue");
  el.textContent = info.lan_ip
    ? `${info.lan_ip} : ${info.proxy_port}`
    : "couldn't detect - see docs/INSTALL.md";
}

function renderMode() {
  document.querySelectorAll(".mode-btn").forEach((btn) => {
    btn.classList.toggle("active", btn.dataset.mode === currentStatus.mode);
  });
  document.getElementById("modeHint").textContent = modeHints[currentStatus.mode] || "";

  const targetSlot = currentStatus.selected?.target_slot;
  const input = document.getElementById("targetSlotInput");
  if (document.activeElement !== input) {
    input.value = targetSlot === null || targetSlot === undefined ? "" : String(targetSlot);
  }
}

async function setMode(mode) {
  await postJSON("/api/mode", { mode });
  await refreshStatus();
}

document.querySelectorAll(".mode-btn").forEach((btn) => {
  btn.addEventListener("click", () => setMode(btn.dataset.mode));
});

function fmtDate(value) {
  if (!value) return "";
  return value.replace(" ", " | ").slice(0, 16);
}

function isSelected(emblem) {
  const selected = currentStatus.selected;
  return selected && selected.group === emblem.group && selected.slot === emblem.slot;
}

function renderEmblems() {
  const list = document.getElementById("emblemList");
  const empty = document.getElementById("emblemsEmpty");
  list.innerHTML = "";
  const visibleEmblems = showProfileOnly
    ? currentEmblems.filter((emblem) => emblem.is_profile)
    : currentEmblems;
  empty.style.display = visibleEmblems.length ? "none" : "";

  const template = document.getElementById("emblemCardTpl");
  for (const emblem of visibleEmblems) {
    const node = template.content.cloneNode(true);
    const card = node.querySelector(".emblem-card");
    card.classList.toggle("selected", isSelected(emblem));
    node.querySelector(".emblem-profile-badge").style.display = emblem.is_profile ? "" : "none";

    node.querySelector(".emblem-thumb").src = `/api/render/${encodeURIComponent(emblem.group)}/${emblem.slot}.png`;
    node.querySelector(".emblem-slot").textContent = `slot_${emblem.slot}`;
    node.querySelector(".emblem-date").textContent = emblem.captured_at || "";

    const labelInput = node.querySelector(".emblem-label-input");
    labelInput.value = emblem.label || `Emblem from ${emblem.captured_at || `${emblem.group}:${emblem.slot}`}`;
    labelInput.addEventListener("click", (event) => event.stopPropagation());
    labelInput.addEventListener("change", async () => {
      await postJSON(`/api/emblems/${encodeURIComponent(emblem.group)}/${emblem.slot}/label`, {
        label: labelInput.value,
      });
    });

    card.addEventListener("click", async () => {
      await postJSON("/api/select", {
        group: emblem.group,
        slot: emblem.slot,
        target_slot: getTargetSlotValue(),
      });
      await refreshStatus();
    });

    list.appendChild(node);
  }
}

document.getElementById("refreshBtn").addEventListener("click", refreshAll);
document.getElementById("profileOnlyToggle").addEventListener("change", (event) => {
  showProfileOnly = event.target.checked;
  renderEmblems();
});

document.getElementById("targetSlotInput").addEventListener("change", async (event) => {
  const raw = event.target.value.trim();
  if (raw && Number.isNaN(Number.parseInt(raw, 10))) {
    event.target.value = "";
  }
  if (!currentStatus?.selected) return;
  await postJSON("/api/target-slot", { target_slot: getTargetSlotValue() });
  await refreshStatus();
});

async function refreshStatus() {
  currentStatus = await getJSON("/api/status");
  renderMode();
  if (currentEmblems.length) renderEmblems();
}

async function refreshAll() {
  [currentStatus, currentEmblems] = await Promise.all([
    getJSON("/api/status"),
    getJSON("/api/emblems"),
  ]);
  renderMode();
  renderEmblems();
}

loadNetworkInfo();
refreshAll();
setInterval(refreshAll, 5000);
