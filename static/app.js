const refreshButton = document.querySelector("#refresh-button");
const exportButton = document.querySelector("#export-button");
const taskForm = document.querySelector("#task-form");
const leadForm = document.querySelector("#lead-form");
const taskFilter = document.querySelector("#task-filter");
const taskList = document.querySelector("#task-list");
const leadList = document.querySelector("#lead-list");
const activityList = document.querySelector("#activity-list");
const taskTemplate = document.querySelector("#task-template");
const leadTemplate = document.querySelector("#lead-template");
const activityTemplate = document.querySelector("#activity-template");

const openTaskCount = document.querySelector("#open-task-count");
const highPriorityCount = document.querySelector("#high-priority-count");
const leadCount = document.querySelector("#lead-count");
const serverTime = document.querySelector("#server-time");

let appState = {
  tasks: [],
  leads: [],
  activity: [],
  summary: {},
  serverTime: "",
};

async function api(path, options = {}) {
  const response = await fetch(path, {
    headers: {
      "Content-Type": "application/json",
    },
    ...options,
  });

  const data = await response.json();
  if (!response.ok) {
    throw new Error(data.error || "Request failed");
  }

  return data;
}

async function loadDashboard() {
  const data = await api("/api/status");
  appState = data;
  render();
}

function render() {
  openTaskCount.textContent = String(appState.summary.openTaskCount || 0);
  highPriorityCount.textContent = String(appState.summary.highPriorityCount || 0);
  leadCount.textContent = String(appState.summary.leadCount || 0);
  serverTime.textContent = formatTime(appState.serverTime);

  renderTasks();
  renderLeads();
  renderActivity();
}

function renderTasks() {
  taskList.innerHTML = "";

  const filter = taskFilter.value;
  const tasks = appState.tasks.filter((task) => filter === "all" || task.status === filter);

  if (tasks.length === 0) {
    taskList.appendChild(emptyState("No tasks match the current filter."));
    return;
  }

  tasks.forEach((task) => {
    const fragment = taskTemplate.content.cloneNode(true);
    const card = fragment.querySelector(".item-card");
    const title = fragment.querySelector(".item-title");
    const meta = fragment.querySelector(".item-meta");
    const detail = fragment.querySelector(".item-detail");
    const priority = fragment.querySelector(".item-priority");
    const statusSelect = fragment.querySelector(".status-select");
    const deleteButton = fragment.querySelector(".delete-button");

    title.textContent = task.title;
    meta.textContent = `${labelForStatus(task.status)} • Due ${task.dueDate || "unscheduled"}`;
    detail.textContent = task.detail || "No extra notes yet.";
    priority.textContent = labelForPriority(task.priority);
    priority.classList.add(`pill-${task.priority}`);
    statusSelect.value = task.status;

    statusSelect.addEventListener("change", async () => {
      await api(`/api/tasks/${task.id}`, {
        method: "PATCH",
        body: JSON.stringify({ status: statusSelect.value }),
      });
      await loadDashboard();
    });

    deleteButton.addEventListener("click", async () => {
      await api(`/api/tasks/${task.id}`, { method: "DELETE" });
      await loadDashboard();
    });

    card.dataset.status = task.status;
    taskList.appendChild(fragment);
  });
}

function renderLeads() {
  leadList.innerHTML = "";

  if (appState.leads.length === 0) {
    leadList.appendChild(emptyState("No leads yet. Add one to start tracking pipeline."));
    return;
  }

  appState.leads.forEach((lead) => {
    const fragment = leadTemplate.content.cloneNode(true);
    const title = fragment.querySelector(".item-title");
    const meta = fragment.querySelector(".item-meta");
    const detail = fragment.querySelector(".item-detail");
    const stage = fragment.querySelector(".item-stage");
    const stageSelect = fragment.querySelector(".stage-select");
    const deleteButton = fragment.querySelector(".delete-button");

    title.textContent = lead.name;
    meta.textContent = [lead.company, lead.email].filter(Boolean).join(" • ") || "No contact details";
    detail.textContent = lead.note || "No notes yet.";
    stage.textContent = labelForStage(lead.stage);
    stage.classList.add(`pill-${lead.stage}`);
    stageSelect.value = lead.stage;

    stageSelect.addEventListener("change", async () => {
      await api(`/api/leads/${lead.id}`, {
        method: "PATCH",
        body: JSON.stringify({ stage: stageSelect.value }),
      });
      await loadDashboard();
    });

    deleteButton.addEventListener("click", async () => {
      await api(`/api/leads/${lead.id}`, { method: "DELETE" });
      await loadDashboard();
    });

    leadList.appendChild(fragment);
  });
}

function renderActivity() {
  activityList.innerHTML = "";

  if (appState.activity.length === 0) {
    activityList.appendChild(emptyState("No activity has been recorded yet."));
    return;
  }

  appState.activity.forEach((entry) => {
    const fragment = activityTemplate.content.cloneNode(true);
    fragment.querySelector(".activity-message").textContent = entry.message;
    fragment.querySelector(".activity-time").textContent = formatDateTime(entry.createdAt);
    activityList.appendChild(fragment);
  });
}

taskForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const formData = new FormData(taskForm);
  await api("/api/tasks", {
    method: "POST",
    body: JSON.stringify({
      title: String(formData.get("title") || "").trim(),
      detail: String(formData.get("detail") || "").trim(),
      dueDate: String(formData.get("dueDate") || "").trim(),
      priority: String(formData.get("priority") || "medium"),
      status: "todo",
    }),
  });
  taskForm.reset();
  document.querySelector("#task-priority").value = "medium";
  await loadDashboard();
});

leadForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const formData = new FormData(leadForm);
  await api("/api/leads", {
    method: "POST",
    body: JSON.stringify({
      name: String(formData.get("name") || "").trim(),
      company: String(formData.get("company") || "").trim(),
      email: String(formData.get("email") || "").trim(),
      note: String(formData.get("note") || "").trim(),
      stage: String(formData.get("stage") || "new"),
    }),
  });
  leadForm.reset();
  document.querySelector("#lead-stage").value = "new";
  await loadDashboard();
});

refreshButton.addEventListener("click", loadDashboard);
taskFilter.addEventListener("change", renderTasks);

exportButton.addEventListener("click", async () => {
  const data = await api("/api/export");
  const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = "pulsedesk-export.json";
  anchor.click();
  URL.revokeObjectURL(url);
});

function emptyState(message) {
  const node = document.createElement("div");
  node.className = "empty-state";
  node.textContent = message;
  return node;
}

function labelForPriority(priority) {
  return priority.replace("_", " ");
}

function labelForStatus(status) {
  return status.replace("_", " ");
}

function labelForStage(stage) {
  return stage.replace("_", " ");
}

function formatDateTime(value) {
  if (!value) {
    return "Unknown time";
  }
  return new Date(value).toLocaleString();
}

function formatTime(value) {
  if (!value) {
    return "--:--";
  }
  return new Date(value).toLocaleTimeString();
}

loadDashboard().catch((error) => {
  taskList.appendChild(emptyState(error.message));
});
