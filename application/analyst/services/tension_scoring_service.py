"""独立多维张力分析服务。

将张力评分从 llm_chapter_extract_bundle() 的多任务 JSON 提取中拆出，
使用专门的多维 prompt（情节/情绪/节奏）进行精准分析。
"""
from __future__ import annotations

import logging
from domain.ai.services.llm_service import LLMService, GenerationConfig
from domain.novel.value_objects.tension_dimensions import TensionDimensions
from application.ai.tension_scoring_contract import (
    tension_scoring_payload_to_domain,
)
from application.ai.structured_json_pipeline import structured_json_generate
from infrastructure.ai.prompt_template_loader import PromptTemplateLoader

logger = logging.getLogger(__name__)

# 章节正文最大长度（与 llm_chapter_extract_bundle 保持一致）
_MAX_CONTENT_LENGTH = 24000

# 内联 fallback（模板文件缺失时使用）
_FALLBACK_SYSTEM = """你是专业的网文叙事张力分析师。你的任务是分析章节正文的多维张力。

## 评分维度（每项 0-100 整数）

### 1. 情节张力 (plot_tension)
衡量冲突强度、悬念密度和信息不对称程度。
### 2. 情绪张力 (emotional_tension)
衡量角色情绪波动幅度和读者共情深度。
### 3. 节奏张力 (pacing_tension)
衡量场景切换频率、叙述节奏和信息密度。

前章综合张力约为 {{ prev_tension }}/100。

输出 JSON：{% raw %}{{"plot_tension": 0, "emotional_tension": 0, "pacing_tension": 0, "plot_justification": "", "emotional_justification": "", "pacing_justification": ""}}{% endraw %}"""

_FALLBACK_USER = """第 {{ chapter_number }} 章正文如下：

{{ body }}"""


class TensionScoringService:
    """独立多维张力分析服务。

    对章节正文进行三维度（情节张力、情绪张力、节奏张力）评分，
    并通过加权公式计算综合张力分。
    """

    def __init__(self, llm_service: LLMService) -> None:
        self._llm = llm_service

    async def score_chapter(
        self,
        chapter_content: str,
        chapter_number: int,
        prev_chapter_tension: float = 50.0,
    ) -> TensionDimensions:
        """分析章节的多维张力。

        Args:
            chapter_content: 章节正文
            chapter_number: 章节号
            prev_chapter_tension: 前章综合张力（0-100），用于提供上下文基准

        Returns:
            TensionDimensions 多维张力结果
        """
        body = chapter_content.strip()
        if not body:
            return TensionDimensions.neutral()
        if len(body) > _MAX_CONTENT_LENGTH:
            body = body[:_MAX_CONTENT_LENGTH] + "\n\n…（正文过长已截断）"

        loader = PromptTemplateLoader.get_instance()
        prompt = loader.render_to_prompt(
            "tension_scoring",
            system_vars={"prev_tension": f"{prev_chapter_tension:.0f}"},
            user_vars={"chapter_number": chapter_number, "body": body},
            fallback_system=_FALLBACK_SYSTEM,
            fallback_user=_FALLBACK_USER,
        )
        contract_model = loader.get_contract_for("tension_scoring")
        config = GenerationConfig(
            max_tokens=512,
            temperature=0.3,
            response_format=loader.get_response_format_for("tension_scoring"),
        )

        try:
            payload = await structured_json_generate(
                llm=self._llm,
                prompt=prompt,
                config=config,
                schema_model=contract_model,
            )
        except Exception as e:
            logger.warning("张力评分管线异常: %s", e)
            payload = None

        if payload is None:
            return TensionDimensions.neutral()

        dims = tension_scoring_payload_to_domain(payload)
        logger.debug(
            "张力评分完成: plot=%.0f emotional=%.0f pacing=%.0f composite=%.1f",
            dims.plot_tension,
            dims.emotional_tension,
            dims.pacing_tension,
            dims.composite_score,
        )
        return dims
