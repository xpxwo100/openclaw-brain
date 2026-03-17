# 架构说明

[English version / 英文版本](./architecture.md)

## 目标

OpenClaw Brain 要解决的不是玄学问题，而是一个很具体的工程问题：

> Agent 不应该把每条消息都当成同等重要，也不应该只靠原始聊天记录来伪装“记忆一致性”。

所以这套架构重点优化的是：

- 选择性写入
- 分层记忆存储
- 面向 prompt 的 recall
- 可持久化
- 能真实接进 OpenClaw hooks / plugins

---

## 设计原则

### 1. 一个统一的记忆模型
所有长期记忆层都应该能表示成 `MemoryRecord`。

不然每个子系统自己造 memory shape，最后模块集成就会退化成满地 `getattr(...)`。

### 2. 认知命名可以保留，但工程边界必须清晰
像 *hippocampus*、*episodic memory* 这些词有用，但不能拿来掩盖职责不清。

每个模块都必须能落回明确的工程责任。

### 3. 先有总调度，再谈子模块
`OpenClawBrain` 是组合根（composition root）。

外部系统应该面向 orchestrator，而不是自己拼一堆子模块。

### 4. Prompt 注入是第一等公民
记忆如果不能改善回答，那就只是存储，不是能力。

所以这套系统不只是 **存**，还要能 **召回并注入** 到模型上下文里。

### 5. 可移植性很重要
项目要能在 Windows、Linux、macOS 上部署，不能一写完就绑死在某个壳子里。

---

## 分层模型

```text
input / event
   │
   ▼
AttentionGate
   │
   ├── reject
   ▼
Hippocampus
   │
   ├── WorkingMemory
   ├── EpisodicStore
   └── SemanticStore
           │
           ▼
MemoryRetriever
           │
           ▼
BrainContextBuilder
           │
           ▼
OpenClaw before_prompt_build plugin injection
```

---

## 组件说明

### 1. Attention Gate
**作用：** 判断一条信息是否值得占用记忆预算。

**输入：**
- 原始文本
- 可选上下文
- 可选记忆提示

**输出：**
- `AttentionResult`

**为什么需要它：**
没有门控，系统就会退化成一个聊天记录垃圾堆。

---

### 2. Working Memory
**作用：** 保存当前任务状态和短时重要信息。

**特性：**
- 容量受限
- 支持 TTL 过期
- 支持 rehearsal（复述 / 转存）
- 偏向当前任务上下文

**为什么需要它：**
Agent 需要一个临时聚焦区，而不是把所有内容都直接污染长期记忆。

---

### 3. Hippocampus
**作用：** 在进入长期层之前，快速编码候选记忆。

**特性：**
- 适合 append 写入
- 有界缓冲
- 保存最近候选记忆
- 能带 source/context 关联信息

**为什么需要它：**
不是所有“记住了”的内容都应该立刻升级为长期知识。

---

### 4. Episodic Store
**作用：** 持久保存事件型、时间型记忆。

**特性：**
- 事件导向
- 支持按时间检索
- 支持 recent-window 访问
- 适合回答“之前发生过什么”

**为什么需要它：**
Agent 经常需要回忆具体事件，而不是只有抽象事实。

---

### 5. Semantic Store
**作用：** 持久保存稳定知识。

**主要类型：**
- fact（事实）
- rule（规则）
- preference（偏好）
- general concept（通用概念）

**为什么需要它：**
像“用户喜欢简洁回答”这类偏好，不应该永远跟原始事件记录混在一起竞争。

---

### 6. Retrieval
**作用：** 从多个记忆层召回候选项并重排。

**可用信号：**
- 词法相关性
- 时间新近性
- 重要度
- 上下文匹配度
- 访问历史
- 记忆强度

**为什么需要它：**
直接暴力召回会很吵，重排才是真正把“存储”变成“可用记忆”的那一步。

---

### 7. Context Builder
**作用：** 把 recall 结果转成紧凑、可直接注入 prompt 的 recall block。

**职责：**
- 过滤最近聊天里的近似回声
- 优先保留 semantic / rule / preference
- 控制最终上下文块的长度
- 输出稳定文本给 prompt 注入层使用

**为什么需要它：**
如果系统只是把用户上一句话换个说法再说一遍，那不叫记忆，那叫偷懒。

---

### 8. Consolidation
**作用：** 把重复或重要的经验转化成更稳定的记忆。

**当前职责：**
- 去重
- 必要时把 episodic 提升为 semantic
- 调整 strength
- 基础遗忘 / 降权

**未来方向：**
- 更强的语义抽取
- 更靠谱的聚类与摘要
- 可选向量辅助巩固

---

## OpenClaw 集成模型

系统通过 3 个接入面和 OpenClaw 集成：

### Message Hook
抓取消息并决定哪些要记住。

### Tool-call Hook
把工具调用写入情景记忆，并尽可能抽取结构化语义知识。

### Prompt Plugin
通过 `before_prompt_build` 把 recall block 注入 system prompt。

这样就形成完整闭环：

```text
message / tool event
  -> ingestion
  -> persistence
  -> recall
  -> context block
  -> prompt injection
  -> better answer
```

---

## 持久化模型

### JSONL 后端
适合追求透明、简单备份和低成本调试的场景。

### LanceDB 后端
适合作为未来语义 / 向量检索的可扩展底座。

持久化接口故意设计成可切换后端，就是为了让认知层不要永远绑死在单一存储实现上。

---

## 跨平台说明

项目目标支持：

- **Windows**：本地 OpenClaw 工作区开发
- **Linux**：服务器和自动化友好的部署
- **macOS**：本地开发和桌面场景

可移植性的基本假设：

- Python 路径不能写死在某一种 shell 环境里
- Node 插件代码不能依赖平台特有的路径技巧
- 持久化目录应该放在稳定工作区，而不是纯临时目录

---

## 这套架构刻意不做什么

这不是：
- 完整认知科学模拟器
- 神奇 AGI 记忆引擎
- 所有记忆工具的替代品

它就是一个给 Agent 用的、务实的记忆子系统。

这才是重点。
