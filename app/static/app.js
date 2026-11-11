const $ = (selector) => document.querySelector(selector);
const $$ = (selector) => [...document.querySelectorAll(selector)];

let state = null;
let toastTimer;

function escapeHtml(value) {
  return String(value ?? "").replace(/[&<>"']/g, (character) => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#39;",
  })[character]);
}

async function request(path, options = {}) {
  const response = await fetch(path, {
    ...options,
    headers: { "Content-Type": "application/json", ...options.headers },
  });
  const payload = response.status === 204 ? null : await response.json();
  if (!response.ok) {
    const message = payload?.detail || "That didn't work. Try again.";
    throw new Error(message);
  }
  return payload;
}

function showToast(message) {
  const toast = $("#toast");
  toast.textContent = message;
  toast.classList.add("visible");
  window.clearTimeout(toastTimer);
  toastTimer = window.setTimeout(() => toast.classList.remove("visible"), 2800);
}

function setView(name) {
  $$(".view").forEach((view) => view.classList.toggle("active", view.id === `view-${name}`));
  $$(".nav-link").forEach((button) => button.classList.toggle("active", button.dataset.view === name));
  if (name === "chat") {
    window.setTimeout(() => $("#chat-input").focus(), 100);
    scrollMessages();
  }
  if (name === "connections") loadCalendar();
}

function formatTime(value, options = {}) {
  if (!value) return "";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat(undefined, {
    month: "short", day: "numeric", hour: "numeric", minute: "2-digit", ...options,
  }).format(date);
}

function setClock() {
  const now = new Date();
  $("#today-date").textContent = new Intl.DateTimeFormat(undefined, {
    weekday: "long", month: "long", day: "numeric",
  }).format(now).toUpperCase();
  $("#current-time").textContent = new Intl.DateTimeFormat(undefined, {
    hour: "2-digit", minute: "2-digit",
  }).format(now);
}

function renderCompactItems(target, items, kind) {
  if (!items.length) {
    target.innerHTML = `<div class="empty-state">${kind === "task" ? "Nothing urgent on this list." : "No reminders coming up."}</div>`;
    return;
  }
  target.innerHTML = items.slice(0, 4).map((item) => {
    const time = kind === "reminder" ? formatTime(item.due_at, { year: undefined, weekday: undefined }) : "OPEN";
    return `<div class="compact-item">
      <i class="compact-marker ${kind === "reminder" ? "coral" : ""}"></i>
      <span class="compact-copy">${escapeHtml(item.content)}</span>
      <span class="compact-time">${escapeHtml(time)}</span>
    </div>`;
  }).join("");
}

function renderTasks(tasks) {
  $("#task-count").textContent = String(tasks.length).padStart(2, "0");
  $("#all-task-count").textContent = String(tasks.length);
  renderCompactItems($("#today-tasks"), tasks, "task");
  if (!tasks.length) {
    $("#all-tasks").innerHTML = '<div class="empty-state">A clear list is a good place to start.</div>';
    return;
  }
  $("#all-tasks").innerHTML = tasks.map((task) => `
    <div class="list-row">
      <button class="icon-action" data-action="complete-task" data-id="${task.id}" aria-label="Complete task ${escapeHtml(task.content)}" title="Complete task">○</button>
      <span class="list-row-text">${escapeHtml(task.content)}</span>
      <button class="icon-action" data-action="delete-task" data-id="${task.id}" aria-label="Delete task ${escapeHtml(task.content)}" title="Delete task">×</button>
    </div>`).join("");
}

function renderReminders(reminders) {
  $("#reminder-count").textContent = String(reminders.length).padStart(2, "0");
  $("#all-reminder-count").textContent = String(reminders.length);
  renderCompactItems($("#today-reminders"), reminders, "reminder");
  if (!reminders.length) {
    $("#all-reminders").innerHTML = '<div class="empty-state">No reminders yet.</div>';
    return;
  }
  $("#all-reminders").innerHTML = reminders.map((reminder) => `
    <div class="list-row">
      <i class="compact-marker coral"></i>
      <span class="list-row-text">${escapeHtml(reminder.content)}<span class="list-row-sub">${escapeHtml(formatTime(reminder.due_at))}</span></span>
      <button class="icon-action" data-action="cancel-reminder" data-id="${reminder.id}" aria-label="Cancel reminder ${escapeHtml(reminder.content)}" title="Cancel reminder">×</button>
    </div>`).join("");
}

