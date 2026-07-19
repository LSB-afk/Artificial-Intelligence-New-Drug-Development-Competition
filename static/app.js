"use strict";

const state = {
  snapshot: null,
  activeView: "dashboard",
  loading: false,
};

const viewRoot = document.getElementById("view-root");
const navRoot = document.getElementById("primary-nav");
const pulseRoot = document.getElementById("ops-pulse");
const syncRail = document.getElementById("sync-rail");
const dialog = document.getElementById("action-dialog");
const toast = document.getElementById("toast");

const viewDefinitions = [
  ["dashboard", "대시보드", renderDashboard],
  ["projects", "프로젝트", renderProjects],
  ["tasks", "태스크", renderTasks],
  ["agents", "에이전트", renderAgents],
  ["runs", "실행", renderRuns],
  ["costs", "비용", renderCosts],
  ["approvals", "승인", renderApprovals],
  ["activity", "활동", renderActivity],
];

const views = {
  dashboard: renderDashboard,
  projects: renderProjects,
  tasks: renderTasks,
  agents: renderAgents,
  runs: renderRuns,
  costs: renderCosts,
  approvals: renderApprovals,
  activity: renderActivity,
};

const labels = {
  planned: "계획",
  active: "진행",
  paused: "일시정지",
  completed: "완료",
  cancelled: "취소",
  backlog: "백로그",
  todo: "대기",
  in_progress: "진행 중",
  in_review: "검토",
  blocked: "차단",
  done: "완료",
  low: "낮음",
  medium: "보통",
  high: "높음",
  critical: "긴급",
  idle: "대기",
  running: "실행 중",
  error: "오류",
  terminated: "종료",
  queued: "대기열",
  succeeded: "성공",
  failed: "실패",
  pending: "대기",
  approved: "승인",
  rejected: "반려",
  revision_requested: "수정 요청",
};

function escapeHtml(value) {
  return String(value ?? "").replace(/[&<>"']/g, (char) => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    "\"": "&quot;",
    "'": "&#39;",
  })[char]);
}

function htmlDate(value) {
  return value ? escapeHtml(value) : "미정";
}

function money(cents) {
  return `$${(Number(cents || 0) / 100).toFixed(2)}`;
}

function number(value) {
  return new Intl.NumberFormat("ko-KR").format(Number(value || 0));
}

function byId(kind, id) {
  const items = state.snapshot?.[kind] || [];
  return items.find((item) => item.id === id);
}

function nameFor(kind, id, fallback = "미지정") {
  if (!id) return fallback;
  const item = byId(kind, id);
  return escapeHtml(item?.name || item?.title || id);
}

function statusLabel(value) {
  return escapeHtml(labels[value] || value || "없음");
}

function statusClass(value) {
  if (["failed", "blocked", "error", "rejected", "terminated", "cancelled"].includes(value)) return "danger";
  if (["pending", "queued", "paused", "in_review", "critical"].includes(value)) return "warning";
  if (["running", "in_progress"].includes(value)) return "running";
  if (["active", "idle", "succeeded", "approved", "done", "completed"].includes(value)) return "approved";
  return "";
}

function utilizationClass(percent) {
  if (percent >= 100) return "danger";
  if (percent >= 80) return "warning";
  return "approved";
}

async function loadConsole({ focus = false } = {}) {
  state.loading = true;
  try {
    const response = await fetch("/api/console", {
      headers: { "Content-Type": "application/json" },
    });
    const payload = await response.json();
    if (!response.ok) throw structuredError(payload);
    state.snapshot = payload;
    renderAll();
    if (focus) viewRoot.focus();
  } catch (error) {
    renderError(error);
    showToast(error.message || "콘솔 스냅샷을 불러오지 못했습니다.", "error");
  } finally {
    state.loading = false;
  }
}

async function api(path, options = {}) {
  const response = await fetch(path, {
    ...options,
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
  });
  const payload = await response.json();
  if (!response.ok) throw structuredError(payload);
  return payload;
}

function structuredError(payload) {
  const error = new Error(payload?.message || payload?.error || "요청에 실패했습니다.");
  error.payload = payload || {};
  return error;
}

