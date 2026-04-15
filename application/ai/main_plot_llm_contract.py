"""主线情节建议：LLM JSON 契约、解析校验与 OpenAI-style tool 定义。

设计要点（与 knowledge_llm_contract / chapter_state_llm_contract 同源）：
- Pydantic 模型 + extra='forbid' 严格约束 LLM 输出结构
- parse_xxx / payload_to_domain / response_format / openai_function_tool 四件套
- 日后 provider 支持 function calling 时，可直接把
  main_plot_openai_function_tool() 交给网关
"""
from __future__ import annotations

from typing import Any, Dict, List

from pydantic import BaseModel, ConfigDict, Field


# ---------------------------------------------------------------------------
# 与 LLM 约定的响应形状
# ---------------------------------------------------------------------------


class LlmPlotOption(BaseModel):
    """单条主线情节选项。"""

    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1, max_length=64, description="选项唯一标识")
    type: str = Field(min_length=1, max_length=64, description="情节类型")
    title: str = Field(
        min_length=1, max_length=16, description="情节标题（8-16 字）",
    )
    logline: str = Field(
        min_length=1, max_length=500, description="一句话梗概",
    )
    core_conflict: str = Field(
        min_length=1, max_length=500, description="核心冲突",
    )
    starting_hook: str = Field(
        min_length=1, max_length=500, description="开篇钩子",
    )


class MainPlotLlmPayload(BaseModel):
    """主线情节建议 LLM 响应根对象。

    仅允许一个字段：plot_options（恰好 3 个选项）。
    """

    model_config = ConfigDict(extra="forbid")

    plot_options: List[LlmPlotOption] = Field(
        min_length=3,
        max_length=3,
        description="主线情节选项列表（恰好 3 个）",
    )


def main_plot_payload_to_domain(
    payload: MainPlotLlmPayload,
) -> List[Dict[str, Any]]:
    """将校验后的 payload 转为字典列表（供上层消费）。"""
    return [opt.model_dump() for opt in payload.plot_options]


# ---------------------------------------------------------------------------
# response_format 构建器（供 GenerationConfig 使用）
# ---------------------------------------------------------------------------


def main_plot_response_format() -> Dict[str, Any]:
    """构建 Anthropic API 的 response_format 参数，强制 LLM 按契约输出 JSON。"""
    return {
        "type": "json_schema",
        "json_schema": {
            "name": "main_plot",
            "description": (
                "主线情节建议：恰好 3 个情节选项，每个包含 id、类型、标题、"
                "一句话梗概、核心冲突和开篇钩子。"
            ),
            "schema": MainPlotLlmPayload.model_json_schema(mode="validation"),
            "strict": True,
        },
    }


# ---------------------------------------------------------------------------
# OpenAI function tool 定义（预留）
# ---------------------------------------------------------------------------


def main_plot_openai_function_tool() -> Dict[str, Any]:
    """可选：接入 function calling 时使用。"""
    schema = MainPlotLlmPayload.model_json_schema(mode="validation")
    return {
        "type": "function",
        "function": {
            "name": "submit_main_plot",
            "description": (
                "提交主线情节建议：恰好 3 个情节选项，每个包含 id、类型、标题、"
                "一句话梗概、核心冲突和开篇钩子。"
            ),
            "parameters": schema,
        },
    }