function renderMemories(memories) {
  $("#memory-count").textContent = String(memories.length).padStart(2, "0");
  $("#memory-count-label").textContent = String(memories.length);
  const formButton = $("#memory-form button");
  const full = memories.length >= 20;
  $("#memory-input").disabled = full;
  formButton.disabled = full;
  formButton.title = full ? "Remove a memory before adding another" : "Save memory";
  if (!memories.length) {
    $("#memory-list").innerHTML = '<div class="empty-memory">Nothing saved yet. Add only what you want the companion to remember.</div>';
    return;
  }
  $("#memory-list").innerHTML = memories.map((memory, index) => `
    <article class="memory-card">
      <span class="memory-index">${String(index + 1).padStart(2, "0")}</span>
      <span class="memory-content">${escapeHtml(memory.content)}</span>
      <button class="icon-action" data-action="delete-memory" data-id="${memory.id}" aria-label="Delete memory ${escapeHtml(memory.content)}" title="Delete memory">×</button>
    </article>`).join("");
}

function renderMessages(messages) {
  const list = $("#messages");
  if (!messages.length) {
    list.innerHTML = '<div class="message-empty">No conversation here yet.<br>Start wherever you are.</div>';
    return;
  }
  list.innerHTML = messages.map((message) => {
    const role = message.role === "user" ? "YOU" : "NOVA";
    const proactive = message.proactive ? " proactive" : "";
    return `<article class="message ${message.role}${proactive}">
      <div class="message-meta"><span class="message-role">${role}</span><time>${escapeHtml(formatTime(message.ts))}</time></div>
      <div class="message-bubble">${escapeHtml(message.content)}</div>
    </article>`;
  }).join("");
  scrollMessages();
}

function scrollMessages() {
  const list = $("#messages");
  list.scrollTop = list.scrollHeight;
}

function setConnectionStatus(id, ready, readyText = "CONNECTED", pendingText = "NOT SET UP") {
  const element = $(id);
  element.textContent = ready ? readyText : pendingText;
  element.classList.toggle("ready", ready);
}

function renderState(nextState) {
  state = nextState;
  const profile = state.profile;
  const firstName = profile.name.trim().split(/\s+/)[0] || "there";
  $("#greeting").textContent = `Hey, ${firstName}.`;
  $("#footer-timezone").textContent = profile.timezone.toUpperCase();
  $("#timezone-label").textContent = profile.timezone.toUpperCase();
  $("#checkin-toggle").checked = state.checkin.enabled;
  $("#checkin-label").textContent = state.checkin.enabled ? "Checking in is on" : "Check-ins are paused";
  $("#checkin-summary").textContent = state.checkin.enabled ? "ON" : "PAUSED";
  $("#proactive-channel").textContent = state.checkin.channel.toUpperCase();

  const connections = state.connections;
  $("#local-status").textContent = "LOCAL SERVER";
  $("#model-status").textContent = connections.model_ready ? `${connections.provider} · ready` : "Model not set up";
  $("#model-dot").classList.toggle("ready", connections.model_ready);
  $("#model-connection-name").textContent = connections.model_ready ? connections.provider : "Model API";
  $("#model-connection-detail").textContent = connections.model_ready ? connections.model : "Add a provider key in .env";
  setConnectionStatus("#model-connection-state", connections.model_ready, "READY");
  setConnectionStatus("#telegram-state", connections.telegram_ready, "READY");
  setConnectionStatus("#discord-state", connections.discord_ready, "READY");
  setConnectionStatus("#calendar-state", connections.calendar_ready, "CONNECTED");

  const chatInput = $("#chat-input");
  const sendButton = $("#send-button");
  chatInput.disabled = !connections.model_ready;
  sendButton.disabled = !connections.model_ready;
  $("#chat-status").innerHTML = connections.model_ready
    ? 'PRIVATE SESSION <span>·</span> YOUR MODEL API'
    : 'ADD AN API KEY TO .ENV <span>·</span> CHAT IS DISABLED';

  renderTasks(state.tasks);
  renderReminders(state.reminders);
  renderMemories(state.memories);
  renderMessages(state.messages);
}

async function refreshState() {
  try {
    renderState(await request("/api/state"));
  } catch (error) {
    $("#local-status").textContent = "SERVER ISSUE";
    showToast(error.message);
  }
}