function renderAll() {
  renderNav();
  renderSyncRail();
  renderPulse();
  renderActiveView();
}

function renderNav() {
  navRoot.innerHTML = viewDefinitions.map(([key, label]) => (
    `<button class="nav-tab${state.activeView === key ? " active" : ""}" type="button" data-view="${escapeHtml(key)}" aria-current="${state.activeView === key ? "page" : "false"}">${escapeHtml(label)}</button>`
  )).join("");
}

function renderSyncRail() {
  const snapshot = state.snapshot;
  const overview = snapshot?.overview || {};
  syncRail.innerHTML = [
    `<div class="sync-title"><span class="sync-label">CONSOLE</span><strong><span class="dot ok" aria-hidden="true"></span>H2L-Forge 동기화</strong></div>`,
    metric("PROJECTS", overview.project_count),
    metric("TASKS", overview.task_count),
    metric("AGENTS", overview.active_agent_count),
    metric("APPROVALS", overview.pending_approval_count),
  ].join("");
}

function metric(label, value) {
  return `<div class="sync-metric"><span>${escapeHtml(label)}</span><strong>${number(value)}</strong></div>`;
}

function renderPulse() {
  const s = state.snapshot;
  if (!s) return;
  const costs = s.costs?.utilization || {};
  const costPct = Number(costs.utilization_pct || 0);
  const steps = [
    ["projects", s.projects.length, "작업 경계", s.projects.some((p) => p.status === "paused") ? "warning" : "approved"],
    ["tasks", s.tasks.length, `${s.tasks.filter((t) => ["blocked", "in_review"].includes(t.status)).length}개 주의`, s.tasks.some((t) => t.status === "blocked") ? "danger" : "approved"],
    ["agents", s.agents.length, `${s.agents.filter((a) => a.status === "running").length} 실행`, s.agents.some((a) => ["error", "paused"].includes(a.status)) ? "warning" : "approved"],
    ["runs", s.runs.length, `${s.runs.filter((r) => ["failed", "cancelled"].includes(r.status)).length} 재시도 가능`, s.runs.some((r) => r.status === "failed") ? "danger" : "running"],
    ["costs", money(s.costs?.total_cost_cents), `${costPct}% 예산`, utilizationClass(costPct)],
    ["approvals", s.approvals.length, `${s.approvals.filter((a) => a.status === "pending").length} 대기`, s.approvals.some((a) => a.status === "pending") ? "warning" : "approved"],
  ];
  pulseRoot.innerHTML = steps.map(([label, count, note, kind]) => `
    <button class="pulse-step ${escapeHtml(kind)}" type="button" data-view="${escapeHtml(label)}">
      <span>${escapeHtml(label)}</span>
      <strong>${escapeHtml(count)}</strong>
      <em>${escapeHtml(note)}</em>
    </button>
  `).join("");
}

function renderActiveView() {
  const renderer = views[state.activeView] || views.dashboard;
  viewRoot.innerHTML = state.snapshot ? renderer() : loadingView();
}

function loadingView() {
  return `<section class="empty-state" role="status">콘솔 스냅샷을 불러오는 중입니다.</section>`;
}

function renderError(error) {
  viewRoot.innerHTML = `
    <section class="empty-state error-state" role="alert">
      <strong>콘솔을 표시할 수 없습니다.</strong>
      <span>${escapeHtml(error.message)}</span>
    </section>
  `;
}

function viewHeader(kicker, title, summary, actionHtml = "") {
  return `
    <div class="view-heading">
      <div>
        <p class="kicker">${escapeHtml(kicker)}</p>
        <h2>${escapeHtml(title)}</h2>
        <p class="view-summary">${escapeHtml(summary)}</p>
      </div>
      <div class="view-actions">${actionHtml}</div>
    </div>
  `;
}

