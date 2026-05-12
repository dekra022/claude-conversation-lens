const state = {
  config: null,
  sessions: [],
  selectedId: null,
  current: null,
  nextOffset: null,
  lastQuery: "",
  loading: false,
};

const els = {
  dataDir: document.querySelector("#dataDir"),
  sessionSearch: document.querySelector("#sessionSearch"),
  sessionList: document.querySelector("#sessionList"),
  sessionRange: document.querySelector("#sessionRange"),
  sessionTitle: document.querySelector("#sessionTitle"),
  metricsStrip: document.querySelector("#metricsStrip"),
  queryInput: document.querySelector("#queryInput"),
  roleFilter: document.querySelector("#roleFilter"),
  startInput: document.querySelector("#startInput"),
  endInput: document.querySelector("#endInput"),
  includeTools: document.querySelector("#includeTools"),
  includeSystem: document.querySelector("#includeSystem"),
  includeMeta: document.querySelector("#includeMeta"),
  matchedCount: document.querySelector("#matchedCount"),
  roleChart: document.querySelector("#roleChart"),
  chapterList: document.querySelector("#chapterList"),
  fileList: document.querySelector("#fileList"),
  timeline: document.querySelector("#timeline"),
  loadMoreBtn: document.querySelector("#loadMoreBtn"),
  refreshBtn: document.querySelector("#refreshBtn"),
  exportMdBtn: document.querySelector("#exportMdBtn"),
  exportHtmlBtn: document.querySelector("#exportHtmlBtn"),
  exportJsonBtn: document.querySelector("#exportJsonBtn"),
  eventTemplate: document.querySelector("#eventTemplate"),
};

const roleLabels = {
  user: "用户",
  assistant: "助手",
  tool: "工具",
  system: "系统",
  unknown: "未知",
};

const roleColors = {
  user: "#167c80",
  assistant: "#376cbd",
  tool: "#9d5a2e",
  system: "#647181",
  unknown: "#8a6b9a",
};

function formatNumber(value) {
  const number = Number(value || 0);
  if (number >= 1_000_000) return `${(number / 1_000_000).toFixed(1)}M`;
  if (number >= 1_000) return `${(number / 1_000).toFixed(1)}K`;
  return String(number);
}

function formatBytes(bytes) {
  const units = ["B", "KB", "MB", "GB"];
  let value = Number(bytes || 0);
  let unit = 0;
  while (value >= 1024 && unit < units.length - 1) {
    value /= 1024;
    unit += 1;
  }
  return `${value.toFixed(unit === 0 ? 0 : 1)} ${units[unit]}`;
}

function debounce(fn, wait = 250) {
  let timer = null;
  return (...args) => {
    window.clearTimeout(timer);
    timer = window.setTimeout(() => fn(...args), wait);
  };
}

async function getJson(url) {
  const response = await fetch(url);
  const payload = await response.json();
  if (!response.ok) {
    throw new Error(payload.error || response.statusText);
  }
  return payload;
}

function toast(message) {
  const node = document.createElement("div");
  node.className = "toast";
  node.textContent = message;
  document.body.appendChild(node);
  window.setTimeout(() => node.remove(), 1800);
}

function currentParams(offset = 0) {
  const params = new URLSearchParams();
  params.set("id", state.selectedId || "");
  params.set("q", els.queryInput.value.trim());
  params.set("role", els.roleFilter.value);
  params.set("start", els.startInput.value);
  params.set("end", els.endInput.value);
  params.set("includeTools", els.includeTools.checked ? "1" : "0");
  params.set("includeSystem", els.includeSystem.checked ? "1" : "0");
  params.set("includeMeta", els.includeMeta.checked ? "1" : "0");
  params.set("offset", String(offset));
  params.set("limit", "120");
  return params;
}

