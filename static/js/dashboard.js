// Real-time-ish order dashboard: polls the JSON feed every few seconds,
// renders cards, plays an audio alert on genuinely new orders, and wires
// up the Accept / In Kitchen / Ready / Completed / Cancel buttons.
(function () {
  const cfg = window.DASHBOARD_CONFIG;
  const grid = document.getElementById("orders-grid");
  const emptyState = document.getElementById("empty-state");
  const sound = document.getElementById("new-order-sound");
  const soundToggle = document.getElementById("sound-toggle");
  const completedCountEl = document.getElementById("completed-count");

  const STATUS_FLOW = ["pending", "accepted", "in_kitchen", "ready", "delivered"];
  const NEXT_LABEL = {
    pending: cfg.labels.accept,
    accepted: cfg.labels.inKitchen,
    in_kitchen: cfg.labels.ready,
    ready: cfg.labels.completed,
  };
  const STATUS_COLOR = {
    pending: "bg-amber-100 text-amber-800 dark:bg-amber-900/30 dark:text-amber-300",
    accepted: "bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-300",
    in_kitchen: "bg-purple-100 text-purple-800 dark:bg-purple-900/30 dark:text-purple-300",
    ready: "bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-300",
    delivered: "bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-300",
    cancelled: "bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-300",
  };

  let soundOn = localStorage.getItem("dashboard_sound") !== "off";
  let knownMaxId = parseInt(sessionStorage.getItem("dashboard_known_max_id") || "0", 10);
  let firstLoad = true;

  function refreshSoundLabel() {
    soundToggle.textContent = soundOn ? `🔔 ${cfg.labels.sound_on || "Sound on"}` : `🔕 ${cfg.labels.sound_off || "Sound off"}`;
  }
  soundToggle.addEventListener("click", () => {
    soundOn = !soundOn;
    localStorage.setItem("dashboard_sound", soundOn ? "on" : "off");
    refreshSoundLabel();
  });
  refreshSoundLabel();

  function csrfToken() {
    const match = document.cookie.match(/csrftoken=([^;]+)/);
    return match ? match[1] : "";
  }

  function orderCardHtml(order) {
    const nextStatus = STATUS_FLOW[STATUS_FLOW.indexOf(order.status) + 1];
    const nextLabel = NEXT_LABEL[order.status];

    const geoLine = order.geo_verified
      ? `<span class="text-xs text-green-600 dark:text-green-400">📍 ${cfg.labels.verified}</span>`
      : `<span class="text-xs text-red-600 dark:text-red-400">⚠️ ${cfg.labels.notVerified}</span>`;
    const distanceLine = order.distance_m != null
      ? `<span class="text-xs text-gray-400"> · ${Math.round(order.distance_m)}${cfg.labels.distance}</span>` : "";

    const photoHtml = order.photo_url
      ? `<img src="${order.photo_url}" alt="${cfg.labels.photo}" class="w-full h-28 object-cover rounded-lg mb-2" loading="lazy">`
      : "";

    const itemsHtml = order.items.map(
      (i) => `<li>${i.qty}× ${escapeHtml(i.name)}${i.notes ? ` <span class="text-gray-400">(${escapeHtml(i.notes)})</span>` : ""}</li>`
    ).join("");

    const canCancel = order.status !== "delivered" && order.status !== "cancelled";

    return `
      <div class="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 p-4" data-order-id="${order.id}">
        <div class="flex items-center justify-between mb-2">
          <span class="font-semibold">${cfg.labels.table} ${order.table_number}</span>
          <span class="text-xs px-2 py-1 rounded-full ${STATUS_COLOR[order.status] || ""}">${order.status_display}</span>
        </div>
        ${photoHtml}
        <p class="text-sm font-medium">${escapeHtml(order.full_name)}</p>
        <p class="text-xs text-gray-500 dark:text-gray-400 mb-1">${escapeHtml(order.phone_number)}</p>
        <p class="mb-2">${geoLine}${distanceLine}</p>
        <p class="text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">${cfg.labels.items}</p>
        <ul class="text-xs space-y-0.5 text-gray-700 dark:text-gray-300 mb-2">${itemsHtml}</ul>
        <p class="text-sm font-semibold">${cfg.labels.total}: ${order.total_amount} UZS</p>
        <div class="flex flex-wrap gap-2 mt-3">
          ${nextStatus ? `<button class="status-btn bg-brand-600 text-white text-xs px-3 py-1.5 rounded-lg" data-id="${order.id}" data-status="${nextStatus}">${nextLabel} →</button>` : ""}
          ${canCancel ? `<button class="status-btn bg-red-50 text-red-700 dark:bg-red-900/30 dark:text-red-300 text-xs px-3 py-1.5 rounded-lg" data-id="${order.id}" data-status="cancelled">${cfg.labels.cancel}</button>` : ""}
        </div>
      </div>`;
  }

  function escapeHtml(str) {
    const div = document.createElement("div");
    div.textContent = str ?? "";
    return div.innerHTML;
  }

  async function updateStatus(orderId, status) {
    const url = cfg.statusUrlTemplate.replace("__ID__", orderId);
    await fetch(url, {
      method: "POST",
      headers: { "X-CSRFToken": csrfToken(), "Content-Type": "application/x-www-form-urlencoded" },
      body: `status=${encodeURIComponent(status)}`,
    });
    fetchFeed();
  }

  function bindButtons() {
    grid.querySelectorAll(".status-btn").forEach((btn) => {
      btn.addEventListener("click", () => updateStatus(btn.dataset.id, btn.dataset.status));
    });
  }

  async function fetchFeed() {
    try {
      const res = await fetch(`${cfg.feedUrl}?since_id=${knownMaxId}`);
      const data = await res.json();

      if (!data.orders.length) {
        grid.querySelectorAll("[data-order-id]").forEach((el) => el.remove());
        emptyState.classList.remove("hidden");
      } else {
        emptyState.classList.add("hidden");
        grid.innerHTML = data.orders.map(orderCardHtml).join("") + emptyState.outerHTML;
        bindButtons();
      }

      if (!firstLoad && data.max_id > knownMaxId && soundOn) {
        sound.currentTime = 0;
        sound.play().catch(() => {});
      }
      if (data.max_id) {
        knownMaxId = data.max_id;
        sessionStorage.setItem("dashboard_known_max_id", String(knownMaxId));
      }
      firstLoad = false;
    } catch (e) {
      // network hiccup — try again next tick
    }
  }

  fetchFeed();
  setInterval(fetchFeed, 4000);
})();