function renderDashboard() {
  const s = state.snapshot;
  const attention = [
    ...s.tasks.filter((task) => ["blocked", "in_review"].includes(task.status)).map((task) => ({
      type: "태스크",
      title: task.title,
      status: task.status,
      detail: `${nameFor("projects", task.project_id)} / ${task.priority}`,
      action: `<button class="secondary-button fit-button" type="button" data-view="tasks">열기</button>`,
    })),
    ...s.approvals.filter((approval) => approval.status === "pending").map((approval) => ({
      type: "승인",
      title: approval.title,
      status: approval.status,
      detail: approval.type,
      action: `<button class="secondary-button fit-button" type="button" data-view="approvals">검토</button>`,
    })),
    ...s.agents.filter((agent) => ["error", "paused"].includes(agent.status)).map((agent) => ({
      type: "에이전트",
      title: agent.name,
      status: agent.status,
      detail: escapeHtml(agent.pause_reason || agent.role),
      action: `<button class="secondary-button fit-button" type="button" data-view="agents">확인</button>`,
    })),
  ].slice(0, 8);
  const activeRuns = s.runs.filter((run) => ["queued", "running"].includes(run.status)).slice(0, 5);
  const recentRuns = s.runs.slice().reverse().slice(0, 5);
  const pendingApprovals = s.approvals.filter((approval) => approval.status === "pending").slice(0, 5);
  const activity = s.activity.slice().reverse().slice(0, 6);
  return `
    <section class="view-section">
      ${viewHeader("dashboard", "운영 대시보드", "프로젝트에서 승인까지 이어지는 데모 운영 상태를 압축해 보여줍니다.", `<button class="primary-button fit-button" type="button" data-action="create-task">태스크 생성</button>`)}
      <div class="dashboard-grid">
        ${panel("주의 큐", renderAttention(attention))}
        ${panel("실행 중 / 대기 실행", activeRuns.length ? compactRuns(activeRuns) : empty("현재 실행 중인 run이 없습니다."))}
        ${panel("최근 실행", recentRuns.length ? compactRuns(recentRuns) : empty("실행 기록이 없습니다."))}
        ${panel("대기 승인", pendingApprovals.length ? compactApprovals(pendingApprovals) : empty("대기 승인이 없습니다."))}
        ${panel("최근 활동", activity.length ? compactActivity(activity) : empty("활동 기록이 없습니다."), "wide-panel")}
      </div>
    </section>
  `;
}

function panel(title, body, extraClass = "") {
  return `<article class="ops-panel ${extraClass}"><h3>${escapeHtml(title)}</h3>${body}</article>`;
}

function renderAttention(items) {
  if (!items.length) return empty("주의가 필요한 항목이 없습니다.");
  return `<div class="attention-list">${items.map((item) => `
    <div class="attention-row">
      <div>
        <span class="table-kicker">${escapeHtml(item.type)}</span>
        <strong>${escapeHtml(item.title)}</strong>
        <small>${item.detail}</small>
      </div>
      <span class="status-pill ${statusClass(item.status)}">${statusLabel(item.status)}</span>
      ${item.action}
    </div>
  `).join("")}</div>`;
}

function renderProjects() {
  const rows = state.snapshot.projects.map((project) => [
    escapeHtml(project.name),
    statusPill(project.status),
    escapeHtml(project.goal),
    nameFor("agents", project.lead_agent_id),
    htmlDate(project.target_date),
    rowActions([
      actionButton("edit-project", project.id, "수정", "secondary"),
      project.status === "active" ? actionButton("project-status", project.id, "일시정지", "ghost", "paused") : "",
      project.status === "paused" ? actionButton("project-status", project.id, "재개", "secondary", "active") : "",
      !["completed", "cancelled"].includes(project.status) ? actionButton("project-status", project.id, "완료", "ghost", "completed") : "",
    ]),
  ]);
  return `
    <section class="view-section">
      ${viewHeader("projects", "프로젝트", "저장소 운영 경계, 목표, 리드 에이전트, 상태를 관리합니다.", `<button class="primary-button fit-button" type="button" data-action="create-project">프로젝트 생성</button>`)}
      ${table(["이름", "상태", "목표", "리드", "목표일", "작업"], rows)}
    </section>
  `;
}

