# 🧠 OpenClaw Brain

**类脑记忆系统 for OpenClaw** - 模拟人脑的多层级记忆、注意力门控与记忆巩固机制

> "The true nature of memory is not to remember, but to reconstruct." 

---

## 🎯 项目目标

构建一个受人脑启发的记忆系统，让 OpenClaw 能够：
- **选择性注意**：像人脑一样过滤无关信息
- **多级存储**：工作记忆 → 短期记忆 → 长期记忆
- **睡眠巩固**：定期整合、压缩、强化关键记忆
- **联想提取**：基于情境、情绪、关联度的智能检索
- **自然遗忘**：艾宾浩斯曲线驱动的遗忘机制

---

## 🏗️ 系统架构

```
┌─────────────────────────────────────────────────────┐
│  感知层 (Perception)                                │
│  (消息、工具输出、文件变化、定时触发)                │
└─────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────┐
│  注意力门控 (Attention Gate)                        │
│  - 优先级过滤 (P0/P1/P2)                            │
│  - 情绪标记 (用户强调/纠正/重复)                    │
│  - 关联触发 (与现有记忆强相关)                      │
└─────────────────────────────────────────────────────┘
                        ↓
        ┌───────────────┴───────────────┐
        ↓                               ↓
┌───────────────────┐           ┌───────────────────┐
│  工作记忆区       │           │  快速通道         │
│  (Working Memory) │           │  (Reflex)         │
│  - 容量：~20 条     │           │  - 高频模式匹配   │
│  - 临时变量/状态  │           │  - 自动化响应     │
└───────────────────┘           └───────────────────┘
                        ↓
┌─────────────────────────────────────────────────────┐
│  海马体 (Hippocampus)                               │
│  - 新事件快速编码                                   │
│  - 模式识别与关联                                   │
│  - 睡眠时巩固到长期记忆                             │
└─────────────────────────────────────────────────────┘
                        ↓
        ┌───────────────┴───────────────┐
        ↓                               ↓
┌───────────────────┐           ┌───────────────────┐
│  情景记忆         │           │  语义记忆         │
│  (Episodic)       │           │  (Semantic)       │
│  - 会话历史       │           │  - 事实知识       │
│  - 用户偏好       │           │  - 技能/规则      │
│  - 时间戳 + 情境  │           │  - 概念网络       │
│  - 向量化 (RAG)   │           │  - 结构化存储     │
└───────────────────┘           └───────────────────┘
                        ↓
┌─────────────────────────────────────────────────────┐
│  记忆巩固循环 (Consolidation Loop)                  │
│  - 每 4 小时：提取、向量化、关联                      │
│  - 每天：睡眠重放、整合、衰减                       │
│  - 艾宾浩斯遗忘曲线                                 │
└─────────────────────────────────────────────────────┘
```

---

## 📁 项目结构

```
openclaw-brain/
├── README.md                    # 项目说明
├── LICENSE                      # MIT License
├── requirements.txt             # Python 依赖
├── setup.py                     # 安装脚本
│
├── brain/                       # 核心模块
│   ├── __init__.py
│   ├── attention.py             # 注意力门控
│   ├── working_memory.py        # 工作记忆区
│   ├── hippocampus.py           # 海马体（编码/巩固）
│   ├── episodic.py              # 情景记忆
│   ├── semantic.py              # 语义记忆
│   ├── consolidation.py         # 记忆巩固循环
│   └── retrieval.py             # 联想提取
│
├── models/                      # 数据模型
│   ├── __init__.py
│   ├── memory.py                # 记忆单元基类
│   ├── event.py                 # 事件模型
│   └── association.py           # 关联关系
│
├── storage/                     # 存储后端
│   ├── __init__.py
│   ├── jsonl_store.py          # JSONL 文件存储
│   ├── vector_store.py          # 向量数据库（LanceDB）
│   └── sql_store.py             # 关系型存储（可选）
│
├── hooks/                       # OpenClaw 集成
│   ├── __init__.py
│   ├── on_message.py            # 消息 Hook
│   ├── on_tool_call.py          # 工具调用 Hook
│   ├── heartbeat.py             # 心跳 Hook
│   └── cron_jobs.py             # 定时任务
│
├── tests/                       # 测试
│   ├── __init__.py
│   ├── test_attention.py
│   ├── test_hippocampus.py
│   └── test_consolidation.py
│
├── examples/                    # 示例
│   ├── basic_usage.py
│   ├── custom_attention_gate.py
│   └── sleep_consolidation.py
│
└── docs/                        # 文档
    ├── architecture.md          # 架构设计
    ├── api.md                   # API 参考
    ├── neuroscience.md          # 神经科学原理
    └── openclaw_integration.md  # OpenClaw 集成指南
```

