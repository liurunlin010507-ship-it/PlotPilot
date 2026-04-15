"""提示词广场 API (Phase 1 — 本地管理版)。

提供模板包列表、节点查询、覆盖激活/取消、schema 查询等端点。
"""
from __future__ import annotations

import importlib
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from infrastructure.ai.prompt_template_loader import PromptTemplateLoader

router = APIRouter(prefix="/prompts", tags=["prompts"])


def _get_loader() -> PromptTemplateLoader:
    return PromptTemplateLoader.get_instance()


def _get_registry():
    return _get_loader().registry


class OverrideRequest(BaseModel):
    """节点覆盖请求体。"""
    node_name: str = Field(min_length=1, description="要覆盖的节点名称")
    pack_id: str = Field(min_length=1, description="目标模板包 ID")


# ------------------------------------------------------------------
# 包管理
# ------------------------------------------------------------------


@router.get("/packs", summary="列出所有已注册模板包")
def list_packs() -> List[Dict[str, Any]]:
    registry = _get_registry()
    return [
        {
            "pack_id": p.pack_id,
            "name": p.name,
            "version": p.version,
            "author": p.author,
            "description": p.description,
            "category": p.category,
            "template_nodes": p.template_nodes,
        }
        for p in registry.list_packs()
    ]


@router.get("/packs/{pack_id}", summary="获取模板包详情")
def get_pack(pack_id: str) -> Dict[str, Any]:
    registry = _get_registry()
    packs = registry.list_packs()
    for p in packs:
        if p.pack_id == pack_id:
            return {
                "pack_id": p.pack_id,
                "name": p.name,
                "version": p.version,
                "author": p.author,
                "description": p.description,
                "category": p.category,
                "template_nodes": p.template_nodes,
                "installed_at": p.installed_at,
            }
    raise HTTPException(status_code=404, detail=f"模板包 '{pack_id}' 未找到")


# ------------------------------------------------------------------
# 节点查询
# ------------------------------------------------------------------


@router.get("/nodes", summary="列出所有 prompt 节点")
def list_nodes() -> List[Dict[str, Any]]:
    loader = _get_loader()
    registry = _get_registry()
    result = []
    for node_name in loader.list_nodes():
        meta = registry.get_node_meta(node_name)
        active_pack = registry.get_active_pack(node_name)
        entry: Dict[str, Any] = {
            "node_name": node_name,
            "description": meta.description if meta else "",
            "domain": meta.domain if meta else "shared",
            "output_format": meta.output_format if meta else "text",
            "active_pack_id": active_pack.pack_id,
        }
        if meta and meta.contract_module and meta.contract_model:
            entry["contract"] = f"{meta.contract_module}:{meta.contract_model}"
        result.append(entry)
    return result


@router.get("/nodes/{node_name}/schema", summary="获取 JSON 节点的 Pydantic schema")
def get_node_schema(node_name: str) -> Dict[str, Any]:
    loader = _get_loader()
    response_format = loader.get_response_format_for(node_name)
    if response_format is None:
        raise HTTPException(
            status_code=404,
            detail=f"节点 '{node_name}' 不是 JSON 输出节点或无关联合约",
        )
    return response_format


# ------------------------------------------------------------------
# 覆盖管理
# ------------------------------------------------------------------


@router.post("/override", summary="激活节点覆盖")
def activate_override(payload: OverrideRequest) -> Dict[str, str]:
    try:
        registry = _get_registry()
        registry.activate_override(payload.node_name, payload.pack_id)
        return {"status": "ok", "node_name": payload.node_name, "pack_id": payload.pack_id}
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.delete("/override/{node_name}", summary="取消节点覆盖")
def deactivate_override(node_name: str) -> Dict[str, str]:
    registry = _get_registry()
    registry.deactivate_override(node_name)
    return {"status": "ok", "node_name": node_name}
