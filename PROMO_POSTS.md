# Claude Conversation Lens 推广文案

## 短推文版

我做了一个本地小工具：Claude Conversation Lens。

使用场景很具体：Claude Code 用久了以后，`.jsonl` 日志里其实保存了大量项目上下文、debug 过程、实验方案和代码修改证据，但原始文件很难直接阅读。

这个工具可以把 JSONL 会话转成可搜索的时间线：

- 自动生成会话标题
- 中英双语界面
- 搜索文件名、命令、实验名
- 展开工具调用和代码块
- 按角色/时间筛选
- 导出 Markdown / HTML / JSON

使用方法：

```bash
python server.py --data-dir /path/to/claude-code-jsonl-folder
```

然后打开：

```text
http://127.0.0.1:8765
```

不是想替代 IDE，也不是复杂平台，只是把 AI 编程过程从“看不懂的日志”变成“能复盘的记录”。

## Thread 版

我做了一个本地工具：Claude Conversation Lens。

它解决的问题很小，但我自己每天都会遇到：

Claude Code 的 `.jsonl` 会话日志里有完整的 AI 编程过程，包括需求、回复、工具调用、代码片段、命令输出、路径、报错和实验决策。

但原始 JSONL 很难读。想回头找“当时为什么这么改”“某个实验方案在哪一轮讨论出来的”“哪个文件被反复修改过”，基本只能硬搜。

所以我做了一个本地 Web reader。

它会把一个 JSONL 目录扫描成会话列表，并自动生成较短的自然语言标题。例如 UUID 文件名不会直接显示成一长串，而会变成类似：

```text
OCT 异常检测 NAS EfficientNet RF-DETR 消融 · 2026-04-16
```

主要功能：

- Claude Code JSONL 解析
- User / Assistant / Tool / System 分角色时间线
- 工具调用、命令输出、代码块可展开
- 全文搜索
- 角色筛选和时间范围筛选
- 高频引用文件统计
- Markdown / HTML / JSON 导出
- 中英双语界面

使用方式很简单：

```bash
git clone https://github.com/dekra022/claude-conversation-lens.git
cd claude-conversation-lens
python server.py --data-dir /path/to/claude-code-jsonl-folder
```

浏览器打开：

```text
http://127.0.0.1:8765
```

我现在主要用它做三件事：

1. 搜索某个文件名，恢复这个文件是怎么一步步改出来的。
2. 搜索实验名或报错信息，把相关对话导出成 Markdown。
3. 复盘 AI 编程过程，把零散 trace 变成项目笔记。

它不是一个“AI 总结神器”，也不是云端知识库。

更准确地说，它是一个本地 LLM trace reader：把 Claude Code 留下的过程证据整理成可读、可查、可导出的材料。

## 中文技术社区版

做了个本地工具：Claude Conversation Lens。

背景是这样的：Claude Code 会把会话存成 `.jsonl`，这些日志其实非常有价值，里面有：

- 用户原始需求
- 模型给出的方案
- 工具调用
- 文件读取结果
- Bash 命令
- 代码 patch
- 报错和修复过程
- 实验设计和复盘内容

问题是原始 JSONL 太难读，UUID 文件名也没有语义。

这个工具做的事情就是把这些日志整理成一个本地网页：

- 自动扫描 JSONL 会话
- 给 UUID 会话生成短标题
- 用时间线展示对话
- 工具调用和代码证据可折叠
- 支持搜索、筛选、导出
- 支持中文/英文界面切换

最常见的用法：

```bash
python server.py --data-dir ./claude-logs
```

然后在浏览器里打开：

```text
http://127.0.0.1:8765
```

适合的场景：

- 从长会话里找某个实验方案
- 找某个 bug 是怎么被定位的
- 把 AI 编程过程整理成项目文档
- 导出一段对话到 Obsidian / README / 论文笔记
- 复盘 agent 工具调用到底做了什么

我觉得 AI coding 之后会产生一个新问题：代码本身有 Git 管理，但 AI 参与产生的“过程知识”很容易丢。

这个项目就是把这部分 trace 先整理起来。

## English Version

I built Claude Conversation Lens, a local web app for reading Claude Code `.jsonl` logs.

The use case is simple: after using Claude Code for real development, the logs contain a lot of valuable context: prompts, assistant replies, tool calls, command output, code patches, file paths, errors, and design decisions.

Raw JSONL is hard to read, and UUID session names are not useful.

Conversation Lens turns those logs into a searchable local timeline:

- readable session titles for UUID files
- bilingual UI
- role-aware timeline
- expandable tool calls and code evidence
- full-text search
- time and role filters
- Markdown / HTML / JSON export

Run it locally:

```bash
git clone https://github.com/dekra022/claude-conversation-lens.git
cd claude-conversation-lens
python server.py --data-dir /path/to/claude-code-jsonl-folder
```

Open:

```text
http://127.0.0.1:8765
```

It is not meant to replace your IDE or Git history. It is a lightweight local trace reader for making AI-assisted programming sessions easier to review, search, and reuse.

## 会不会被说“这有捷径”？

有可能。比较可能被提到的替代方案：

- 直接用 Claude Code 自带历史/转录。
- 用 `jq`、`rg`、`grep` 搜 JSONL。
- 写一个几十行脚本把 JSONL 转 Markdown。
- 把日志丢给另一个 LLM 总结。

这些都成立，所以宣传时不要说成“首创”或“革命性工具”。更稳的说法是：

- 它不是替代 `grep/jq`，而是把常用复盘工作流做成一个本地 UI。
- 它不是 JSON 美化器，重点是角色归一化、工具证据展开、时间线、搜索筛选和导出。
- 它不是自动总结工具，默认不篡改内容，保留原始 trace 的可追溯性。
- 它适合日志已经很多、需要频繁回看和导出的人；如果只是偶尔查一条记录，`rg` 当然更快。

更防喷的定位：

> A local reader for Claude Code traces. Simple, boring, useful.

或者中文：

> 一个本地 Claude Code 日志阅读器，不追求神奇，只解决“日志太难复盘”的问题。
