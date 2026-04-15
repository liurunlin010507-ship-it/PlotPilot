"""张力分析器：LLM JSON 契约、解析校验与 OpenAI-style tool 定义。

设计要点（与 knowledge_llm_contract / chapter_state_llm_contract 同源）：
- Pydantic 模型 + extra='forbid' 严格约束 LLM 输出结构
- parse_xxx / payload_to_domain / response_format / openai_function_tool 四件套
- 日后 provider 支持 function calling 时，可直接把
  tension_analyzer_openai_function_tool() 交给网关
"""
from __future__ import annotations

from typing import Any, Dict, List, Literal

from pydantic import BaseModel, ConfigDict, Field

from application.workbench.dtos.writer_block_dto import TensionDiagnosis


# ---------------------------------------------------------------------------
# 与 LLM 约定的响应形状
# ---------------------------------------------------------------------------


class TensionAnalyzerLlmPayload(BaseModel):
    """张力分析器 LLM 响应根对象。

    仅允许四个字段：diagnosis / tension_level / missing_elements / suggestions。
    """

    model_config = ConfigDict(extra="forbid")

    diagnosis: str = Field(
        default="",
        max_length=2000,
        description="张力诊断描述（2-3 句话）",
    )
    tension_level: Literal["low", "medium", "high"] = Field(
        default="medium",
        description="张力等级：low | medium | high",
    )
    missing_elements: List[str] = Field(
        default_factory=list,
        description="缺失的张力元素列表",
    )
    suggestions: List[str] = Field(
        default_factory=list,
        description="改进建议列表",
    )


def tension_analyzer_payload_to_domain(
    payload: TensionAnalyzerLlmPayload,
) -> TensionDiagnosis:
    """将校验后的 payload 转为领域 DTO。"""
    return TensionDiagnosis(
        diagnosis=payload.diagnosis,
        tension_level=payload.tension_level,
        missing_elements=list(payload.missing_elements),
        suggestions=list(payload.suggestions),
    )


# ---------------------------------------------------------------------------
# response_format 构建器（供 GenerationConfig 使用）
# ---------------------------------------------------------------------------


def tension_analyzer_response_format() -> Dict[str, Any]:
    """构建 Anthropic API 的 response_format 参数，强制 LLM 按契约输出 JSON。"""
    return {
        "type": "json_schema",
        "json_schema": {
            "name": "tension_analyzer",
            "description": (
                "张力分析器：诊断当前段落的张力水平、缺失元素及改进建议。"
            ),
            "schema": TensionAnalyzerLlmPayload.model_json_schema(mode="validation"),
            "strict": True,
        },
    }


# ---------------------------------------------------------------------------
# OpenAI function tool 定义（预留）
# ---------------------------------------------------------------------------


def tension_analyzer_openai_function_tool() -> Dict[str, Any]:
    """可选：接入 function calling 时使用。"""
    schema = TensionAnalyzerLlmPayload.model_json_schema(mode="validation")
    return {
        "type": "function",
        "function": {
            "name": "submit_tension_analyzer",
            "description": (
                "提交张力分析结果：诊断描述、张力等级（low/medium/high）、"
                "缺失元素及改进建议。"
            ),
            "parameters": schema,
        },
    }