---

## 🚀 快速开始

### 安装

```bash
pip install openclaw-brain
```

### 基础用法

```python
from brain import OpenClawBrain

# 初始化大脑
brain = OpenClawBrain(
    workspace="C:/Users/Administrator.xpxwo/.openclaw/workspace",
    attention_threshold=0.7,
    consolidation_interval_hours=4
)

# 添加记忆（注意力门控自动判断是否重要）
brain.remember("用户喜欢被叫'<BOT_NAME>'", context={"source": "user_profile"})

# 工作记忆区（临时存储）
brain.working.add("临时变量", value=42)

# 提取记忆（联想检索）
memories = brain.remember("用户偏好", mode="semantic")

# 触发巩固（通常在定时任务中）
brain.consolidate()
```

---

## 🧠 核心机制

### 1. 注意力门控 (Attention Gate)

模拟人脑的选择性注意，决定哪些信息值得进入记忆：

```python
from brain.attention import AttentionGate

gate = AttentionGate(
    priority_keywords=["记住", "重要", "注意", "P0"],
    emotional_triggers=["纠正", "否定", "强调"],
    association_threshold=0.8
)

should_remember = gate.should_pass(
    text="记住，我喜欢用 <MODEL_NAME> 处理简单任务",
    context={"user": "<USER_NAME>", "timestamp": "2026-03-17T04:52"}
)
# 返回：True (包含"记住"关键词)
```

### 2. 工作记忆区 (Working Memory)

容量有限的临时存储区，模拟人类的工作记忆：

```python
from brain.working_memory import WorkingMemory

wm = WorkingMemory(capacity=20)

# 添加项目
wm.add("用户当前任务", "创建 OpenClaw 记忆系统")

# 获取所有项目（FIFO + 重要性排序）
items = wm.get_all()

# 复述（将重要项目转入长期记忆）
wm.rehearse("用户当前任务", target="semantic")
```

### 3. 睡眠巩固 (Sleep Consolidation)

定期整合、压缩、强化记忆：

```python
from brain.consolidation import SleepConsolidation

consolidator = SleepConsolidation(brain)

# 执行巩固（通常在凌晨 3 点）
consolidator.run()
# - 重放当天事件
# - 合并重复记忆
# - 应用艾宾浩斯衰减
# - 修剪过期临时记忆
```

---

## 📊 记忆生命周期

```
[感知] → [注意力过滤] → [工作记忆] → [海马体编码] → [情景/语义记忆]
                              ↓                      ↓
                        (容量限制)            [睡眠巩固]
                              ↓                      ↓
                        [遗忘曲线] ←────────── [联想提取]
```

### 遗忘曲线实现

```python
from brain.forgetting import EbbinghausCurve

curve = EbbinghausCurve()

# 计算记忆保留率（小时后）
retention = curve.retention(hours=24)  # ~35%
retention = curve.retention(hours=168)  # ~15% (一周后)

# 应用衰减
memory.strength *= curve.retention(hours_since_last_review)
```

---

## 🔧 配置示例

```yaml
# config.yaml
brain:
  working_memory:
    capacity: 20
    ttl_minutes: 30

  attention:
    priority_threshold: 0.7
    emotional_boost: 1.5
    association_weight: 0.3

  consolidation:
    interval_hours: 4
    sleep_time: "03:00"
    ebbinghaus_halflife_hours: 24

  storage:
    type: "jsonl"  # 或 "lancedb", "sqlite"
    path: "./memory"
    vector_model: "BAAI/bge-m3"
```

---

## 🧪 测试

```bash
pytest tests/ -v
```

---

## 📚 文档

- [架构设计](docs/architecture.md)
- [API 参考](docs/api.md)
- [神经科学原理](docs/neuroscience.md)
- [OpenClaw 集成](docs/openclaw_integration.md)

---

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

---

## 📄 License

MIT License

---

## 🙏 致谢

- OpenClaw 团队
- 认知神经科学研究
- 记忆心理学理论

---

**🌟 让 AI 像人一样记忆，像人一样遗忘，像人一样学习。**