function renderSessions() {
  const query = els.sessionSearch.value.trim().toLowerCase();
  els.sessionList.innerHTML = "";
  const filtered = state.sessions.filter((session) => {
    const haystack = [
      session.id,
      session.firstTimestamp,
      session.lastTimestamp,
      Object.keys(session.models || {}).join(" "),
      session.topCwd,
    ].join(" ").toLowerCase();
    return !query || haystack.includes(query);
  });

  if (!filtered.length) {
    els.sessionList.innerHTML = `<div class="empty-copy"><strong>没有会话</strong><span>没有找到匹配的 JSONL 文件。</span></div>`;
    return;
  }

  for (const session of filtered) {
    const button = document.createElement("button");
    button.className = `session-card${session.id === state.selectedId ? " active" : ""}`;
    button.type = "button";
    button.innerHTML = `
      <span class="session-name">${escapeHtml(session.displayTitle || session.name)}</span>
      <span class="session-id">${escapeHtml(session.id)}</span>
      <span class="session-meta">
        <span>${escapeHtml(session.firstTimestamp || "无时间")}</span>
        <span>${formatBytes(session.size)}</span>
      </span>
      <span class="session-meta">
        <span>${formatNumber(session.eventCount)} 条事件</span>
        <span>${formatNumber(session.toolCalls)} 次工具</span>
      </span>
    `;
    button.addEventListener("click", () => selectSession(session.id));
    els.sessionList.appendChild(button);
  }
}

function setMetrics(summary) {
  const tokenTotal = Object.values(summary.tokenUsage || {}).reduce((acc, value) => acc + Number(value || 0), 0);
  const values = [
    ["事件", summary.eventCount],
    ["工具调用", summary.toolCalls],
    ["代码块", summary.codeBlocks],
    ["Tokens", tokenTotal],
  ];
  els.metricsStrip.innerHTML = values
    .map(([label, value]) => `<div><span>${label}</span><strong>${formatNumber(value)}</strong></div>`)
    .join("");
}

function drawRoleChart(summary) {
  const canvas = els.roleChart;
  const dpr = window.devicePixelRatio || 1;
  const rect = canvas.getBoundingClientRect();
  canvas.width = Math.max(1, Math.floor(rect.width * dpr));
  canvas.height = Math.max(1, Math.floor(rect.height * dpr));
  const ctx = canvas.getContext("2d");
  ctx.scale(dpr, dpr);
  ctx.clearRect(0, 0, rect.width, rect.height);

  const roles = Object.entries(summary.roles || {}).filter(([, count]) => count > 0);
  const total = roles.reduce((acc, [, count]) => acc + count, 0);
  if (!total) return;

  let x = 18;
  const y = 26;
  const height = 34;
  const width = rect.width - 36;
  for (const [role, count] of roles) {
    const segment = Math.max(3, (count / total) * width);
    ctx.fillStyle = roleColors[role] || roleColors.unknown;
    ctx.fillRect(x, y, segment, height);
    x += segment;
  }

  let legendX = 18;
  ctx.font = "12px system-ui, sans-serif";
  ctx.textBaseline = "middle";
  for (const [role, count] of roles) {
    ctx.fillStyle = roleColors[role] || roleColors.unknown;
    ctx.fillRect(legendX, 80, 10, 10);
    ctx.fillStyle = "#44505d";
    const label = `${roleLabels[role] || role}: ${count}`;
    ctx.fillText(label, legendX + 15, 85);
    legendX += ctx.measureText(label).width + 38;
  }
}

function renderChapters(summary) {
  const chapters = summary.chapters || [];
  if (!chapters.length) {
    els.chapterList.innerHTML = `<div class="chapter-item"><strong>没有检测到用户轮次</strong><span>可以打开元数据，或选择其他会话。</span></div>`;
    return;
  }
  els.chapterList.innerHTML = chapters
    .map((chapter) => `
      <div class="chapter-item" data-line="${chapter.line}">
        <strong>${escapeHtml(chapter.title)}</strong>
        <span>${escapeHtml(chapter.time || "")} · line ${chapter.line}</span>
      </div>
    `)
    .join("");
}

function renderFiles(summary) {
  const files = summary.topFiles || [];
  if (!files.length) {
    els.fileList.innerHTML = `<div class="file-item"><code>暂无引用路径</code><span>0</span></div>`;
    return;
  }
  els.fileList.innerHTML = files
    .map((item) => `<div class="file-item"><code>${escapeHtml(item.path)}</code><span>${item.count}</span></div>`)
    .join("");
}

