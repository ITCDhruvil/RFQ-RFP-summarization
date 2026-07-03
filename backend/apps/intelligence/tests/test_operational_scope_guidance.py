from apps.intelligence.prompts.templates import (
    build_operational_scope_guidance,
    summary_user_prompt,
)


def test_guidance_when_operational_extractions_present():
    extractions = {
        "scope_of_work": {
            "items": [
                {
                    "requirement": "Deploy ~275 security personnel for transport escort in Bangalore and Chennai."
                }
            ]
        },
        "technical_requirements": {"items": []},
    }
    guidance = build_operational_scope_guidance(extractions)
    assert "CRITICAL" in guidance
    assert "275" in guidance
    assert "absent" in guidance.lower()


def test_guidance_when_operational_extractions_empty():
    guidance = build_operational_scope_guidance({})
    assert "empty" in guidance.lower()
    assert "CRITICAL" not in guidance


def test_summary_user_prompt_includes_scope_guidance():
    import json

    payload = {
        "scope_of_work": {
            "items": [{"requirement": "24x7 guarding and transport escort services."}]
        }
    }
    prompt = summary_user_prompt(json.dumps(payload), "Security RFP.docx")
    assert "CRITICAL" in prompt
    assert "transport escort" in prompt