async function loadCalendar() {
  const host = $("#calendar-events");
  host.innerHTML = "";
  try {
    const data = await request("/api/calendar");
    setConnectionStatus("#calendar-state", data.connected, "CONNECTED");
    if (!data.connected) {
      $("#calendar-detail").textContent = "Calendar events only · local OAuth setup needed";
      return;
    }
    $("#calendar-detail").textContent = "Calendar events only · read access";
    if (!data.events.length) {
      host.innerHTML = '<div class="empty-state">No upcoming events.</div>';
      return;
    }
    host.innerHTML = data.events.map((event) => `
      <div class="calendar-event"><strong>${escapeHtml(event.summary)}</strong><span>${escapeHtml(formatTime(event.start))}</span></div>`).join("");
  } catch {
    $("#calendar-detail").textContent = "Calendar is unavailable right now";
  }
}

function localDateTimeValue(date) {
  const local = new Date(date.getTime() - date.getTimezoneOffset() * 60000);
  return local.toISOString().slice(0, 16);
}

function setDefaultReminderTime() {
  $("#reminder-due").value = localDateTimeValue(new Date(Date.now() + 60 * 60 * 1000));
}

async function submitForm(form, path, makeBody, successMessage) {
  try {
    await request(path, { method: "POST", body: JSON.stringify(makeBody()) });
    form.reset();
    if (form.id === "reminder-form") setDefaultReminderTime();
    showToast(successMessage);
    await refreshState();
  } catch (error) {
    showToast(error.message);
  }
}

function bindEvents() {
  $$(".nav-link").forEach((button) => button.addEventListener("click", () => setView(button.dataset.view)));
  $$('[data-open-view="chat"]').forEach((button) => button.addEventListener("click", () => setView("chat")));
  $$('[data-open-view="tasks"]').forEach((button) => button.addEventListener("click", () => setView("tasks")));
  $("#refresh-button").addEventListener("click", refreshState);

  $("#chat-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    const input = $("#chat-input");
    const content = input.value.trim();
    if (!content || !state?.connections.model_ready) return;
    const send = $("#send-button");
    input.disabled = true;
    send.disabled = true;
    $("#chat-status").textContent = "NOVA IS THINKING";
    try {
      await request("/api/chat", { method: "POST", body: JSON.stringify({ content }) });
      input.value = "";
      await refreshState();
    } catch (error) {
      showToast(error.message);
    } finally {
      input.disabled = !state?.connections.model_ready;
      send.disabled = !state?.connections.model_ready;
      $("#chat-status").innerHTML = state?.connections.model_ready
        ? 'PRIVATE SESSION <span>·</span> YOUR MODEL API'
        : 'ADD AN API KEY TO .ENV <span>·</span> CHAT IS DISABLED';
      input.focus();
    }
  });

  $("#task-form").addEventListener("submit", (event) => {
    event.preventDefault();
    submitForm(event.currentTarget, "/api/tasks", () => ({ content: $("#task-input").value.trim() }), "Task added.");
  });

  $("#reminder-form").addEventListener("submit", (event) => {
    event.preventDefault();
    submitForm(event.currentTarget, "/api/reminders", () => ({
      content: $("#reminder-input").value.trim(),
      due_at: new Date($("#reminder-due").value).toISOString(),
    }), "Reminder set.");
  });

  $("#memory-form").addEventListener("submit", (event) => {
    event.preventDefault();
    submitForm(event.currentTarget, "/api/memories", () => ({ content: $("#memory-input").value.trim() }), "Memory saved.");
  });

  $("#checkin-toggle").addEventListener("change", async (event) => {
    const enabled = event.currentTarget.checked;
    try {
      await request("/api/checkin", { method: "PATCH", body: JSON.stringify({ enabled }) });
      showToast(enabled ? "Adaptive check-ins are on." : "Adaptive check-ins paused.");
      await refreshState();
    } catch (error) {
      event.currentTarget.checked = !enabled;
      showToast(error.message);
    }
  });

  document.addEventListener("click", async (event) => {
    const button = event.target.closest("[data-action]");
    if (!button) return;
    const { action, id } = button.dataset;
    const routes = {
      "complete-task": [`/api/tasks/${id}/done`, "PATCH", "Task complete."],
      "delete-task": [`/api/tasks/${id}`, "DELETE", "Task deleted."],
      "cancel-reminder": [`/api/reminders/${id}`, "DELETE", "Reminder cancelled."],
      "delete-memory": [`/api/memories/${id}`, "DELETE", "Memory removed."],
    };
    const route = routes[action];
    if (!route) return;
    button.disabled = true;
    try {
      await request(route[0], { method: route[1] });
      showToast(route[2]);
      await refreshState();
    } catch (error) {
      button.disabled = false;
      showToast(error.message);
    }
  });
}

setClock();
window.setInterval(setClock, 30_000);
setDefaultReminderTime();
bindEvents();
refreshState();