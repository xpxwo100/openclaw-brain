# OpenClaw Brain 项目构建配置

## Goal (目标)
构建一个完整的、可发布到 GitHub 的 OpenClaw Brain 项目，实现类脑记忆系统。

## Scope (范围)

### 可修改文件 (Writable)
- `C:\Users\Administrator.xpxwo\.openclaw\workspace\projects\openclaw-brain\**`

### 只读文件 (Read-only)
- 当前 OpenClaw 配置
- 其他项目文件

## Metric (度量标准)

### 主要指标
1. **模块完整性**: 7 个核心模块全部实现并可导入
2. **测试通过率**: pytest 测试 100% 通过
3. **文档完整性**: README 包含安装、用法、API 说明

### 验证方式
```bash
# 1. 验证模块可导入
python -c "from brain import AttentionGate, WorkingMemory, Hippocampus"

# 2. 运行测试
pytest tests/ -v

# 3. 检查文件结构
tree /F /A
```

## Verification (验证脚本)

每次迭代后运行：
1. 检查模块是否可导入
2. 运行现有测试
3. 验证文件结构完整性

## Constraints (约束)
- 不修改 OpenClaw 核心代码
- 不配置到当前运行实例
- 保持项目独立性
- 使用 MIT License

## Iteration Rules (迭代规则)
1. 每次迭代只做一个原子性修改
2. 修改前必须运行验证
3. 如果验证失败，回滚并尝试更小改动
4. 记录每次迭代的结果到 `iterations.log`

## Success Criteria (成功标准)
- [ ] 7 个核心模块全部实现
- [ ] 测试覆盖率 > 80%
- [ ] README 完整
- [ ] 可以 pip install
- [ ] 示例代码可运行