function renderTasks() {
  const rows = state.snapshot.tasks.map((task) => [
    `<strong>${escapeHtml(task.title)}</strong><small>${escapeHtml(task.description || "설명 없음")}</small>`,
    nameFor("projects", task.project_id),
    statusPill(task.status),
    statusPill(task.priority),
    nameFor("agents", task.assignee_agent_id),
    rowActions(taskActions(task)),
  ]);
  return `
    <section class="view-section">
      ${viewHeader("tasks", "태스크", "생성, 수정, 체크아웃, 릴리스, 라이프사이클 전환을 수행합니다.", `<button class="primary-button fit-button" type="button" data-action="create-task">태스크 생성</button>`)}
      ${table(["태스크", "프로젝트", "상태", "우선순위", "담당", "작업"], rows)}
    </section>
  `;
}

function taskActions(task) {
  const actions = [actionButton("edit-task", task.id, "수정", "secondary")];
  if (task.status === "todo") actions.push(actionButton("checkout-task", task.id, "체크아웃", "primary"));
  if (task.status === "in_progress") {
    actions.push(actionButton("task-status", task.id, "검토", "secondary", "in_review"));
    actions.push(actionButton("task-status", task.id, "차단", "danger", "blocked"));
    actions.push(actionButton("release-task", task.id, "릴리스", "ghost"));
  }
  if (task.status === "blocked") actions.push(actionButton("task-status", task.id, "재개", "secondary", "in_progress"));
  if (task.status === "in_review") {
    actions.push(actionButton("task-status", task.id, "수정", "ghost", "in_progress"));
    actions.push(actionButton("task-status", task.id, "완료", "secondary", "done"));
  }
  if (task.status === "backlog") actions.push(actionButton("task-status", task.id, "대기 전환", "secondary", "todo"));
  return actions;
}

function renderAgents() {
  const rows = state.snapshot.agents.map((agent) => {
    const pct = agent.budget_monthly_cents ? Math.round((agent.spent_monthly_cents / agent.budget_monthly_cents) * 100) : 0;
    return [
      `<strong>${escapeHtml(agent.name)}</strong><small>${escapeHtml(agent.title || agent.role)}</small>`,
      statusPill(agent.status),
      escapeHtml(agent.role),
      escapeHtml((agent.capabilities || []).join(", ")),
      `<span class="budget ${utilizationClass(pct)}"><strong>${money(agent.spent_monthly_cents)} / ${money(agent.budget_monthly_cents)}</strong><small>${pct}% 사용</small></span>`,
      rowActions([
        agent.status === "paused" ? actionButton("resume-agent", agent.id, "재개", "secondary") : actionButton("pause-agent", agent.id, "일시정지", "danger"),
      ]),
    ];
  });
  return `
    <section class="view-section">
      ${viewHeader("agents", "에이전트", "역할, 상태, 하트비트, 예산 사용률을 확인하고 일시정지/재개합니다.")}
      ${table(["이름", "상태", "역할", "역량", "월 예산", "작업"], rows)}
    </section>
  `;
}

function renderRuns() {
  const rows = state.snapshot.runs.slice().reverse().map((run) => [
    `<strong>${escapeHtml(run.id)}</strong><small>${escapeHtml(run.invocation_source || "source 없음")}</small>`,
    nameFor("tasks", run.task_id),
    nameFor("agents", run.agent_id),
    statusPill(run.status),
    `${number(run.usage?.input_tokens)} / ${number(run.usage?.output_tokens)} tokens`,
    `${money(run.cost_cents)}<small>${escapeHtml(run.error || run.result || run.next_action || "이벤트 없음")}</small>`,
    rowActions(["failed", "cancelled"].includes(run.status) ? [actionButton("retry-run", run.id, "재시도", "secondary")] : [disabledButton("재시도 불가", "failed/cancelled 상태만 가능")]),
  ]);
  return `
    <section class="view-section">
      ${viewHeader("runs", "실행 기록", "결과, 오류, 다음 조치, 토큰/비용을 간결한 실행 이벤트로 표시합니다.")}
      ${table(["Run", "태스크", "에이전트", "상태", "토큰", "비용/이벤트", "작업"], rows)}
    </section>
  `;
}

