"""Prompt 模板系统数据模型。

用于模板包注册、查询和管理的值对象。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from jinja2 import Environment, TemplateNotFound


@dataclass
class PackInfo:
    """模板包摘要信息（用于列表展示）。"""

    pack_id: str
    name: str
    version: str
    author: str
    description: str
    category: str  # "builtin" | "marketplace" | "user"
    template_nodes: List[str] = field(default_factory=list)
    installed_at: Optional[str] = None


@dataclass
class NodeMeta:
    """单个 prompt 节点的元数据。"""

    node_name: str
    description: str
    domain: str  # "generation" | "analysis" | "extraction" | "blueprint" | "world" | "audit" | "shared"
    output_format: str  # "json" | "text"
    contract_module: Optional[str] = None
    contract_model: Optional[str] = None


@dataclass
class TemplatePack:
    """已加载的模板包实例。"""

    pack_id: str
    manifest: Dict[str, Any]
    pack_dir: Path
    jinja_env: Environment

    def has_node(self, node_name: str, role: str) -> bool:
        """检查该包是否包含指定节点的模板文件。"""
        domain = self._get_domain_for_node(node_name)
        template_name = f"{domain}/{node_name}_{role}.j2"
        try:
            self.jinja_env.get_template(template_name)
            return True
        except TemplateNotFound:
            return False

    def _get_domain_for_node(self, node_name: str) -> str:
        """从 manifest 的 templates 配置中获取节点所属功能域。"""
        templates = self.manifest.get("templates", {})
        node_cfg = templates.get(node_name, {})
        return node_cfg.get("domain", "shared")
