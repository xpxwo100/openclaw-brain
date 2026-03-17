# OpenClaw Brain

> 一个为 OpenClaw 设计的多层记忆系统。这次不是“脑科学名词堆砌”，而是能真正落地的工程版本。

[English documentation / 英文文档](./README.md)

## 项目简介

OpenClaw Brain 提供了一条完整的记忆处理链路：

- **注意力门控**：决定哪些信息值得记住
- **工作记忆**：保存短时任务状态
- **海马体缓冲**：快速编码最近候选记忆
- **情景记忆**：存储事件和经历
- **语义记忆**：存储事实、规则、偏好
- **检索与上下文构建**：把记忆变成可注入 prompt 的 recall block
- **持久化后端**：支持 JSONL 和 LanceDB
- **OpenClaw Hook / Plugin 集成**：接入真实消息流和工具流

项目目标支持 **Windows / Linux / macOS** 三个平台部署。

---

## 目录

- [项目目标](#项目目标)
- [核心能力](#核心能力)
- [项目结构](#项目结构)
- [快速开始](#快速开始)
- [OpenClaw 集成](#openclaw-集成)
- [存储后端](#存储后端)
- [跨平台部署](#跨平台部署)
- [文档导航](#文档导航)
- [开发说明](#开发说明)
- [路线图](#路线图)
- [贡献方式](#贡献方式)
- [许可证](#许可证)

---

## 项目目标

旧版本的问题很典型：

- 概念很大，边界很虚
- 不同 memory 对象结构不统一
- 缺少统一编排入口
- recall 和 consolidation 没真正串成一条主线

这次重构重点解决：

- 引入统一数据模型：`MemoryRecord`
- 引入统一编排入口：`OpenClawBrain`
- 增加面向 prompt 的 `build_context()`
- 增加持久化能力，支持真实部署
- 加入 OpenClaw hooks / plugin 接口，能接入正式链路

---

## 核心能力

### 记忆系统能力
- 使用 `MemoryRecord` 统一记忆结构
- 基于注意力评分进行记忆写入
- 工作记忆支持 TTL 和容量控制
- 海马体作为快速编码缓冲层
- 情景记忆和语义记忆分层存储
- 支持巩固、提升和遗忘机制
- 多因素 recall 重排
- 支持重复抑制的上下文构建

### 持久化能力
- `jsonl`：透明、可读、适合调试
- `lancedb`：适合扩展到向量检索和更大规模
- 通过 `OpenClawBrain.save()` / `OpenClawBrain.load()` 读写

### OpenClaw 集成能力
- `hooks/brain-ingest`：统一处理消息写入 + 工具历史写入 + 语义知识提取
- `plugins/brain-prompt`：在 `before_prompt_build` 阶段注入 recall block

### 跨平台能力
- Windows 的 PowerShell 使用说明
- Linux / macOS 的 shell 使用说明
- 本地开发和 OpenClaw 工作区部署路径说明

---

## 项目结构

```text
openclaw-brain/
├─ brain/                     # 核心记忆流水线
│  ├─ base.py                 # 统一记忆模型
│  ├─ attention.py            # 注意力门控
│  ├─ working_memory.py       # 工作记忆
│  ├─ hippocampus.py          # 海马体缓冲
│  ├─ episodic.py             # 情景记忆
│  ├─ semantic.py             # 语义记忆
│  ├─ retrieval.py            # 检索与重排
│  ├─ consolidation.py        # 巩固 / 遗忘原语
│  ├─ context.py              # Recall 上下文构建
│  └─ orchestrator.py         # OpenClawBrain 总入口
├─ storage/                   # 持久化后端
├─ hooks/                     # OpenClaw hooks 与 Python bridge
├─ plugins/brain-prompt/      # 回答前注入的 OpenClaw 插件
├─ docs/                      # 架构与部署文档
├─ examples/                  # 示例代码
├─ tests/                     # 测试
└─ verify.py                  # 结构 / 导入 / 插件 / 测试校验
```

---

## 快速开始

### 环境要求

- Python **3.9+**
- 如果需要接 OpenClaw plugin，建议 Node.js **18+**
- OpenClaw 运行时是**可选依赖**，只有在需要 hook / plugin 集成时才需要

### 开发安装

#### Windows PowerShell

```powershell
cd C:\path\to\openclaw-brain
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

#### Linux / macOS

```bash
cd /path/to/openclaw-brain
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 基础示例

```python
from brain import OpenClawBrain

brain = OpenClawBrain(attention_threshold=0.4)

brain.remember(
    "记住，用户喜欢被叫鸡哥",
    context={"kind": "preference", "source": "profile"},
    importance=0.9,
)

results = brain.recall("鸡哥", limit=5)
for item in results:
    print(item.memory.content)

context_block = brain.build_context(
    query="我应该怎么称呼用户？",
    recent_messages=["记住，用户喜欢被叫鸡哥"],
    recent_message_ids=["m1"],
    limit=3,
)

print(context_block["context_text"])
```

---

## OpenClaw 集成

这个项目包含 2 个主要集成面：

### 1. 统一 Ingest Hook
用于把重要消息写入记忆、记录工具调用历史，并从工具结果中提取语义知识。

- 路径：`hooks/brain-ingest`
- 文档：[`hooks/brain-ingest/HOOK.md`](./hooks/brain-ingest/HOOK.md)

### 2. Prompt 注入 Plugin
在 `before_prompt_build` 阶段把 recall block 注入 system prompt。

- 路径：`plugins/brain-prompt`
- 文档：[`plugins/brain-prompt/README.md`](./plugins/brain-prompt/README.md)

### 目标运行链路

```text
message/tool events
  -> OpenClawBrain persisted store
  -> build_context(query, recent_messages, ...)
  -> prependSystemContext
  -> model answer
```

---

## 存储后端

### JSONL
适合场景：

- 本地调试
- 直接查看记忆文件
- 简单备份
- 不想引入数据库依赖

### LanceDB
适合场景：

- 更大规模的持久化存储
- 后续扩展向量检索
- 更清晰地演进为语义搜索架构

### 示例

```python
from brain import OpenClawBrain

brain = OpenClawBrain(attention_threshold=0.1)
brain.remember("用户偏好简洁回答", context={"kind": "preference"}, importance=0.9)

brain.save("./data/brain-jsonl", backend="jsonl")
brain.save("./data/brain-lancedb", backend="lancedb")
```

---

## 跨平台部署

详细说明见：[`DEPLOYMENT.zh-CN.md`](./DEPLOYMENT.zh-CN.md)

支持目标：

- **Windows**：PowerShell、本地 OpenClaw 工作区部署
- **Linux**：本地 / 服务器部署，适合 cron 场景
- **macOS**：本地开发与桌面式 OpenClaw 部署

部署原则：

- 不要在你自己的配置里硬编码路径分隔符
- Python 和 Node 最好都在 `PATH` 中可用
- 每台机器都使用独立虚拟环境
- 持久化目录不要放在临时目录下

---

## 文档导航

### 英文文档
- [README](./README.md)
- [Architecture](./docs/architecture.md)
- [Deployment Guide](./DEPLOYMENT.md)
- [Contributing](./CONTRIBUTING.md)
- [Security](./SECURITY.md)

### 中文文档
- [中文 README](./README.zh-CN.md)
- [架构说明](./docs/architecture.zh-CN.md)
- [部署指南](./DEPLOYMENT.zh-CN.md)

---

## 开发说明

### 运行测试

```bash
python -m pytest -q
```

### 校验结构、导入、插件导入和测试

```bash
python verify.py
```

### 可编辑安装

```bash
pip install -e .
```

---

## 路线图

近期重点：

- 更深入的 LanceDB / 向量检索接入
- 更强的语义抽取流程
- 更稳定的 repository 抽象层
- 更完整的 OpenClaw 配置示例
- 增加 Windows / Linux / macOS 的 CI 验证

---

## 贡献方式

欢迎提 PR。

提交前建议至少做到：

1. 先跑测试
2. 先跑 `python verify.py`
3. 改行为时同步更新文档
4. 如果改了公共 API，要明确写清兼容性影响

详见 [`CONTRIBUTING.md`](./CONTRIBUTING.md)。

---

## 许可证

MIT，见 [`LICENSE`](./LICENSE)。
