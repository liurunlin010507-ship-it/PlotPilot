"""Claude 章节摘要生成器实现"""
import os
from domain.ai.services.chapter_summarizer import ChapterSummarizer
from domain.ai.services.llm_service import LLMService, GenerationConfig
from domain.ai.value_objects.prompt import Prompt
from infrastructure.ai.prompt_template_loader import PromptTemplateLoader


class ClaudeChapterSummarizer(ChapterSummarizer):
    """使用 Claude 实现的章节摘要生成器

    使用现有的 LLMService 生成章节摘要。
    """

    def __init__(self, llm_service: LLMService):
        """初始化 Claude 章节摘要生成器

        Args:
            llm_service: LLM 服务实例

        Raises:
            ValueError: 如果 ANTHROPIC_API_KEY 未设置
        """
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY environment variable is required")

        self.llm_service = llm_service

    async def summarize(self, content: str, max_length: int = 300) -> str:
        """生成章节摘要

        Args:
            content: 章节内容
            max_length: 摘要最大长度（字符数），默认 300

        Returns:
            生成的摘要文本

        Raises:
            ValueError: 当内容为空时
            RuntimeError: 当摘要生成失败时
        """
        # 验证输入
        if not content or not content.strip():
            raise ValueError("Content cannot be empty")

        # 构建提示词（通过模板加载器）
        loader = PromptTemplateLoader.get_instance()

        fallback_system = (
            "You are a professional chapter summarizer. Your task is to create "
            "concise, informative summaries of chapter content.\n\n"
            "Requirements:\n"
            "- Maximum length: {{ max_length }} characters\n"
            "- Focus on key plot points, character developments, and important events\n"
            "- Write in a clear, engaging style\n"
            "- Maintain the narrative flow\n"
            "- Do not include meta-commentary or analysis"
        )
        fallback_user = "Please summarize the following chapter content:\n\n{{ content }}"

        prompt = loader.render_to_prompt(
            "chapter_summarizer",
            system_vars={"max_length": max_length},
            user_vars={"content": content},
            fallback_system=fallback_system,
            fallback_user=fallback_user,
        )

        try:
            # 配置生成参数
            config = GenerationConfig(
                model=os.getenv("WRITING_MODEL", ""),
                max_tokens=1024,
                temperature=0.7
            )

            # 调用 LLM 服务生成摘要
            result = await self.llm_service.generate(prompt, config)

            return result.content

        except ValueError:
            # 重新抛出验证错误
            raise
        except Exception as e:
            # 转换为通用运行时错误
            raise RuntimeError(f"Failed to summarize chapter: {str(e)}") from e
