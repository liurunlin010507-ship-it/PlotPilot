"""LLM 侧契约：结构化输出解析、校验与（可选）function-calling schema。"""

from application.ai.chapter_state_llm_contract import (
    ChapterStateLlmPayload,
    CHAPTER_STATE_SYSTEM_FALLBACK,
    chapter_state_openai_function_tool,
    chapter_state_payload_to_domain,
    empty_chapter_state,
)
from application.ai.knowledge_llm_contract import (
    INITIAL_KNOWLEDGE_SYSTEM_FALLBACK,
    LlmInitialKnowledgeFact,
    LlmInitialKnowledgePayload,
    initial_knowledge_openai_function_tool,
    to_knowledge_service_update_dict,
)
from application.ai.llm_json_extract import (
    extract_outer_json_object,
    parse_llm_json_to_dict,
    strip_json_fences,
)

__all__ = [
    "CHAPTER_STATE_SYSTEM_FALLBACK",
    "ChapterStateLlmPayload",
    "INITIAL_KNOWLEDGE_SYSTEM_FALLBACK",
    "LlmInitialKnowledgeFact",
    "LlmInitialKnowledgePayload",
    "chapter_state_openai_function_tool",
    "chapter_state_payload_to_domain",
    "empty_chapter_state",
    "extract_outer_json_object",
    "initial_knowledge_openai_function_tool",
    "parse_llm_json_to_dict",
    "strip_json_fences",
    "to_knowledge_service_update_dict",
]
