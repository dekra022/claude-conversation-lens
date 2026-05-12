# Claude Conversation Lens

Claude Conversation Lens is a local web application for turning Claude Code JSONL logs into a searchable, readable research timeline. It parses mixed user, assistant, system, tool-call, and tool-result records, keeps code and command evidence expandable, and exports cleaned conversations to Markdown, HTML, or JSON.

## Run

```powershell
git clone https://github.com/<your-name>/claude-conversation-lens.git
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
- Session-level analytics: role distribution, tool-call counts, code-block counts, token totals, chapter extraction, and referenced-file ranking.
- Full-text search, role filtering, local-time range filtering, system/meta toggles, and incremental pagination for large logs.
- Markdown, HTML, and JSON export endpoints that respect the active filters.
- Dependency-light deployment using only the Python standard library plus static HTML/CSS/JavaScript.

## Resume Framing

**Claude Conversation Lens | Local LLM Trace Mining and Conversation Reconstruction Tool**

Built a dependency-light web application that reconstructs Claude Code JSONL traces into a searchable natural-language timeline. Designed a robust parser for heterogeneous records, tool calls, command outputs, code patches, file references, timestamps, and token usage; added interactive filtering, evidence expansion, session analytics, and multi-format export. The system improves developer auditability and knowledge reuse for AI-assisted programming workflows.

## Why It Is More Than a Viewer

Raw Claude Code logs are not a single chat transcript. They mix conversation turns, local command envelopes, structured tool calls, code payloads, file-history snapshots, metadata, and sometimes private reasoning blocks. This project normalizes those records into a higher-level event model, builds indexes and metrics on top of it, and presents a clean reader that still preserves provenance.

Good next steps for a master's-to-PhD-level version:

- Add semantic retrieval over conversation chunks using embeddings and hybrid BM25/vector ranking.
- Build topic segmentation with change-point detection over turns, files, tools, and token bursts.
- Add automatic session summarization with citation back to exact JSONL line numbers.
- Extract code-evolution graphs by linking tool calls, file paths, patches, and command results.
- Support privacy policies for redacting secrets and omitting sensitive command output during export.
