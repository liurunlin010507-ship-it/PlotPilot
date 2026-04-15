from application.ai.chapter_state_llm_contract import (
    ChapterStateLlmPayload,
    chapter_state_openai_function_tool,
    chapter_state_payload_to_domain,
    empty_chapter_state,
)
from application.ai.structured_json_pipeline import (
    sanitize_llm_output,
    parse_and_repair_json,
    validate_json_schema,
)


def _parse(raw: str):
    """解析 + 校验（复用管线组件）。"""
    cleaned = sanitize_llm_output(raw)
    data, errs = parse_and_repair_json(cleaned)
    if data is None:
        return None, errs
    return validate_json_schema(data, ChapterStateLlmPayload)


def test_parse_valid():
    raw = '{"new_characters": [], "character_actions": [], "relationship_changes": [], "foreshadowing_planted": [], "foreshadowing_resolved": [], "events": []}'
    p, errs = _parse(raw)
    assert errs == []
    assert p is not None
    st = chapter_state_payload_to_domain(p)
    assert st.new_characters == []


def test_rejects_extra_root_key():
    raw = (
        '{"new_characters": [], "character_actions": [], "relationship_changes": [], '
        '"foreshadowing_planted": [], "foreshadowing_resolved": [], "events": [], "extra": 1}'
    )
    p, errs = _parse(raw)
    assert p is None
    assert errs


def test_empty_chapter_state():
    st = empty_chapter_state()
    assert st.new_characters == [] and st.events == []


def test_openai_tool_shape():
    t = chapter_state_openai_function_tool()
    assert t["function"]["name"] == "submit_chapter_state_extraction"
    assert "properties" in t["function"]["parameters"]
