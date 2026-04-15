"""宏观重构提案：LLM JSON 契约、解析校验与 OpenAI-style tool 定义。

设计要点（与 knowledge_llm_contract / chapter_state_llm_contract 同源）：
- Pydantic 模型 + extra='forbid' 严格约束 LLM 输出结构
- parse_xxx / payload_to_domain / response_format / openai_function_tool 四件套
- 日后 provider 支持 function calling 时，可直接把
  refactor_proposal_openai_function_tool() 交给网关
"""
from __future__ import annotations

from typing import Any, Dict, List, Literal

from pydantic import BaseModel, ConfigDict, Field

from application.audit.dtos.macro_refactor_dto import RefactorProposal


# ---------------------------------------------------------------------------
# 与 LLM 约定的响应形状
# ---------------------------------------------------------------------------


class LlmMutation(BaseModel):
    """单条 mutation：type + tag，以及可选的 old/new 值。"""

    model_config = ConfigDict(extra="forbid")

    type: Literal["add_tag", "remove_tag", "replace_tag"] = Field(
        description="mutation 类型：add_tag | remove_tag | replace_tag"
    )
    tag: str = Field(default="", description="目标标签")
    old: str = Field(default="", description="被替换的旧值（replace_tag 时使用）")
    new: str = Field(default="", description="替换后的新值（replace_tag 时使用）")


class RefactorProposalLlmPayload(BaseModel):
    """重构提案 LLM 响应根对象。

    仅允许四个字段：natural_language_suggestion / suggested_mutations /
    suggested_tags / reasoning。
    """

    model_config = ConfigDict(extra="forbid")

    natural_language_suggestion: str = Field(
        default="", max_length=4000, description="自然语言重构建议",
    )
    suggested_mutations: List[LlmMutation] = Field(
        default_factory=list, description="建议的标签 mutations",
    )
    suggested_tags: List[str] = Field(
        default_factory=list, description="建议的新标签列表",
    )
    reasoning: str = Field(
        default="", max_length=4000, description="推理过程",
    )


def refactor_proposal_payload_to_domain(
    payload: RefactorProposalLlmPayload,
) -> RefactorProposal:
    """将校验后的 payload 转为领域 DTO。"""
    return RefactorProposal(
        natural_language_suggestion=payload.natural_language_suggestion,
        suggested_mutations=[m.model_dump() for m in payload.suggested_mutations],
        suggested_tags=list(payload.suggested_tags),
        reasoning=payload.reasoning,
    )


# ---------------------------------------------------------------------------
# response_format 构建器（供 GenerationConfig 使用）
# ---------------------------------------------------------------------------


def refactor_proposal_response_format() -> Dict[str, Any]:
    """构建 Anthropic API 的 response_format 参数，强制 LLM 按契约输出 JSON。"""
    return {
        "type": "json_schema",
        "json_schema": {
            "name": "refactor_proposal",
            "description": (
                "宏观重构提案：自然语言建议、标签 mutations、建议标签及推理过程。"
            ),
            "schema": RefactorProposalLlmPayload.model_json_schema(mode="validation"),
            "strict": True,
        },
    }


# ---------------------------------------------------------------------------
# OpenAI function tool 定义（预留）
# ---------------------------------------------------------------------------


def refactor_proposal_openai_function_tool() -> Dict[str, Any]:
    """可选：接入 function calling 时使用。"""
    schema = RefactorProposalLlmPayload.model_json_schema(mode="validation")
    return {
        "type": "function",
        "function": {
            "name": "submit_refactor_proposal",
            "description": (
                "提交宏观重构提案：自然语言建议、标签 mutations、建议标签及推理过程。"
            ),
            "parameters": schema,
        },
    }
