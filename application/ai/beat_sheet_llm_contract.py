"""节拍表（Beat Sheet）：LLM JSON 契约、解析校验与 OpenAI-style tool 定义。

设计要点（与 knowledge_llm_contract / chapter_state_llm_contract 同源）：
- Pydantic 模型 + extra='forbid' 严格约束 LLM 输出结构
- parse_xxx / payload_to_domain / response_format / openai_function_tool 四件套
- 日后 provider 支持 function calling 时，可直接把
  beat_sheet_openai_function_tool() 交给网关
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field

from domain.novel.value_objects.scene import Scene


# ---------------------------------------------------------------------------
# 与 LLM 约定的响应形状
# ---------------------------------------------------------------------------


class LlmBeatScene(BaseModel):
    """节拍表中单个场景的 LLM 输出形状。"""

    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1, max_length=200, description="场景标题")
    goal: str = Field(min_length=1, max_length=1000, description="场景目标")
    pov_character: str = Field(
        min_length=1, max_length=200, description="POV 角色名称",
    )
    location: Optional[str] = Field(
        default=None, max_length=200, description="地点（可选）",
    )
    tone: str = Field(default="", max_length=100, description="情绪基调")
    estimated_words: int = Field(
        gt=0, le=10000, description="预估字数",
    )


class BeatSheetLlmPayload(BaseModel):
    """节拍表 LLM 响应根对象。

    仅允许一个字段：scenes（场景列表）。
    """

    model_config = ConfigDict(extra="forbid")

    scenes: List[LlmBeatScene] = Field(
        default_factory=list,
        max_length=50,
        description="场景列表",
    )


def beat_sheet_payload_to_domain(
    payload: BeatSheetLlmPayload,
) -> List[Scene]:
    """将校验后的 payload 转为 Scene 领域值对象列表。"""
    scenes: List[Scene] = []
    for idx, s in enumerate(payload.scenes):
        scenes.append(
            Scene(
                title=s.title,
                goal=s.goal,
                pov_character=s.pov_character,
                location=s.location,
                tone=s.tone or None,
                estimated_words=s.estimated_words,
                order_index=idx,
            )
        )
    return scenes


# ---------------------------------------------------------------------------
# response_format 构建器（供 GenerationConfig 使用）
# ---------------------------------------------------------------------------


def beat_sheet_response_format() -> Dict[str, Any]:
    """构建 Anthropic API 的 response_format 参数，强制 LLM 按契约输出 JSON。"""
    return {
        "type": "json_schema",
        "json_schema": {
            "name": "beat_sheet",
            "description": (
                "节拍表：包含场景列表，每个场景有标题、目标、POV 角色、"
                "地点、情绪基调及预估字数。"
            ),
            "schema": BeatSheetLlmPayload.model_json_schema(mode="validation"),
            "strict": True,
        },
    }


# ---------------------------------------------------------------------------
# OpenAI function tool 定义（预留）
# ---------------------------------------------------------------------------


def beat_sheet_openai_function_tool() -> Dict[str, Any]:
    """可选：接入 function calling 时使用。"""
    schema = BeatSheetLlmPayload.model_json_schema(mode="validation")
    return {
        "type": "function",
        "function": {
            "name": "submit_beat_sheet",
            "description": (
                "提交节拍表：包含场景列表，每个场景有标题、目标、POV 角色、"
                "地点、情绪基调及预估字数。"
            ),
            "parameters": schema,
        },
    }