function renderCosts() {
  const costs = state.snapshot.costs || {};
  const utilization = costs.utilization || {};
  const agentRows = Object.entries(costs.by_agent || {}).map(([id, bucket]) => {
    const agent = byId("agents", id);
    const pct = agent?.budget_monthly_cents ? Math.round((agent.spent_monthly_cents / agent.budget_monthly_cents) * 100) : 0;
    return [nameFor("agents", id), number(bucket.total_tokens), money(bucket.cost_cents), statusPill(`${pct}%`, utilizationClass(pct))];
  });
  const projectRows = Object.entries(costs.by_project || {}).map(([id, bucket]) => [
    nameFor("projects", id),
    number(bucket.total_tokens),
    money(bucket.cost_cents),
    number(bucket.event_count),
  ]);
  const eventRows = (state.snapshot.cost_events || []).slice().reverse().map((event) => [
    htmlDate(event.occurred_at),
    nameFor("agents", event.agent_id),
    nameFor("projects", event.project_id),
    escapeHtml(event.model),
    number(Number(event.input_tokens || 0) + Number(event.cached_input_tokens || 0) + Number(event.output_tokens || 0)),
    money(event.cost_cents),
  ]);
  return `
    <section class="view-section">
      ${viewHeader("costs", "비용", `총 ${money(costs.total_cost_cents)} / ${number(costs.total_tokens)} tokens / 월 예산 ${utilization.utilization_pct || 0}% 사용`)}
      <div class="dashboard-grid">
        ${panel("에이전트별 사용률", table(["에이전트", "토큰", "비용", "위험"], agentRows))}
        ${panel("프로젝트별 비용", table(["프로젝트", "토큰", "비용", "이벤트"], projectRows))}
        ${panel("비용 이벤트 원장", table(["시각", "에이전트", "프로젝트", "모델", "토큰", "비용"], eventRows), "wide-panel")}
      </div>
    </section>
  `;
}

function renderApprovals() {
  const rows = state.snapshot.approvals.map((approval) => [
    `<strong>${escapeHtml(approval.title)}</strong><small>${escapeHtml(approval.type)}</small>`,
    statusPill(approval.status),
    nameFor("agents", approval.requested_by, approval.requested_by || "요청자 없음"),
    escapeHtml(JSON.stringify(approval.payload || {})),
    escapeHtml(approval.decision_note || "결정 메모 없음"),
    rowActions(approval.status === "pending" ? [
      actionButton("decide-approval", approval.id, "승인", "primary", "approve"),
      actionButton("decide-approval", approval.id, "반려", "danger", "reject"),
      actionButton("decide-approval", approval.id, "수정 요청", "danger", "request-revision"),
    ] : [disabledButton("종결", "pending 상태만 결정 가능")]),
  ]);
  return `
    <section class="view-section">
      ${viewHeader("approvals", "승인", "운영 범위, 예산, 배포 같은 고위험 작업은 결정 메모와 함께 종결합니다.")}
      ${table(["승인", "상태", "요청자", "페이로드", "결정 메모", "작업"], rows)}
    </section>
  `;
}

function renderActivity() {
  const rows = state.snapshot.activity.slice().reverse().map((event) => [
    htmlDate(event.created_at),
    escapeHtml(event.action),
    `${escapeHtml(event.entity_type)} / ${escapeHtml(event.entity_id)}`,
    escapeHtml(event.actor_id),
    escapeHtml(JSON.stringify(event.details || {})),
  ]);
  return `
    <section class="view-section">
      ${viewHeader("activity", "활동 로그", "프로젝트, 태스크, 에이전트, 승인, 실행 변경이 append-only 이벤트로 남습니다.")}
      ${table(["시각", "동작", "대상", "행위자", "상세"], rows)}
    </section>
  `;
}

function compactRuns(runs) {
  return `<div class="compact-list">${runs.map((run) => `
    <div class="compact-row">
      <strong>${escapeHtml(run.id)}</strong>
      <span>${nameFor("tasks", run.task_id)} / ${nameFor("agents", run.agent_id)}</span>
      ${statusPill(run.status)}
    </div>
  `).join("")}</div>`;
}

function compactApprovals(items) {
  return `<div class="compact-list">${items.map((approval) => `
    <div class="compact-row">
      <strong>${escapeHtml(approval.title)}</strong>
      <span>${escapeHtml(approval.type)}</span>
      ${statusPill(approval.status)}
    </div>
  `).join("")}</div>`;
}

