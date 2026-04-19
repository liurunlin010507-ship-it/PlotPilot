"""AI 功能评测脚本集

用于测试和优化各种 AI 生成功能的效果。
使用项目现有服务接口，不重新实现LLM调用。
"""

from .base_evaluator import (
    BaseEvaluator,
    EvaluationMetric,
    EvaluationReport,
    EvaluationResult,
    create_metric,
)
from .beat_sheet_evaluator import BeatSheetEvaluator
from .chapter_generation_evaluator import ChapterGenerationEvaluator
from .consistency_evaluator import ConsistencyEvaluator
from .knowledge_evaluator import KnowledgeEvaluator
from .macro_planning_evaluator import MacroPlanningEvaluator

__all__ = [
    "BaseEvaluator",
    "EvaluationResult",
    "EvaluationReport",
    "EvaluationMetric",
    "create_metric",
    "ChapterGenerationEvaluator",
    "MacroPlanningEvaluator",
    "BeatSheetEvaluator",
    "KnowledgeEvaluator",
    "ConsistencyEvaluator",
]
