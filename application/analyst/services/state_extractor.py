import logging
import os
from domain.ai.services.llm_service import LLMService, GenerationConfig
from domain.ai.value_objects.prompt import Prompt
from domain.novel.value_objects.chapter_state import ChapterState
from application.ai.chapter_state_llm_contract import (
    CHAPTER_STATE_SYSTEM_FALLBACK,
    chapter_state_payload_to_domain,
    empty_chapter_state,
)
from application.ai.structured_json_pipeline import structured_json_generate
from infrastructure.ai.prompt_template_loader import PromptTemplateLoader

logger = logging.getLogger(__name__)


class StateExtractor:
    """状态提取应用服务

    使用 LLM 从章节内容中提取结构化信息
    """

    def __init__(self, llm_service: LLMService):
        self.llm_service = llm_service

    async def extract_chapter_state(self, content: str) -> ChapterState:
        """从章节内容中提取状态

        Args:
            content: 章节内容

        Returns:
            提取的章节状态
        """
        logger.info(f"StateExtractor.extract_chapter_state: content_length={len(content)}")

        # 构建提取提示词
        prompt = self._build_extraction_prompt(content)

        # 获取合约模型与 response_format
        loader = PromptTemplateLoader.get_instance()
        contract_model = loader.get_contract_for("chapter_state")
        response_format = loader.get_response_format_for("chapter_state")

        # 配置 LLM
        config = GenerationConfig(
            model=os.getenv("SYSTEM_MODEL", ""),
            max_tokens=4096,
            temperature=0.3,
            response_format=response_format,
        )

        # 调用结构化 JSON 管线
        payload = await structured_json_generate(
            llm=self.llm_service,
            prompt=prompt,
            config=config,
            schema_model=contract_model,
        )
        if payload is None:
            logger.warning("StateExtractor: 结构化 JSON 管线返回 None，使用空回退")
            chapter_state = empty_chapter_state()
        else:
            chapter_state = chapter_state_payload_to_domain(payload)
        logger.info(
            f"StateExtractor result: "
            f"new_characters={len(chapter_state.new_characters)}, "
            f"character_actions={len(chapter_state.character_actions)}, "
            f"relationship_changes={len(chapter_state.relationship_changes)}, "
            f"foreshadowing_planted={len(chapter_state.foreshadowing_planted)}, "
            f"foreshadowing_resolved={len(chapter_state.foreshadowing_resolved)}, "
            f"events={len(chapter_state.events)}"
        )
        return chapter_state

    def _build_extraction_prompt(self, content: str) -> Prompt:
        """构建提取提示词

        Args:
            content: 章节内容

        Returns:
            Prompt 值对象
        """
        loader = PromptTemplateLoader.get_instance()
        system = loader.render_with_fallback(
            "chapter_state", "system",
            fallback=CHAPTER_STATE_SYSTEM_FALLBACK,
        )
        user = loader.render_with_fallback(
            "chapter_state", "user",
            fallback=f"请从以下章节内容中提取结构化信息：\n\n{content}",
            content=content,
        )
        return Prompt(system=system, user=user)