function compactActivity(items) {
  return `<div class="compact-list">${items.map((event) => `
    <div class="compact-row">
      <strong>${escapeHtml(event.action)}</strong>
      <span>${escapeHtml(event.entity_type)} / ${escapeHtml(event.entity_id)} / ${htmlDate(event.created_at)}</span>
    </div>
  `).join("")}</div>`;
}

function table(headers, rows) {
  if (!rows.length) return empty("표시할 데이터가 없습니다.");
  return `
    <div class="table-wrap">
      <table class="data-table">
        <thead><tr>${headers.map((header) => `<th scope="col">${escapeHtml(header)}</th>`).join("")}</tr></thead>
        <tbody>${rows.map((cells) => `
          <tr>${cells.map((cell, index) => `<td data-label="${escapeHtml(headers[index])}">${cell}</td>`).join("")}</tr>
        `).join("")}</tbody>
      </table>
    </div>
  `;
}

function empty(message) {
  return `<div class="empty-state">${escapeHtml(message)}</div>`;
}

function statusPill(value, forcedClass) {
  const cls = forcedClass || statusClass(value);
  return `<span class="status-pill ${escapeHtml(cls)}">${statusLabel(value)}</span>`;
}

function rowActions(actions) {
  return `<div class="row-actions">${actions.filter(Boolean).join("")}</div>`;
}

function actionButton(action, id, label, tone = "secondary", value = "") {
  const className = tone === "primary" ? "primary-button" : tone === "danger" ? "danger-button" : tone === "ghost" ? "ghost-button" : "secondary-button";
  return `<button class="${className} fit-button" type="button" data-action="${escapeHtml(action)}" data-id="${escapeHtml(id)}" data-value="${escapeHtml(value)}">${escapeHtml(label)}</button>`;
}

function disabledButton(label, reason) {
  return `<button class="ghost-button fit-button" type="button" disabled aria-disabled="true" title="${escapeHtml(reason)}">${escapeHtml(label)}</button>`;
}

function formValue(form, name) {
  return form.elements[name]?.value?.trim() || "";
}

function selectOptions(items, selectedId, emptyLabel = "미지정") {
  return `<option value="">${escapeHtml(emptyLabel)}</option>${items.map((item) => `
    <option value="${escapeHtml(item.id)}"${item.id === selectedId ? " selected" : ""}>${escapeHtml(item.name || item.title || item.id)}</option>
  `).join("")}`;
}

function openDialog({ title, description, body, submitLabel = "저장", danger = false, onSubmit }) {
  dialog.innerHTML = `
    <form method="dialog" class="action-form">
      <header class="dialog-header">
        <div>
          <h2 id="dialog-title">${escapeHtml(title)}</h2>
          <p id="dialog-description">${escapeHtml(description)}</p>
        </div>
        <button class="ghost-button fit-button" type="button" data-action="close-dialog" aria-label="닫기">닫기</button>
      </header>
      <div class="dialog-error" role="alert" hidden></div>
      <div class="dialog-body">${body}</div>
      <footer class="dialog-actions">
        <button class="ghost-button fit-button" value="cancel" type="button" data-action="close-dialog">취소</button>
        <button class="${danger ? "danger-button" : "primary-button"} fit-button" value="default" type="submit">${escapeHtml(submitLabel)}</button>
      </footer>
    </form>
  `;
  const form = dialog.querySelector("form");
  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    await submitDialog(form, onSubmit);
  });
  dialog.showModal();
  form.querySelector("input, select, textarea, button")?.focus();
}

async function submitDialog(form, onSubmit) {
  const errorBox = dialog.querySelector(".dialog-error");
  errorBox.hidden = true;
  errorBox.textContent = "";
  try {
    await onSubmit(form);
    dialog.close();
    showToast("작업이 저장되었습니다.");
    await loadConsole({ focus: true });
  } catch (error) {
    const detail = error.payload?.error ? `${error.payload.error}: ${error.message}` : error.message;
    errorBox.textContent = detail;
    errorBox.hidden = false;
    showToast(detail, "error");
  }
}

