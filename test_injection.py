"""
测试记忆注入逻辑
"""

from brain import AttentionGate, Hippocampus, MemoryRetriever

def test_injection():
    """测试记忆注入是否正常工作"""
    # 初始化组件
    gate = AttentionGate()
    retriever = MemoryRetriever()
    
    # 测试消息
    test_message = "我叫什么名字？"
    
    # 测试检索（应该返回空，因为还没有记忆）
    memories = retriever.remember(test_message, limit=3)
    
    if not memories:
        print("✅ 测试通过：记忆系统为空（正常）")
    else:
        print(f"ℹ️  检索到 {len(memories)} 条记忆")
        for mem in memories:
            print(f"  - {mem.content}")
    
    # 测试注意力门控
    should_remember = gate.should_pass("记住，这是重要信息")
    print(f"✅ 注意力门控测试：{should_remember}")

if __name__ == '__main__':
    test_injection()
