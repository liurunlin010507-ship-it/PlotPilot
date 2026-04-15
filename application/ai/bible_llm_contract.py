"""世界观设定（Bible）生成：LLM JSON 契约、解析校验与 OpenAI-style tool 定义。

包含 4 个 Bible 生成节点对应的 Pydantic 模型：
- BibleAllLlmPayload        全量生成
- BibleWorldbuildingLlmPayload  世界观子集
- BibleCharactersLlmPayload     角色子集
- BibleLocationsLlmPayload      地点子集

设计要点（与 knowledge_llm_contract / chapter_state_llm_contract 同源）：
- Pydantic 模型 + extra='forbid' 严格约束 LLM 输出结构
- 每个 payload 提供 parse / response_format / openai_function_tool
- payload_to_domain 返回已校验的 dict（auto_bible_generator 直接消费 dict）
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


# ---------------------------------------------------------------------------
# 通用构建辅助
# ---------------------------------------------------------------------------


def _make_response_format(
    name: str,
    description: str,
    model_cls: type[BaseModel],
) -> Dict[str, Any]:
    """通用 response_format 构建器。"""
    return {
        "type": "json_schema",
        "json_schema": {
            "name": name,
            "description": description,
            "schema": model_cls.model_json_schema(mode="validation"),
            "strict": True,
        },
    }


def _make_function_tool(
    function_name: str,
    description: str,
    model_cls: type[BaseModel],
) -> Dict[str, Any]:
    """通用 OpenAI function tool 构建器。"""
    schema = model_cls.model_json_schema(mode="validation")
    return {
        "type": "function",
        "function": {
            "name": function_name,
            "description": description,
            "parameters": schema,
        },
    }


# ---------------------------------------------------------------------------
# 嵌套模型（各 Bible payload 共用）
# ---------------------------------------------------------------------------


class LlmCharacter(BaseModel):
    """角色条目。"""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=200, description="角色名称")
    role: str = Field(default="", max_length=100, description="角色定位")
    description: str = Field(default="", max_length=4000, description="角色描述")
    relationships: Optional[List[Dict[str, Any]]] = Field(
        default=None,
        description="角色关系列表（可选，角色子集生成时使用）",
    )


class LlmLocation(BaseModel):
    """地点条目。"""

    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1, max_length=64, description="地点 ID")
    name: str = Field(min_length=1, max_length=200, description="地点名称")
    type: str = Field(default="", max_length=100, description="地点类型")
    description: str = Field(default="", max_length=4000, description="地点描述")
    parent_id: Optional[str] = Field(
        default=None, max_length=64, description="父级地点 ID（可选）",
    )
    connections: List[Dict[str, Any]] = Field(
        default_factory=list, description="连接关系列表",
    )


# ---------------------------------------------------------------------------
# BibleAllLlmPayload — 全量生成
# ---------------------------------------------------------------------------


class BibleAllLlmPayload(BaseModel):
    """全量 Bible 生成 LLM 响应根对象。

    包含 characters / locations / style / worldbuilding 四个顶层字段。
    """

    model_config = ConfigDict(extra="forbid")

    characters: List[LlmCharacter] = Field(
        default_factory=list, max_length=100, description="角色列表",
    )
    locations: List[LlmLocation] = Field(
        default_factory=list, max_length=100, description="地点列表",
    )
    style: str = Field(default="", max_length=4000, description="文风描述")
    worldbuilding: Dict[str, Any] = Field(
        default_factory=dict,
        description="世界观设定（core_rules / geography / society / culture / daily_life）",
    )


def bible_all_payload_to_domain(payload: BibleAllLlmPayload) -> Dict[str, Any]:
    """将校验后的 payload 转为 dict（auto_bible_generator 直接消费）。"""
    return payload.model_dump()


def bible_all_response_format() -> Dict[str, Any]:
    """构建全量 Bible 生成的 response_format。"""
    return _make_response_format(
        "bible_all",
        "全量世界观设定生成：角色、地点、文风与世界观。",
        BibleAllLlmPayload,
    )


def bible_all_openai_function_tool() -> Dict[str, Any]:
    """可选：接入 function calling 时使用。"""
    return _make_function_tool(
        "submit_bible_all",
        "提交全量世界观设定：角色、地点、文风与世界观。",
        BibleAllLlmPayload,
    )


# ---------------------------------------------------------------------------
# BibleWorldbuildingLlmPayload — 世界观子集
# ---------------------------------------------------------------------------


class BibleWorldbuildingLlmPayload(BaseModel):
    """世界观子集 LLM 响应根对象。

    仅包含 style / worldbuilding 两个字段。
    """

    model_config = ConfigDict(extra="forbid")

    style: str = Field(default="", max_length=4000, description="文风描述")
    worldbuilding: Dict[str, Any] = Field(
        default_factory=dict,
        description="世界观设定（core_rules / geography / society / culture / daily_life）",
    )


def bible_worldbuilding_payload_to_domain(
    payload: BibleWorldbuildingLlmPayload,
) -> Dict[str, Any]:
    """将校验后的 payload 转为 dict。"""
    return payload.model_dump()


def bible_worldbuilding_response_format() -> Dict[str, Any]:
    """构建世界观子集生成的 response_format。"""
    return _make_response_format(
        "bible_worldbuilding",
        "世界观设定子集：文风与世界观。",
        BibleWorldbuildingLlmPayload,
    )


def bible_worldbuilding_openai_function_tool() -> Dict[str, Any]:
    """可选：接入 function calling 时使用。"""
    return _make_function_tool(
        "submit_bible_worldbuilding",
        "提交世界观设定子集：文风与世界观。",
        BibleWorldbuildingLlmPayload,
    )


# ---------------------------------------------------------------------------
# BibleCharactersLlmPayload — 角色子集
# ---------------------------------------------------------------------------


class BibleCharactersLlmPayload(BaseModel):
    """角色子集 LLM 响应根对象。

    仅包含 characters 字段（每项可附带 relationships）。
    """

    model_config = ConfigDict(extra="forbid")

    characters: List[LlmCharacter] = Field(
        default_factory=list, max_length=100, description="角色列表",
    )


def bible_characters_payload_to_domain(
    payload: BibleCharactersLlmPayload,
) -> Dict[str, Any]:
    """将校验后的 payload 转为 dict。"""
    return payload.model_dump()


def bible_characters_response_format() -> Dict[str, Any]:
    """构建角色子集生成的 response_format。"""
    return _make_response_format(
        "bible_characters",
        "角色设定子集：角色列表（含关系）。",
        BibleCharactersLlmPayload,
    )


def bible_characters_openai_function_tool() -> Dict[str, Any]:
    """可选：接入 function calling 时使用。"""
    return _make_function_tool(
        "submit_bible_characters",
        "提交角色设定子集：角色列表（含关系）。",
        BibleCharactersLlmPayload,
    )


# ---------------------------------------------------------------------------
# BibleLocationsLlmPayload — 地点子集
# ---------------------------------------------------------------------------


class BibleLocationsLlmPayload(BaseModel):
    """地点子集 LLM 响应根对象。

    仅包含 locations 字段。
    """

    model_config = ConfigDict(extra="forbid")

    locations: List[LlmLocation] = Field(
        default_factory=list, max_length=100, description="地点列表",
    )


def bible_locations_payload_to_domain(
    payload: BibleLocationsLlmPayload,
) -> Dict[str, Any]:
    """将校验后的 payload 转为 dict。"""
    return payload.model_dump()


def bible_locations_response_format() -> Dict[str, Any]:
    """构建地点子集生成的 response_format。"""
    return _make_response_format(
        "bible_locations",
        "地点设定子集：地点列表（含层级与连接关系）。",
        BibleLocationsLlmPayload,
    )


def bible_locations_openai_function_tool() -> Dict[str, Any]:
    """可选：接入 function calling 时使用。"""
    return _make_function_tool(
        "submit_bible_locations",
        "提交地点设定子集：地点列表（含层级与连接关系）。",
        BibleLocationsLlmPayload,
    )