function projectForm(project = {}) {
  return `
    <label class="field-label">이름<input name="name" required value="${escapeHtml(project.name)}"></label>
    <label class="field-label">설명<textarea name="description">${escapeHtml(project.description)}</textarea></label>
    <label class="field-label">목표<textarea name="goal">${escapeHtml(project.goal)}</textarea></label>
    <label class="field-label">상태<select name="status">${["planned", "active", "paused", "completed", "cancelled"].map((s) => `<option value="${s}"${project.status === s ? " selected" : ""}>${statusLabel(s)}</option>`).join("")}</select></label>
    <label class="field-label">목표일<input name="target_date" type="date" value="${escapeHtml(project.target_date)}"></label>
    <label class="field-label">리드 에이전트<select name="lead_agent_id">${selectOptions(state.snapshot.agents, project.lead_agent_id)}</select></label>
  `;
}

function taskForm(task = {}) {
  return `
    <label class="field-label">제목<input name="title" required value="${escapeHtml(task.title)}"></label>
    <label class="field-label">설명<textarea name="description">${escapeHtml(task.description)}</textarea></label>
    <label class="field-label">프로젝트<select name="project_id" required>${selectOptions(state.snapshot.projects, task.project_id, "프로젝트 선택")}</select></label>
    <label class="field-label">상태<select name="status">${["backlog", "todo", "in_progress", "in_review", "blocked", "done"].map((s) => `<option value="${s}"${task.status === s ? " selected" : ""}>${statusLabel(s)}</option>`).join("")}</select></label>
    <label class="field-label">우선순위<select name="priority">${["low", "medium", "high", "critical"].map((s) => `<option value="${s}"${(task.priority || "medium") === s ? " selected" : ""}>${statusLabel(s)}</option>`).join("")}</select></label>
    <label class="field-label">담당 에이전트<select name="assignee_agent_id">${selectOptions(state.snapshot.agents, task.assignee_agent_id)}</select></label>
    <label class="field-label">라벨<input name="labels" value="${escapeHtml((task.labels || []).join(", "))}" placeholder="demo, repository"></label>
  `;
}

function noteForm(label = "결정 메모", extra = "") {
  return `${extra}<label class="field-label">${escapeHtml(label)}<textarea name="note" required></textarea></label>`;
}

function checkoutForm(task) {
  return `
    <p class="dialog-context">태스크: ${escapeHtml(task.title)}</p>
    <label class="field-label">담당 에이전트<select name="agent_id" required>${selectOptions(state.snapshot.agents, task.assignee_agent_id, "에이전트 선택")}</select></label>
    <label class="field-label">Run ID<input name="run_id" required value="run-${escapeHtml(Date.now())}"></label>
  `;
}

async function mutate(path, method = "POST", payload = {}) {
  await api(path, {
    method,
    body: JSON.stringify({ actor: "console-operator", ...payload }),
  });
  showToast("작업이 완료되었습니다.");
  await loadConsole({ focus: true });
}

function showToast(message, kind = "ok") {
  toast.textContent = message;
  toast.dataset.kind = kind;
  toast.classList.add("visible");
  window.clearTimeout(showToast.timer);
  showToast.timer = window.setTimeout(() => toast.classList.remove("visible"), 3600);
}

function openCreateProject() {
  openDialog({
    title: "프로젝트 생성",
    description: "데모 운영 저장소에 새 프로젝트 경계를 추가합니다.",
    body: projectForm({ status: "planned" }),
    onSubmit: (form) => mutate("/api/projects", "POST", projectPayload(form)),
  });
}

function openEditProject(id) {
  const project = byId("projects", id);
  openDialog({
    title: "프로젝트 수정",
    description: "프로젝트 목표, 상태, 리드를 갱신합니다.",
    body: projectForm(project),
    onSubmit: (form) => mutate(`/api/projects/${id}`, "PATCH", projectPayload(form)),
  });
}

function projectPayload(form) {
  return {
    name: formValue(form, "name"),
    description: formValue(form, "description"),
    goal: formValue(form, "goal"),
    status: formValue(form, "status"),
    target_date: formValue(form, "target_date") || null,
    lead_agent_id: formValue(form, "lead_agent_id") || null,
  };
}

