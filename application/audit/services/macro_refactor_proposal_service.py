"""Macro Refactor Proposal Service - 使用 LLM 生成重构建议"""
import logging
import os
from typing import Dict, Any
from application.audit.dtos.macro_refactor_dto import RefactorProposalRequest, RefactorProposal
from application.ai.refactor_proposal_llm_contract import (
    refactor_proposal_payload_to_domain,
)
from application.ai.structured_json_pipeline import structured_json_generate
from domain.ai.services.llm_service import LLMService, GenerationConfig
from domain.ai.value_objects.prompt import Prompt
from infrastructure.ai.prompt_template_loader import PromptTemplateLoader

logger = logging.getLogger(__name__)


class MacroRefactorProposalService:
    """宏观重构提案服务 - 使用 LLM 生成修复建议"""

    def __init__(self, llm_service: LLMService):
        """初始化服务

        Args:
            llm_service: LLM 服务实例
        """
        self.llm_service = llm_service

    async def generate_proposal(self, request: RefactorProposalRequest) -> RefactorProposal:
        """生成重构提案

        Args:
            request: 提案请求

        Returns:
            RefactorProposal: 重构提案
        """
        try:
            # 构建 LLM prompt
            prompt = self._build_prompt(request)

            # 调用结构化 JSON 管线
            loader = PromptTemplateLoader.get_instance()
            contract_model = loader.get_contract_for("refactor_proposal")
            config = GenerationConfig(
                model=os.getenv("SYSTEM_MODEL", ""),
                max_tokens=2048,
                temperature=0.7,
                response_format=loader.get_response_format_for("refactor_proposal"),
            )

            payload = await structured_json_generate(
                llm=self.llm_service,
                prompt=prompt,
                config=config,
                schema_model=contract_model,
            )

            if payload is None:
                logger.warning("结构化 JSON 管线返回 None，使用降级提案")
                return self._create_fallback_proposal()

            # 将校验后的 payload 转为领域 DTO
            return refactor_proposal_payload_to_domain(payload)

        except Exception as e:
            logger.error(f"Error generating proposal: {e}", exc_info=True)
            return self._create_fallback_proposal()

    def _build_prompt(self, request: RefactorProposalRequest) -> Prompt:
        """构建 LLM prompt

        Args:
            request: 提案请求

        Returns:
            Prompt: 构建的提示词
        """
        loader = PromptTemplateLoader.get_instance()
        return loader.render_to_prompt(
            "refactor_proposal",
            user_vars={
                "author_intent": request.author_intent,
                "current_event_summary": request.current_event_summary,
                "current_tags": ", ".join(request.current_tags),
                "event_id": request.event_id,
            },
            fallback_system="""你是一个专业的小说编辑助手，帮助作者修复人设冲突和叙事不一致问题。

你的任务是分析当前事件，根据作者意图提供修复建议。

请以 JSON 格式输出，包含以下字段：
- natural_language_suggestion: 自然语言建议（简洁明了）
- suggested_mutations: 建议的修改操作列表，每个操作是一个对象，包含：
  * type: 操作类型（"add_tag" | "remove_tag" | "replace_tag"）
  * tag: 要添加/删除的标签（add_tag/remove_tag）
  * old/new: 要替换的旧标签和新标签（replace_tag）
- suggested_tags: 建议的新标签列表
- reasoning: 推理过程（解释为什么这样修改）

示例输出：
{% raw %}{
    "natural_language_suggestion": "建议将角色的冲动行为改为理性决策",
    "suggested_mutations": [
        {"type": "replace_tag", "old": "动机:冲动", "new": "动机:理性"},
        {"type": "remove_tag", "tag": "情感:同情"}
    ],
    "suggested_tags": ["动机:理性", "性格:冷酷"],
    "reasoning": "冷酷的角色不会冲动行事，应该基于理性判断"
}{% endraw %}""",
            fallback_user="""请分析以下事件并提供修复建议：

**作者意图：**
{{ author_intent }}

**当前事件摘要：**
{{ current_event_summary }}

**当前标签：**
{{ current_tags }}

**事件 ID：**
{{ event_id }}

请提供修复建议（JSON 格式）：""",
        )

    def _create_fallback_proposal(self) -> RefactorProposal:
        """创建降级提案（当 LLM 失败时）

        Returns:
            RefactorProposal: 降级提案
        """
        return RefactorProposal(
            natural_language_suggestion="无法生成具体建议，请手动检查事件标签和内容",
            suggested_mutations=[],
            suggested_tags=[],
            reasoning="LLM 服务暂时不可用或响应格式错误"
        )