function updateSummary(data) {
  const summary = data.summary;
  state.current = data;
  els.sessionTitle.textContent = summary.displayTitle || summary.name;
  els.sessionRange.textContent = `${summary.firstTimestamp || "未知"} 至 ${summary.lastTimestamp || "未知"} · 已解析 ${summary.eventCount} 条 · ${summary.id}`;
  els.matchedCount.textContent = `匹配 ${formatNumber(data.matched)} 条`;
  setMetrics(summary);
  drawRoleChart(summary);
  renderChapters(summary);
  renderFiles(summary);
}

function escapeHtml(text) {
  return String(text ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function renderInlineMarkdown(text) {
  return escapeHtml(text)
    .replace(/`([^`]+)`/g, "<code>$1</code>")
    .replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>")
    .replace(/\*([^*]+)\*/g, "<em>$1</em>");
}

function normalizeSquashedTextSegment(text) {
  let value = String(text || "").replace(/\r\n?/g, "\n").trim();
  const newlineCount = (value.match(/\n/g) || []).length;
  const hasStructure = /(^|\s)(#{1,6}\s+|---|\-\s+\*\*|\d+\.\s+|\|[^|\n]+\|)/.test(value);
  if (!hasStructure) return value;

  if (newlineCount < 4) {
    value = value
      .replace(/\s+---\s+/g, "\n\n---\n\n")
      .replace(/([^\n])\s+(#{1,6})\s+/g, "$1\n\n$2 ")
      .replace(/\s+(-|\*)\s+(?=\*\*|[A-Za-z0-9\u4e00-\u9fff])/g, "\n$1 ")
      .replace(/\s+(\d+\.)\s+(?=[A-Za-z0-9\u4e00-\u9fff])/g, "\n$1 ")
      .replace(/\|\s+\|/g, "|\n|")
      .replace(/([^\n])\s+(\|[^\n]+\|\n\|[-:\s|]+\|)/g, "$1\n\n$2");
  }

  return value.replace(/\n{3,}/g, "\n\n").trim();
}

function normalizeCodeFenceContent(text) {
  return String(text || "")
    .trim()
    .replace(/\s+(?=Input\s+\()/g, "\n")
    .replace(/\s+(?=Stem\s+\()/g, "\n")
    .replace(/\s+(?=Stage\s+\d+:)/g, "\n")
    .replace(/\s+(?=[┌│└├┤▼])/g, "\n")
    .replace(/\s+↓\s+/g, "\n↓\n")
    .replace(/\n{3,}/g, "\n\n");
}

function makeInlineNode(tagName, text, className = "") {
  const node = document.createElement(tagName);
  if (className) node.className = className;
  node.innerHTML = renderInlineMarkdown(text);
  return node;
}

function isTableSeparator(line) {
  return /^\|\s*:?-{2,}:?\s*(\|\s*:?-{2,}:?\s*)+\|?$/.test(line.trim());
}

function isTableRow(line) {
  const trimmed = line.trim();
  return trimmed.startsWith("|") && trimmed.includes("|", 1);
}

function splitTableCells(line) {
  return line
    .trim()
    .replace(/^\|/, "")
    .replace(/\|$/, "")
    .split("|")
    .map((cell) => cell.trim());
}

function appendTable(container, lines, startIndex) {
  const rows = [];
  let index = startIndex;
  while (index < lines.length && isTableRow(lines[index])) {
    if (!isTableSeparator(lines[index])) {
      rows.push(splitTableCells(lines[index]));
    }
    index += 1;
  }
  if (!rows.length) return startIndex;

  const wrapper = document.createElement("div");
  wrapper.className = "md-table-wrap";
  const table = document.createElement("table");
  table.className = "md-table";
  const [head, ...bodyRows] = rows;
  const thead = document.createElement("thead");
  const headRow = document.createElement("tr");
  for (const cell of head) {
    const th = document.createElement("th");
    th.innerHTML = renderInlineMarkdown(cell);
    headRow.appendChild(th);
  }
  thead.appendChild(headRow);
  table.appendChild(thead);

  if (bodyRows.length) {
    const tbody = document.createElement("tbody");
    for (const row of bodyRows) {
      const tr = document.createElement("tr");
      for (const cell of row) {
        const td = document.createElement("td");
        td.innerHTML = renderInlineMarkdown(cell);
        tr.appendChild(td);
      }
      tbody.appendChild(tr);
    }
    table.appendChild(tbody);
  }
  wrapper.appendChild(table);
  container.appendChild(wrapper);
  return index;
}

function appendList(container, lines, startIndex, ordered) {
  const list = document.createElement(ordered ? "ol" : "ul");
  list.className = "md-list";
  const pattern = ordered ? /^\d+\.\s+(.+)$/ : /^[-*]\s+(.+)$/;
  let index = startIndex;
  while (index < lines.length) {
    const match = lines[index].trim().match(pattern);
    if (!match) break;
    const item = document.createElement("li");
    item.innerHTML = renderInlineMarkdown(match[1]);
    list.appendChild(item);
    index += 1;
  }
  container.appendChild(list);
  return index;
}

function appendTextSegment(container, text) {
  const normalized = normalizeSquashedTextSegment(text);
  if (!normalized) return;

  const lines = normalized.split("\n");
  let paragraph = [];

  const flushParagraph = () => {
    const content = paragraph.join(" ").trim();
    paragraph = [];
    if (content) container.appendChild(makeInlineNode("p", content, "md-paragraph"));
  };

  for (let index = 0; index < lines.length;) {
    const line = lines[index].trim();
    if (!line) {
      flushParagraph();
      index += 1;
      continue;
    }

    const heading = line.match(/^(#{1,6})\s+(.+)$/);
    if (heading) {
      flushParagraph();
      const level = Math.min(5, Math.max(3, heading[1].length + 2));
      const node = makeInlineNode(`h${level}`, heading[2], `md-heading md-heading-${heading[1].length}`);
      container.appendChild(node);
      index += 1;
      continue;
    }

    if (/^---+$/.test(line)) {
      flushParagraph();
      const hr = document.createElement("hr");
      hr.className = "md-rule";
      container.appendChild(hr);
      index += 1;
      continue;
    }

    if (isTableRow(line) && index + 1 < lines.length && isTableSeparator(lines[index + 1])) {
      flushParagraph();
      index = appendTable(container, lines, index);
      continue;
    }

    if (/^[-*]\s+/.test(line)) {
      flushParagraph();
      index = appendList(container, lines, index, false);
      continue;
    }

    if (/^\d+\.\s+/.test(line)) {
      flushParagraph();
      index = appendList(container, lines, index, true);
      continue;
    }

    paragraph.push(line);
    index += 1;
  }
  flushParagraph();
}

function renderReadableText(text) {
  const container = document.createElement("div");
  container.className = "readable-block";
  const parts = String(text || "").split("```");
  parts.forEach((part, index) => {
    if (!part.trim()) return;
    if (index % 2 === 1) {
      const pre = document.createElement("pre");
      pre.className = "code-block";
      pre.textContent = normalizeCodeFenceContent(part);
      container.appendChild(pre);
      return;
    }
    appendTextSegment(container, part);
  });
  return container;
}

function blockToPlainText(block) {
  const title = block.title ? `${block.title}\n` : "";
  return `${title}${block.text || ""}`;
}

function eventToPlainText(event) {
  return event.blocks.map(blockToPlainText).join("\n\n");
}

function renderBlock(block) {
  const text = block.text || "";
  if (block.hidden) {
    const div = document.createElement("div");
    div.className = "text-block hidden-note";
    div.textContent = text;
    return div;
  }

  if (block.kind === "tool_use" || block.kind === "tool_result") {
    const details = document.createElement("details");
    details.className = "tool-block";
    if (block.kind === "tool_use") details.open = true;
    const summary = document.createElement("summary");
    summary.textContent = block.kind === "tool_use" ? `工具调用: ${block.title || block.tool || "unknown"}` : "工具结果";
    const pre = document.createElement("pre");
    pre.textContent = text;
    details.append(summary, pre);
    return details;
  }

  return renderReadableText(text);
}

function renderEvents(events, append = false) {
  if (!append) {
    els.timeline.className = "timeline";
    els.timeline.innerHTML = "";
  }
  if (!events.length && !append) {
    els.timeline.className = "timeline empty-state";
    els.timeline.innerHTML = `<div class="empty-copy"><strong>没有匹配事件</strong><span>可以清空搜索，或放宽时间范围。</span></div>`;
    return;
  }

  for (const event of events) {
    const node = els.eventTemplate.content.firstElementChild.cloneNode(true);
    node.dataset.role = event.role;
    const pill = node.querySelector(".role-pill");
    const role = event.role || "unknown";
    pill.classList.add(`role-${role}`);
    pill.textContent = roleLabels[role] || role;
    node.querySelector("time").textContent = event.timestamp.local || `line ${event.line}`;

    const content = node.querySelector(".event-content");
    for (const block of event.blocks || []) {
      const rendered = renderBlock(block);
      if (rendered) content.appendChild(rendered);
    }
    if (!content.childElementCount && event.snippet) {
      const div = document.createElement("div");
      div.className = "text-block";
      div.textContent = event.snippet;
      content.appendChild(div);
    }

    node.querySelector(".event-copy").addEventListener("click", async () => {
      await navigator.clipboard.writeText(eventToPlainText(event));
      toast("事件文本已复制");
    });
    els.timeline.appendChild(node);
  }
}

async function loadEvents(offset = 0, append = false) {
  if (!state.selectedId || state.loading) return;
  state.loading = true;
  els.loadMoreBtn.disabled = true;
  try {
    const data = await getJson(`/api/session?${currentParams(offset).toString()}`);
    updateSummary(data);
    renderEvents(data.events, append);
    state.nextOffset = data.nextOffset;
    els.loadMoreBtn.hidden = data.nextOffset === null;
  } catch (error) {
    els.timeline.className = "timeline empty-state";
    els.timeline.innerHTML = `<div class="empty-copy"><strong>加载失败</strong><span>${escapeHtml(error.message)}</span></div>`;
  } finally {
    state.loading = false;
    els.loadMoreBtn.disabled = false;
  }
}

async function selectSession(id) {
  state.selectedId = id;
  state.nextOffset = null;
  renderSessions();
  await loadEvents(0, false);
}

async function refreshSessions() {
  const [config, payload] = await Promise.all([getJson("/api/config"), getJson("/api/sessions")]);
  state.config = config;
  state.sessions = payload.sessions || [];
  els.dataDir.textContent = config.dataDir;
  renderSessions();
  if (!state.selectedId && state.sessions.length) {
    await selectSession(state.sessions[0].id);
  } else if (state.selectedId) {
    await loadEvents(0, false);
  }
}

function exportUrl(format) {
  if (!state.selectedId) return null;
  const params = currentParams(0);
  params.delete("offset");
  params.delete("limit");
  params.set("format", format);
  return `/api/export?${params.toString()}`;
}

function attachEvents() {
  const reload = debounce(() => loadEvents(0, false), 280);
  els.sessionSearch.addEventListener("input", renderSessions);
  els.queryInput.addEventListener("input", reload);
  els.roleFilter.addEventListener("change", reload);
  els.startInput.addEventListener("change", reload);
  els.endInput.addEventListener("change", reload);
  els.includeTools.addEventListener("change", reload);
  els.includeSystem.addEventListener("change", reload);
  els.includeMeta.addEventListener("change", reload);
  els.refreshBtn.addEventListener("click", () => refreshSessions().catch((error) => toast(error.message)));
  els.loadMoreBtn.addEventListener("click", () => {
    if (state.nextOffset !== null) loadEvents(state.nextOffset, true);
  });
  els.exportMdBtn.addEventListener("click", () => {
    const url = exportUrl("markdown");
    if (url) window.location.href = url;
  });
  els.exportHtmlBtn.addEventListener("click", () => {
    const url = exportUrl("html");
    if (url) window.location.href = url;
  });
  els.exportJsonBtn.addEventListener("click", () => {
    const url = exportUrl("json");
    if (url) window.location.href = url;
  });
  window.addEventListener("resize", debounce(() => {
    if (state.current) drawRoleChart(state.current.summary);
  }, 180));
}

attachEvents();
refreshSessions().catch((error) => {
  els.timeline.className = "timeline empty-state";
  els.timeline.innerHTML = `<div class="empty-copy"><strong>启动失败</strong><span>${escapeHtml(error.message)}</span></div>`;
});
