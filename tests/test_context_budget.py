from brain import OpenClawBrain


def test_build_context_respects_character_and_token_budget():
    brain = OpenClawBrain(attention_threshold=0.1)
    brain.remember(
        "user prefers being called Chicken Bro",
        context={"kind": "preference", "definition": "user prefers being called Chicken Bro", "source": "profile"},
        importance=0.95,
        mode="semantic",
    )
    brain.remember(
        "backup before changing config",
        context={"kind": "rule", "definition": "backup before changing config in production", "source": "ops"},
        importance=0.9,
        mode="semantic",
    )
    brain.remember(
        "current state is gateway now writes memory to LanceDB and recall uses vector prefilter",
        context={"kind": "summary", "definition": "gateway now writes memory to LanceDB and recall uses vector prefilter", "source_subtype": "assistant_state_summary"},
        importance=0.98,
        mode="semantic",
    )

    result = brain.build_context(
        query="what should I remember about the user and current status",
        limit=5,
        max_chars=120,
        max_estimated_tokens=40,
    )

    assert result["count"] >= 1
    assert result["context_chars"] <= 120
    assert result["estimated_tokens"] <= 40

