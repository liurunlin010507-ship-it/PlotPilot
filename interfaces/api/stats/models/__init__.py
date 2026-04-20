"""
数据模型：Pydantic模型定义
"""

from .responses import ErrorResponse, PaginatedResponse, SuccessResponse
from .stats_models import BookStats, ChapterStats, ContentAnalysis, GlobalStats, WritingProgress

__all__ = [
    "SuccessResponse",
    "ErrorResponse",
    "PaginatedResponse",
    "GlobalStats",
    "BookStats",
    "ChapterStats",
    "WritingProgress",
    "ContentAnalysis",
]
