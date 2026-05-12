# Claude Conversation Lens 使用指南

Claude Conversation Lens 用来把 Claude Code 生成的 `.jsonl` 对话日志转换成可阅读、可搜索、可导出的自然语言时间线。它适合整理 AI 编程过程、恢复项目决策脉络、提取代码修改证据，以及把原始日志转成 Markdown/HTML 文档。

## 1. 启动应用

在 PowerShell 中运行：

```powershell
git clone https://github.com/<your-name>/claude-conversation-lens.git
cd claude-conversation-lens
python server.py --data-dir "path\to\claude-code-jsonl-folder" --host 127.0.0.1 --port 8765
```

浏览器打开：

```text
http://127.0.0.1:8765
```

如果不传 `--data-dir`，应用会默认读取项目目录下的 `data` 文件夹。也可以用环境变量指定日志目录：

```powershell
$env:CLAUDE_LOG_DIR="path\to\claude-code-jsonl-folder"
python server.py
```

如果已经启动过服务，直接刷新浏览器即可。

## 2. 选择会话

左侧是当前数据目录下扫描到的 Claude Code `.jsonl` 会话。

每个会话卡片会显示：

- 会话 ID
- 文件大小
- 事件数量
- 工具调用数量
- 首尾时间范围

点击任意会话后，右侧会加载对应的自然语言时间线。

## 3. 阅读时间线

右侧主区域会把原始 JSONL 中的记录整理成事件卡片：

- `User`: 用户输入
- `Assistant`: Claude 回复
- `Tool`: 工具结果、命令输出、文件读取结果
- `System`: 系统记录或本地命令元信息

普通文本会自动按轻量 Markdown 排版，支持：

- 标题
- 列表
- 表格
- 分隔线
- 代码块

工具调用和代码证据会以可展开块展示，便于保留上下文但不干扰阅读。

## 4. 搜索和筛选

顶部筛选栏支持：

- `Full Text Search`: 搜索正文、路径、命令、工具内容
- `Role`: 按 User / Assistant / Tool / System 过滤
- `Start / End`: 按北京时间筛选范围
- `Tool traces`: 是否显示工具调用和工具结果
- `System`: 是否显示系统记录
- `Meta`: 是否显示元数据记录

常见用法：

- 搜索某个文件名，恢复它在整个对话中的修改过程
- 搜索某个实验名，提取完整实验方案
- 只看 `Assistant`，快速阅读模型给出的方案
- 关闭 `Tool traces`，获得更干净的自然语言版本

## 5. 会话分析面板

页面上方会显示当前会话的统计信息：

- 解析事件数
- 工具调用数
- 代码块数
- token 粗统计

`Conversation Map` 显示不同角色的记录分布。

`Evidence Paths` 显示对话中最常被引用的文件路径，适合快速定位项目核心文件。

## 6. 导出

右上角提供三种导出：

- `Export MD`: 导出 Markdown，适合放进 Obsidian、论文笔记或项目文档
- `Export HTML`: 导出可直接浏览的 HTML
- `JSON`: 导出结构化 JSON，适合二次分析

导出会遵循当前筛选条件。例如，搜索 `MGEAD-NAS` 后再导出，只会导出匹配到的相关记录。

## 7. 推荐工作流

1. 选择一个 Claude Code `.jsonl` 会话。
2. 用关键词搜索项目名、实验名、文件名或命令。
3. 关闭不需要的 `Meta` 或 `System` 记录。
4. 展开工具调用，确认代码、命令和文件证据。
5. 导出 Markdown，作为项目复盘、实验记录或简历素材。

## 8. 常见问题

### 页面没有更新

浏览器可能缓存了旧的前端文件。使用：

```text
Ctrl + F5
```

强制刷新。

### 看不到会话

确认启动命令里的 `--data-dir` 指向包含 `.jsonl` 文件的目录。

### 内容太多

使用搜索词、时间范围和角色筛选缩小范围。页面默认分页加载，底部可以点击 `Load more` 继续加载。

### 不想显示工具输出

取消勾选 `Tool traces`，时间线会更接近普通聊天记录。

## 9. 适合写进简历的描述

Claude Conversation Lens 是一个本地 LLM trace mining 工具，用于将 Claude Code JSONL 日志重建为可搜索、可审计、可导出的自然语言时间线。项目实现了异构记录解析、工具调用归档、代码证据展开、角色/时间/全文检索、会话统计和多格式导出，提升 AI 编程过程的可复盘性和知识复用效率。
