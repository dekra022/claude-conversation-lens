# Claude Conversation Lens

English | [中文](#中文说明)

Claude Conversation Lens is a local web application for turning Claude Code JSONL logs into searchable, readable timelines. It parses mixed user, assistant, system, tool-call, and tool-result records, keeps code and command evidence expandable, and exports cleaned conversations to Markdown, HTML, or JSON.

## Why "Lens"?

Here, **lens** means "a viewing lens" or "an analytical lens", not a prism. The project takes raw agent traces and focuses them into a readable view: timeline, search, evidence, and export.

## What Are UUID File Names?

Claude Code session logs are often named like:

```text
f1043af8-ba2f-4e52-9240-ee57443f7e68.jsonl
```

That string is a UUID-style session identifier. It is useful for uniqueness, but it does not encode a meaningful title. Conversation Lens keeps the original ID for traceability and generates a readable display title from the first real user turn plus the session date.

## Run

```powershell
git clone https://github.com/dekra022/claude-conversation-lens.git
cd claude-conversation-lens
python server.py --data-dir "path\to\claude-code-jsonl-folder" --host 127.0.0.1 --port 8765
```

Open `http://127.0.0.1:8765`.

If `--data-dir` is omitted, the app reads from `./data`. You can also set `CLAUDE_LOG_DIR`:

```powershell
$env:CLAUDE_LOG_DIR="path\to\claude-code-jsonl-folder"
python server.py
```

On macOS/Linux:

```bash
CLAUDE_LOG_DIR=/path/to/claude-code-jsonl-folder python server.py
```

## Features

- Streaming JSONL parser for Claude Code session records, including `tool_use`, `tool_result`, command output, file snapshots, and token usage metadata.
- Natural-language timeline that hides private reasoning by default while preserving tool and code traces as expandable evidence.
- Readable auto-generated session titles for UUID-named JSONL files.
- Session analytics: role distribution, tool-call counts, code-block counts, token totals, chapter extraction, and referenced-file ranking.
- Full-text search, role filtering, local-time range filtering, system/meta toggles, and incremental pagination for large logs.
- Markdown, HTML, and JSON export endpoints that respect the active filters.
- Dependency-light deployment using only the Python standard library plus static HTML/CSS/JavaScript.

## Resume Framing

**Claude Conversation Lens | Local LLM Trace Mining and Conversation Reconstruction Tool**

Built a dependency-light web application that reconstructs Claude Code JSONL traces into a searchable natural-language timeline. Designed a robust parser for heterogeneous records, tool calls, command outputs, code patches, file references, timestamps, and token usage; added interactive filtering, evidence expansion, session analytics, auto-title generation, and multi-format export. The system improves developer auditability and knowledge reuse for AI-assisted programming workflows.

---

# 中文说明

Claude Conversation Lens 是一个本地 Web 应用，用来把 Claude Code 生成的 JSONL 日志转换成可搜索、可阅读、可导出的自然语言时间线。它能解析用户输入、助手回复、系统记录、工具调用、工具结果、命令输出和代码片段，并把这些混杂记录整理成适合复盘的会话视图。

## 为什么叫 Lens？

这里的 **Lens** 不是“棱镜”那个意思，而是“镜头 / 透镜 / 观察视角”。这个项目的作用是把原始 agent trace 聚焦成一个可阅读的视图：时间线、搜索、证据展开和导出。

如果想完全中文化，也可以理解成：

- 对话镜头
- 会话透镜
- Trace 阅读镜

我保留 `Lens` 是因为英文技术项目里常用它表示“观察和分析某类复杂数据的工具”。

## UUID 文件名有实际含义吗？

像下面这种文件名：

```text
f1043af8-ba2f-4e52-9240-ee57443f7e68.jsonl
```

不是乱码，而是 UUID 风格的会话 ID。它的主要作用是保证每个会话文件唯一，通常不能直接转换出自然语言含义。

更合理的做法是：保留原始 UUID 作为可追溯 ID，同时根据会话内容自动生成标题。现在应用会从首个真实用户轮次提取标题，并加上日期，例如：

```text
MGEAD-NAS 搜索方案 · 2026-04-16
```

左侧列表会优先显示这种自然语言标题，下面保留原始 JSONL 文件名。

## 运行方式

```powershell
git clone https://github.com/dekra022/claude-conversation-lens.git
cd claude-conversation-lens
python server.py --data-dir "path\to\claude-code-jsonl-folder" --host 127.0.0.1 --port 8765
```

浏览器打开：

```text
http://127.0.0.1:8765
```

如果不传 `--data-dir`，应用会读取项目目录下的 `data` 文件夹。也可以使用环境变量：

```powershell
$env:CLAUDE_LOG_DIR="path\to\claude-code-jsonl-folder"
python server.py
```

macOS/Linux：

```bash
CLAUDE_LOG_DIR=/path/to/claude-code-jsonl-folder python server.py
```

## 功能

- 解析 Claude Code JSONL 中的用户、助手、系统、工具调用和工具结果记录。
- 把原始日志重建成自然语言时间线。
- 自动为 UUID 文件名生成可读会话标题。
- 默认隐藏 private reasoning，同时保留工具调用和代码证据。
- 支持全文搜索、角色筛选、时间范围筛选、系统/元数据开关。
- 统计角色分布、工具调用数、代码块数、token 粗统计和高频引用文件。
- 支持 Markdown、HTML、JSON 导出。
- 无前端构建依赖，仅依赖 Python 标准库和原生 HTML/CSS/JavaScript。

## 简历写法

**Claude Conversation Lens | 本地 LLM Trace Mining 与对话重建工具**

构建了一个轻量级本地 Web 应用，将 Claude Code JSONL 日志重建为可搜索、可审计、可导出的自然语言时间线。项目实现了异构记录解析、工具调用归档、代码证据展开、角色/时间/全文检索、会话统计、UUID 会话自动标题生成和多格式导出，提升 AI 编程过程的可复盘性和知识复用效率。
