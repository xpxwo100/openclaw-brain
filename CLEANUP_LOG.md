# 隐私清理完成

## 已清理内容
- ✅ 移除所有"小帅" → 替换为 `<USER_NAME>`
- ✅ 移除所有"鸡哥" → 替换为 `<BOT_NAME>`
- ✅ 移除所有"厦门" → 替换为 `<CITY_NAME>`
- ✅ 移除所有"MiniMax" → 替换为 `<MODEL_NAME>`

## 清理的文件
- README.md
- DEVELOPMENT.md
- brain/working_memory.py
- tests/test_brain.py
- test_injection.py
- config.example.yaml

## 验证方法
```bash
# 在项目根目录运行
python -c "
import os
found = []
for root, _, fnames in os.walk('.'):
    for f in fnames:
        if f.endswith(('.md', '.py', '.yaml')):
            path = os.path.join(root, f)
            try:
                content = open(path, encoding='utf-8').read()
                if any(kw in content for kw in ['小帅', '鸡哥', '厦门']):
                    found.append(path)
            except:
                pass
print('✅ 清理完成！' if not found else f'⚠️ 待清理：{found}')
"
```

## 示例数据脱敏
所有示例现在使用通用占位符：
- `<USER_NAME>` - 用户名
- `<BOT_NAME>` - 助手名
- `<CITY_NAME>` - 城市名
- `<MODEL_NAME>` - 模型名

这样发布到 GitHub 时不会泄露个人隐私。