function openCreateTask() {
  openDialog({
    title: "태스크 생성",
    description: "프로젝트에 연결된 새 운영 태스크를 만듭니다.",
    body: taskForm({ status: "backlog", priority: "medium" }),
    onSubmit: (form) => mutate("/api/tasks", "POST", taskPayload(form, false)),
  });
}

function openEditTask(id) {
  const task = byId("tasks", id);
  openDialog({
    title: "태스크 수정",
    description: "허용된 라이프사이클과 담당 정보를 갱신합니다.",
    body: taskForm(task),
    onSubmit: (form) => mutate(`/api/tasks/${id}`, "PATCH", taskPayload(form, true)),
  });
}

function taskPayload(form, includeAssignee) {
  const payload = {
    project_id: formValue(form, "project_id"),
    title: formValue(form, "title"),
    description: formValue(form, "description"),
    status: formValue(form, "status"),
    priority: formValue(form, "priority"),
    labels: formValue(form, "labels").split(",").map((label) => label.trim()).filter(Boolean),
  };
  if (includeAssignee || formValue(form, "assignee_agent_id")) {
    payload.assignee_agent_id = formValue(form, "assignee_agent_id") || null;
  }
  return payload;
}

function openCheckoutTask(id) {
  const task = byId("tasks", id);
  openDialog({
    title: "태스크 체크아웃",
    description: "대기 상태 태스크를 원자적으로 담당 에이전트에게 할당하고 running run을 생성합니다.",
    body: checkoutForm(task),
    onSubmit: (form) => mutate(`/api/tasks/${id}/checkout`, "POST", {
      agent_id: formValue(form, "agent_id"),
      expected_statuses: [task.status],
      run_id: formValue(form, "run_id"),
    }),
  });
}

function openPauseAgent(id) {
  const agent = byId("agents", id);
  openDialog({
    title: "에이전트 일시정지",
    description: `${agent.name} 에이전트의 새 작업 배정을 중단합니다.`,
    body: noteForm("일시정지 사유"),
    submitLabel: "일시정지",
    danger: true,
    onSubmit: (form) => mutate(`/api/agents/${id}/pause`, "POST", { reason: formValue(form, "note") }),
  });
}

function openApprovalDecision(id, decision) {
  const approval = byId("approvals", id);
  openDialog({
    title: `승인 ${statusLabel(decision)}`,
    description: approval.title,
    body: noteForm("결정 메모", `<p class="dialog-context">${escapeHtml(JSON.stringify(approval.payload || {}))}</p>`),
    submitLabel: statusLabel(decision),
    danger: decision !== "approve",
    onSubmit: (form) => mutate(`/api/approvals/${id}/${decision}`, "POST", { note: formValue(form, "note") }),
  });
}

async function handleClick(event) {
  const viewButton = event.target.closest("[data-view]");
  if (viewButton) {
    state.activeView = viewButton.dataset.view;
    renderAll();
    viewRoot.focus();
    return;
  }

  const button = event.target.closest("[data-action]");
  if (!button) return;
  const { action, id, value } = button.dataset;
  try {
    if (action === "close-dialog") dialog.close();
    if (action === "reload") await loadConsole({ focus: true });
    if (action === "create-project") openCreateProject();
    if (action === "edit-project") openEditProject(id);
    if (action === "project-status") await mutate(`/api/projects/${id}`, "PATCH", { status: value });
    if (action === "create-task") openCreateTask();
    if (action === "edit-task") openEditTask(id);
    if (action === "task-status") await mutate(`/api/tasks/${id}`, "PATCH", { status: value });
    if (action === "checkout-task") openCheckoutTask(id);
    if (action === "release-task") await mutate(`/api/tasks/${id}/release`, "POST");
    if (action === "pause-agent") openPauseAgent(id);
    if (action === "resume-agent") await mutate(`/api/agents/${id}/resume`, "POST");
    if (action === "retry-run") await mutate(`/api/runs/${id}/retry`, "POST");
    if (action === "decide-approval") openApprovalDecision(id, value);
  } catch (error) {
    showToast(error.message || "작업에 실패했습니다.", "error");
  }
}

document.addEventListener("click", handleClick);
dialog.addEventListener("cancel", () => showToast("작업을 취소했습니다."));

loadConsole();
