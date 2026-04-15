"""Prompt 模板加载与渲染器。

从 PromptTemplateRegistry 解析出的 pack 中加载 Jinja2 模板，
渲染为 Prompt 值对象，并提供 JSON 合约模型的懒加载。
"""
from __future__ import annotations

import importlib
import logging
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Type

from pydantic import BaseModel

from domain.ai.value_objects.prompt import Prompt
from infrastructure.ai.prompt_template_models import TemplatePack
from infrastructure.ai.prompt_template_registry import (
    PromptTemplateRegistry,
    _PROMPTS_DIR,
)

logger = logging.getLogger(__name__)


class PromptTemplateLoader:
    """模板加载与渲染器。

    用法::

        loader = PromptTemplateLoader.get_instance()
        prompt = loader.render_to_prompt(
            "tension_scoring",
            system_vars={"prev_tension": 50.0},
            user_vars={"chapter_number": 5, "body": "..."},
        )
    """

    _instance: Optional[PromptTemplateLoader] = None

    def __init__(self, registry: Optional[PromptTemplateRegistry] = None) -> None:
        self._registry = registry or PromptTemplateRegistry()
        # 合约模型缓存：node_name → model class
        self._contract_cache: Dict[str, Optional[Type[BaseModel]]] = {}

    @classmethod
    def get_instance(cls) -> PromptTemplateLoader:
        """模块级单例。"""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def reset_instance(cls) -> None:
        """重置单例（仅用于测试）。"""
        cls._instance = None

    @property
    def registry(self) -> PromptTemplateRegistry:
        """暴露内部注册表（供 API 层使用）。"""
        return self._registry

    # ------------------------------------------------------------------
    # 低级 API
    # ------------------------------------------------------------------

    def render(self, node_name: str, role: str, **variables: Any) -> str:
        """从当前生效的 pack 中加载模板并渲染。

        Args:
            node_name: 节点名（如 "tension_scoring"）
            role: "system" 或 "user"
            **variables: 模板变量

        Returns:
            渲染后的字符串

        Raises:
            KeyError: 模板不存在
        """
        pack = self._registry.get_active_pack(node_name)
        domain = pack._get_domain_for_node(node_name)
        template_name = f"{domain}/{node_name}_{role}.j2"
        try:
            template = pack.jinja_env.get_template(template_name)
            return template.render(**variables)
        except Exception as e:
            raise KeyError(
                f"模板加载失败: node={node_name}, role={role}, "
                f"template={template_name}: {e}"
            ) from e

    def render_with_fallback(
        self,
        node_name: str,
        role: str,
        fallback: str,
        **variables: Any,
    ) -> str:
        """渲染模板，文件缺失时使用 fallback 字符串。"""
        try:
            return self.render(node_name, role, **variables)
        except KeyError:
            logger.warning(
                "模板 '%s_%s' 不存在，使用内联 fallback", node_name, role
            )
            # fallback 也作为 Jinja2 模板渲染（保持变量替换一致）
            pack = self._registry.get_active_pack(node_name)
            template = pack.jinja_env.from_string(fallback)
            return template.render(**variables)

    # ------------------------------------------------------------------
    # 高级 API
    # ------------------------------------------------------------------

    def render_to_prompt(
        self,
        node_name: str,
        *,
        system_vars: Optional[Dict[str, Any]] = None,
        user_vars: Optional[Dict[str, Any]] = None,
        fallback_system: Optional[str] = None,
        fallback_user: Optional[str] = None,
    ) -> Prompt:
        """加载 system + user 模板对，渲染为 Prompt 值对象。

        Args:
            node_name: 节点名
            system_vars: system 模板变量
            user_vars: user 模板变量
            fallback_system: system 模板缺失时的 fallback 字符串
            fallback_user: user 模板缺失时的 fallback 字符串

        Returns:
            Prompt 值对象
        """
        sv = system_vars or {}
        uv = user_vars or {}

        if fallback_system is not None:
            system = self.render_with_fallback(
                node_name, "system", fallback_system, **sv
            )
        else:
            system = self.render(node_name, "system", **sv)

        if fallback_user is not None:
            user = self.render_with_fallback(
                node_name, "user", fallback_user, **uv
            )
        else:
            user = self.render(node_name, "user", **uv)

        return Prompt(system=system, user=user)

    # ------------------------------------------------------------------
    # 合约管理
    # ------------------------------------------------------------------

    def get_contract_for(self, node_name: str) -> Optional[Type[BaseModel]]:
        """获取该节点关联的 Pydantic 合约模型（懒加载 + 缓存）。"""
        if node_name in self._contract_cache:
            return self._contract_cache[node_name]

        meta = self._registry.get_node_meta(node_name)
        if meta is None or not meta.contract_module or not meta.contract_model:
            self._contract_cache[node_name] = None
            return None

        try:
            module = importlib.import_module(meta.contract_module)
            model_cls = getattr(module, meta.contract_model)
            self._contract_cache[node_name] = model_cls
            return model_cls
        except (ImportError, AttributeError) as e:
            logger.error(
                "无法加载合约模型 %s:%s: %s",
                meta.contract_module, meta.contract_model, e,
            )
            self._contract_cache[node_name] = None
            return None

    def get_response_format_for(self, node_name: str) -> Optional[Dict[str, Any]]:
        """构建 response_format（供 GenerationConfig 使用）。

        包含合约校验：检查 extra="forbid" 等约束。
        """
        model_cls = self.get_contract_for(node_name)
        if model_cls is None:
            return None

        # 校验：合约模型应使用 extra="forbid"
        config = getattr(model_cls, "model_config", {})
        if config.get("extra") != "forbid":
            logger.warning(
                "合约模型 %s 未设置 extra='forbid'，可能导致 LLM 输出多余字段",
                model_cls.__name__,
            )

        schema = model_cls.model_json_schema(mode="validation")
        return {
            "type": "json_schema",
            "json_schema": {
                "name": node_name,
                "description": f"{node_name} structured output",
                "schema": schema,
                "strict": True,
            },
        }

    def validate_contract_for(self, node_name: str) -> List[str]:
        """校验合约模型的完整性（用于启动时检查）。"""
        warnings_list: List[str] = []
        model_cls = self.get_contract_for(node_name)
        if model_cls is None:
            return warnings_list

        # 1. extra="forbid" 检查
        config = getattr(model_cls, "model_config", {})
        if config.get("extra") != "forbid":
            warnings_list.append(
                f"{model_cls.__name__}: 未设置 extra='forbid'"
            )

        # 2. Field 约束检查
        for field_name, field_info in model_cls.model_fields.items():
            metadata = getattr(field_info, "metadata", [])
            has_max_length = any(
                hasattr(m, "max_length") and m.max_length is not None
                for m in metadata
            )
            if field_name.endswith("_justification") and not has_max_length:
                warnings_list.append(
                    f"{model_cls.__name__}.{field_name}: 缺少 max_length 约束"
                )

        return warnings_list

    # ------------------------------------------------------------------
    # 模板自描述解析
    # ------------------------------------------------------------------

    def _parse_template_header(self, template_source: str) -> Dict[str, Any]:
        """解析模板头部的 {# @node @role @output @vars #} 注释声明。"""
        result: Dict[str, Any] = {}
        # 提取 {# ... #} 块
        match = re.match(r"\{#\s*(.*?)\s*#\}", template_source, re.DOTALL)
        if not match:
            return result

        header = match.group(1)

        # 解析 @key: value
        for m in re.finditer(r"@(\w+):\s*(.+?)(?=\n\s*@|\Z)", header, re.DOTALL):
            key = m.group(1)
            value = m.group(2).strip()
            result[key] = value

        return result

    def validate_template_consistency(self, node_name: str) -> List[str]:
        """校验模板头部声明与 manifest.json 的一致性。"""
        warnings_list: List[str] = []
        meta = self._registry.get_node_meta(node_name)
        if meta is None:
            warnings_list.append(f"节点 '{node_name}' 不在 manifest.json 中")
            return warnings_list

        for role in ("system", "user"):
            try:
                pack = self._registry.get_active_pack(node_name)
                domain = pack._get_domain_for_node(node_name)
                template_name = f"{domain}/{node_name}_{role}.j2"
                template = pack.jinja_env.get_template(template_name)
                header = self._parse_template_header(template.source)

                # 校验 @node
                if header.get("node") != node_name:
                    warnings_list.append(
                        f"{template_name}: @node='{header.get('node')}' "
                        f"与 manifest 节点名 '{node_name}' 不一致"
                    )

                # 校验 @output
                header_output = header.get("output", "text")
                if header_output != meta.output_format:
                    warnings_list.append(
                        f"{template_name}: @output='{header_output}' "
                        f"与 manifest output_format='{meta.output_format}' 不一致"
                    )

            except Exception:
                pass  # 模板不存在不在此处报错

        return warnings_list

    # ------------------------------------------------------------------
    # 便捷查询
    # ------------------------------------------------------------------

    def list_nodes(self) -> List[str]:
        """列出所有已知节点名。"""
        return self._registry.list_nodes()

    def list_json_nodes(self) -> List[str]:
        """列出所有 JSON 输出节点名。"""
        return self._registry.list_json_nodes()
