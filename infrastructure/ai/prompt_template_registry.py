"""Prompt 模板包注册表。

管理内置 / 广场 / 用户自定义模板包的注册、激活覆盖和查询。
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional

from jinja2 import Environment, FileSystemLoader

from infrastructure.ai.prompt_template_models import (
    NodeMeta,
    PackInfo,
    TemplatePack,
)

logger = logging.getLogger(__name__)

# 默认模板根目录
_PROMPTS_DIR = Path(__file__).resolve().parent / "prompts"


class PromptTemplateRegistry:
    """模板包注册表。

    管理：
    1. 多个模板包的注册（内置、广场下载、用户自定义）
    2. 节点粒度的覆盖激活
    3. 优先级解析：active_overrides → builtin
    """

    def __init__(self, prompts_dir: Optional[Path] = None) -> None:
        self._prompts_dir = prompts_dir or _PROMPTS_DIR
        self._packs: Dict[str, TemplatePack] = {}
        self._active_overrides: Dict[str, str] = {}  # node_name → pack_id
        self._load_builtin()

    # ------------------------------------------------------------------
    # 初始化
    # ------------------------------------------------------------------

    def _load_builtin(self) -> None:
        """加载内置模板包。"""
        builtin_dir = self._prompts_dir / "builtin"
        manifest_path = self._prompts_dir / "manifest.json"

        if not builtin_dir.is_dir():
            logger.warning("内置模板目录不存在: %s", builtin_dir)
            return

        if not manifest_path.is_file():
            logger.warning("内置 manifest.json 不存在: %s", manifest_path)
            return

        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as e:
            logger.error("无法加载内置 manifest.json: %s", e)
            return

        env = self._create_jinja_env(builtin_dir)
        pack = TemplatePack(
            pack_id=manifest.get("pack_id", "builtin"),
            manifest=manifest,
            pack_dir=builtin_dir,
            jinja_env=env,
        )
        self._packs[pack.pack_id] = pack
        logger.info("已加载内置模板包: %s (%d 节点)",
                     pack.pack_id, len(manifest.get("templates", {})))

    @staticmethod
    def _create_jinja_env(pack_dir: Path) -> Environment:
        """为指定包目录创建 Jinja2 环境（启用缓存）。"""
        return Environment(
            loader=FileSystemLoader(str(pack_dir)),
            keep_trailing_newline=True,
            autoescape=False,
            trim_blocks=True,
            lstrip_blocks=True,
            auto_reload=False,
        )

    # ------------------------------------------------------------------
    # 包管理
    # ------------------------------------------------------------------

    def register_pack(self, pack_dir: Path) -> str:
        """注册一个模板包（本地目录）。

        Args:
            pack_dir: 模板包根目录（需含 manifest.json）

        Returns:
            注册的 pack_id

        Raises:
            FileNotFoundError: manifest.json 不存在
            ValueError: manifest 格式错误
        """
        manifest_path = pack_dir / "manifest.json"
        if not manifest_path.is_file():
            raise FileNotFoundError(f"模板包缺少 manifest.json: {manifest_path}")

        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        pack_id = manifest.get("pack_id")
        if not pack_id:
            raise ValueError("manifest.json 缺少 pack_id 字段")

        env = self._create_jinja_env(pack_dir)
        pack = TemplatePack(
            pack_id=pack_id,
            manifest=manifest,
            pack_dir=pack_dir,
            jinja_env=env,
        )
        self._packs[pack_id] = pack
        logger.info("已注册模板包: %s", pack_id)
        return pack_id

    def reload_pack(self, pack_id: str) -> None:
        """重新加载指定包的 Jinja2 环境（安装新模板包后调用）。"""
        if pack_id not in self._packs:
            raise KeyError(f"模板包未注册: {pack_id}")
        pack = self._packs[pack_id]
        pack.jinja_env = self._create_jinja_env(pack.pack_dir)
        logger.info("已重新加载模板包: %s", pack_id)

    # ------------------------------------------------------------------
    # 覆盖管理
    # ------------------------------------------------------------------

    def activate_override(self, node_name: str, pack_id: str) -> None:
        """为某个节点启用指定模板包的覆盖。"""
        if pack_id not in self._packs:
            raise KeyError(f"模板包未注册: {pack_id}")
        self._active_overrides[node_name] = pack_id
        logger.info("节点 '%s' 已切换到模板包 '%s'", node_name, pack_id)

    def deactivate_override(self, node_name: str) -> None:
        """取消覆盖，恢复使用内置模板。"""
        self._active_overrides.pop(node_name, None)
        logger.info("节点 '%s' 已恢复内置模板", node_name)

    # ------------------------------------------------------------------
    # 查询
    # ------------------------------------------------------------------

    def get_active_pack(self, node_name: str) -> TemplatePack:
        """获取某个节点当前生效的模板包。

        优先级：active_overrides → builtin
        """
        pack_id = self._active_overrides.get(node_name)
        if pack_id and pack_id in self._packs:
            return self._packs[pack_id]
        # 回退到内置
        builtin = self._packs.get("builtin")
        if builtin is None:
            raise RuntimeError("内置模板包未加载")
        return builtin

    def get_node_meta(self, node_name: str) -> Optional[NodeMeta]:
        """获取节点的元数据（从当前生效的包的 manifest 中读取）。"""
        pack = self.get_active_pack(node_name)
        templates = pack.manifest.get("templates", {})
        cfg = templates.get(node_name)
        if cfg is None:
            return None
        return NodeMeta(
            node_name=node_name,
            description=cfg.get("description", ""),
            domain=cfg.get("domain", "shared"),
            output_format=cfg.get("output_format", "text"),
            contract_module=cfg.get("contract_module"),
            contract_model=cfg.get("contract_model"),
        )

    def list_packs(self) -> List[PackInfo]:
        """列出所有已注册模板包。"""
        result: List[PackInfo] = []
        for pack in self._packs.values():
            manifest = pack.manifest
            result.append(PackInfo(
                pack_id=pack.pack_id,
                name=manifest.get("name", ""),
                version=manifest.get("version", ""),
                author=manifest.get("author", ""),
                description=manifest.get("description", ""),
                category=manifest.get("category", "user"),
                template_nodes=list(manifest.get("templates", {}).keys()),
            ))
        return result

    def list_nodes(self) -> List[str]:
        """列出所有已知节点名（合并所有包中的节点）。"""
        nodes: set = set()
        for pack in self._packs.values():
            nodes.update(pack.manifest.get("templates", {}).keys())
        return sorted(nodes)

    def list_json_nodes(self) -> List[str]:
        """列出所有 output_format="json" 的节点名。"""
        return [
            name for name in self.list_nodes()
            if self.get_node_meta(name) and self.get_node_meta(name).output_format == "json"
        ]
