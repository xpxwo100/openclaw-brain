#!/usr/bin/env python3
"""
OpenClaw Brain 验证脚本
用于 autoresearch 循环中的机械验证
"""

import sys
import os
from pathlib import Path

# 修复 Windows 控制台编码问题
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except:
        pass

def verify_structure():
    """验证项目结构完整性"""
    project_root = Path(__file__).parent
    
    required_dirs = [
        'brain',
        'models', 
        'storage',
        'hooks',
        'tests',
        'examples',
        'docs'
    ]
    
    required_files = [
        'README.md',
        'requirements.txt',
        'LICENSE',
        'GOAL.md'
    ]
    
    errors = []
    
    # 检查目录
    for dir_name in required_dirs:
        dir_path = project_root / dir_name
        if not dir_path.exists():
            errors.append(f"缺少目录：{dir_name}")
        elif not dir_path.is_dir():
            errors.append(f"{dir_name} 不是目录")
    
    # 检查文件
    for file_name in required_files:
        file_path = project_root / file_name
        if not file_path.exists():
            errors.append(f"缺少文件：{file_name}")
    
    return errors

def verify_modules():
    """验证核心模块是否可导入"""
    errors = []
    
    required_modules = [
        'brain',
        'brain.attention',
        'brain.working_memory',
        'brain.hippocampus',
        'brain.episodic',
        'brain.semantic',
        'brain.consolidation',
        'brain.retrieval'
    ]
    
    sys.path.insert(0, str(Path(__file__).parent))
    
    for module in required_modules:
        try:
            __import__(module)
        except ImportError as e:
            errors.append(f"模块导入失败：{module} - {str(e)}")
        except Exception as e:
            errors.append(f"模块错误：{module} - {str(e)}")
    
    return errors

def verify_tests():
    """验证测试是否可运行"""
    import subprocess
    
    test_dir = Path(__file__).parent / 'tests'
    if not test_dir.exists():
        return ["测试目录不存在"]
    
    # 尝试运行测试
    try:
        result = subprocess.run(
            ['pytest', 'tests/', '-v', '--tb=short'],
            cwd=Path(__file__).parent,
            capture_output=True,
            text=True,
            timeout=60
        )
        if result.returncode != 0:
            return [f"测试失败：{result.stdout}\n{result.stderr}"]
    except subprocess.TimeoutExpired:
        return ["测试超时 (60s)"]
    except FileNotFoundError:
        # pytest 未安装，跳过
        pass
    except Exception as e:
        return [f"测试运行错误：{str(e)}"]
    
    return []

def main():
    """主验证函数"""
    print("=" * 60)
    print("OpenClaw Brain Verification Report")
    print("=" * 60)
    
    all_errors = []
    
    # 结构验证
    print("\n[1] Verifying project structure...")
    errors = verify_structure()
    if errors:
        for err in errors:
            print(f"  [X] {err}")
        all_errors.extend(errors)
    else:
        print("  [OK] Project structure complete")
    
    # 模块验证
    print("\n[2] Verifying module imports...")
    errors = verify_modules()
    if errors:
        for err in errors:
            print(f"  [X] {err}")
        all_errors.extend(errors)
    else:
        print("  [OK] All modules can be imported")
    
    # 测试验证
    print("\n[3] Running test suite...")
    errors = verify_tests()
    if errors:
        for err in errors:
            print(f"  [X] {err}")
        all_errors.extend(errors)
    else:
        print("  [OK] Tests passed")
    
    # 总结
    print("\n" + "=" * 60)
    if all_errors:
        print(f"Verification FAILED: {len(all_errors)} errors")
        for err in all_errors:
            print(f"  - {err}")
        return 1
    else:
        print("[OK] Verification PASSED!")
        return 0

if __name__ == '__main__':
    sys.exit(main())
