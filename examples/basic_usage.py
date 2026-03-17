from brain import OpenClawBrain


if __name__ == "__main__":
    brain = OpenClawBrain(attention_threshold=0.4)

    brain.remember("记住，用户喜欢被叫鸡哥", context={"kind": "preference", "source": "profile"})
    brain.remember("今天修好了 openclaw-brain 的测试", context={"source": "devlog"})
    brain.remember("规则：改配置前先备份", context={"kind": "rule", "definition": "任何配置改动前必须先备份"})

    print("Recall: 鸡哥")
    for result in brain.recall("鸡哥", limit=5):
        print(f"- {result.memory.content} | score={result.score.total():.3f}")

    print("\nConsolidation:")
    print(brain.consolidate())
