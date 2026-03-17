# 部署指南

[English version / 英文版本](./DEPLOYMENT.md)

## 适用范围

本指南覆盖以下平台的部署与运行：

- Windows
- Linux
- macOS

内容包括：
- 本地开发环境准备
- OpenClaw 工作区场景下的本地部署
- hooks / plugins 路径说明
- 持久化目录建议

---

## 1. 运行环境要求

### 必需
- Python 3.9+
- `pip`
- Node.js 18+（接 OpenClaw plugin 时推荐）

### 建议
- 每台机器使用独立虚拟环境
- 使用稳定的工作目录
- 如需 hooks / plugins 集成，先安装好 OpenClaw

---

## 2. 克隆与安装

### Windows（PowerShell）

```powershell
git clone <your-repo-url>
cd openclaw-brain
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install --upgrade pip
pip install -r requirements.txt
```

### Linux / macOS

```bash
git clone <your-repo-url>
cd openclaw-brain
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

---

## 3. 安装校验

```bash
python -m pytest -q
python verify.py
```

预期结果：
- 测试通过
- verify 中 structure / imports / plugin / tests 全部 OK

---

## 4. 持久化路径

### 独立项目模式
如果你直接运行这个项目，没有 OpenClaw 的 `workspace.dir` 上下文，默认回退存储路径是：

```text
./data/hook-brain/
```

### OpenClaw 工作区模式
通过 hooks / plugins 运行时，默认持久化目录是：

```text
<workspace>/.openclaw-brain/hooks/
```

例如：

- Windows：
  `C:\Users\you\.openclaw\workspace\.openclaw-brain\hooks\`
- Linux/macOS：
  `/home/you/.openclaw/workspace/.openclaw-brain/hooks/`

### 推荐做法
如果准备长期使用，建议把存储改到更清晰的位置，例如：

```text
<workspace>/data/openclaw-brain/
```

这样备份、迁移、排障都省事。

---

## 5. OpenClaw Hook 部署

### 统一 Ingest Hook
路径：

```text
hooks/brain-ingest
```

### Prompt 注入 Plugin
路径：

```text
plugins/brain-prompt
```

### OpenClaw 配置示例

> 路径请按你的机器实际情况调整。

```json5
{
  hooks: {
    "brain-ingest": {
      enabled: true,
      attention_threshold: 0.7,
      auto_consolidate: true,
      consolidation_interval: 100,
      extract_knowledge: true
    }
  },
  plugins: {
    entries: {
      brainPrompt: {
        enabled: true,
        kind: "path",
        path: "<absolute-path-to>/openclaw-brain/plugins/brain-prompt",
        hooks: {
          allowPromptInjection: true
        },
        config: {
          enabled: true,
          backend: "jsonl",
          limit: 5,
          recentWindow: 8,
          minQueryLength: 2,
          heading: "[Brain Recall]"
        }
      }
    }
  }
}
```

---

## 6. 后端选择

### JSONL 后端
适合：
- 本地查看方便
- 手动备份简单
- 依赖少
- 调试更省事

### LanceDB 后端
适合：
- 更大规模数据
- 未来向量检索
- 向语义搜索架构演进

---

## 7. 平台差异说明

### Windows
- 推荐使用 PowerShell 或配置正常的终端
- JSON 配置中的反斜杠路径要注意转义
- 如果激活虚拟环境被策略拦住，可以先执行：

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```

- 如果 `python` 指向微软商店占位符，用 `py` 或完整 Python 路径

### Linux
- 确保 `python3` 和 `pip` 对应的是同一个解释器
- 适合做 cron 触发的巩固 / 维护任务
- 如果记忆文件包含敏感信息，注意文件权限

### macOS
- 通常优先使用 `python3`
- 如果使用 Homebrew Python，确认 PATH 指向的是正确解释器
- 很适合本地桌面式 OpenClaw 使用场景

---

## 8. 升级流程

升级项目时建议按这个顺序来：

1. 先备份持久化目录
2. 再拉新代码
3. 如有需要重新安装依赖
4. 跑 `python verify.py`
5. 最后再切换正在运行的 OpenClaw 配置

别反着来，不然容易自己给自己挖坑。

---

## 9. 备份与恢复

### 最低备份集
- 持久化目录（JSONL 文件或 LanceDB 目录）
- 引用本项目的 OpenClaw 配置片段

### 恢复思路
- 恢复持久化目录
- 恢复 OpenClaw 配置
- 再跑一遍 `python verify.py`

---

## 10. 常见问题排查

### Plugin 导入失败
检查：
- Node.js 是否已安装
- `plugins/brain-prompt/package.json` 是否存在
- OpenClaw 配置里的 plugin 路径是否正确

### Brain CLI 调用失败
检查：
- Python 是否已安装并在 `PATH` 中
- Python 依赖是否安装完整
- 项目路径是否正确

### 没有生成记忆文件
检查：
- hook / plugin 是否真的启用了
- OpenClaw 是否提供了 `workspace.dir`
- attention threshold 是否设得太苛刻

### Recall block 为空
检查：
- 是否先有消息 / 工具写入记忆
- 重复抑制是不是把有用内容全过滤了
- query 长度是否高于 `minQueryLength`

---

## 11. 更像生产环境的建议

- 持久化目录单独放到数据目录下
- 做结构性改动前先备份记忆数据
- 出现奇怪问题时，优先用 JSONL 调试，再切 LanceDB
- 把真实部署路径写进你的仓库文档或运维说明里
- 没在目标系统上跑过之前，别嘴硬说自己“跨平台支持”
