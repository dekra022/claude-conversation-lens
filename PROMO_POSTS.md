# Claude Conversation Lens 推销文案

## 短推文版

我做了一个本地工具：Claude Conversation Lens。

它可以把 Claude Code 的 `.jsonl` 日志转换成可阅读、可搜索、可导出的自然语言时间线。

支持：
- 自动解析 user / assistant / system / tool records
- 工具调用、代码块、命令输出可展开
- 全文搜索、角色筛选、时间范围筛选
- Markdown / HTML / JSON 导出

原始 JSONL 很难读，但里面藏着完整的 AI 编程过程、实验决策和代码演化证据。

这个工具的目标就是把 AI coding trace 变成可复盘、可审计、可复用的知识资产。

## Thread 版

我最近做了一个小工具：Claude Conversation Lens。

它解决的是一个很具体但很烦的问题：

Claude Code 的 `.jsonl` 日志保存了完整的 AI 编程过程，但原始文件几乎不可读。里面混着用户输入、模型回复、工具调用、命令输出、文件读取结果、系统记录和 metadata。

所以我把它做成了一个本地 Web 应用。

功能包括：

1. 把 Claude Code JSONL 重建成自然语言时间线
2. 自动区分 User / Assistant / Tool / System
3. 工具调用、代码块和命令输出可展开
4. 支持全文搜索、角色筛选和时间范围筛选
5. 自动统计工具调用数、代码块数、token 粗统计和引用文件排行
6. 支持导出 Markdown / HTML / JSON

我最喜欢的一点是：它不是简单的 JSON 美化器。

Claude Code 日志本质上是 LLM agent trace，里面有很多结构化证据。比如某段代码是怎么生成的、哪个文件被反复修改、某个实验方案是在哪一轮对话里形成的。

这些东西如果能被检索、阅读和导出，就可以变成项目复盘、实验记录、论文笔记，甚至简历素材。

现在我可以直接搜索一个实验名或文件名，然后导出相关对话，快速恢复完整上下文。

对 AI-assisted programming 来说，我觉得 trace mining 会越来越重要。

写代码只是第一步，更重要的是保留决策链、工具证据和演化过程。

Claude Conversation Lens 就是我对这个方向的一个本地原型。

## 中文朋友圈/技术社区版

做了一个本地小工具：Claude Conversation Lens。

用途很简单：把 Claude Code 生成的 `.jsonl` 对话日志整理成好读的自然语言时间线。

原始 JSONL 里其实保存了非常多有价值的信息：用户需求、模型方案、工具调用、代码片段、命令输出、文件路径、实验设计、debug 过程。但直接看文件非常痛苦，基本没法复盘。

这个工具做了几件事：

- 自动解析 Claude Code 的异构日志记录
- 把对话重建成按时间排列的阅读视图
- 支持 Markdown 式排版，表格、列表、代码块都能正常显示
- 工具调用和命令输出可以折叠展开
- 支持全文搜索、角色过滤、时间范围筛选
- 可以导出 Markdown / HTML / JSON

它更像一个本地的 LLM trace mining 工具，而不是 JSON viewer。

我现在主要用它来整理 AI 编程过程、恢复实验方案、提取项目决策记录，以及把复杂对话转成可写进文档的材料。

这个方向挺有意思：AI 写代码之后，如何管理和复用 AI 参与产生的过程知识，可能会变成一个新的工程问题。

## 英文版

I built Claude Conversation Lens, a local web app for turning Claude Code `.jsonl` logs into readable, searchable, exportable timelines.

Claude Code logs are not just chat transcripts. They contain user turns, assistant responses, tool calls, command output, file paths, code patches, system records, and metadata.

The app reconstructs those traces into a clean timeline with:

- role-aware parsing
- expandable tool and code evidence
- full-text search
- time and role filters
- session analytics
- Markdown / HTML / JSON export

The goal is to make AI coding traces auditable and reusable.

Instead of losing the reasoning, experiments, and code evolution inside raw JSONL files, you can turn them into project notes, research logs, or documentation.
