"""
ACPO-LLM Prompt Engineering Module
====================================
提供结构化的 Prompt 生成和管理功能，包括：
- 向量化知识库
- 优化策略模板
- Few-shot 示例
- 多轮优化 Prompt 构建
"""

from .knowledge_base import get_vectorization_patterns, get_pattern_for_issue
from .templates import (
    build_optimization_prompt,
    build_retry_prompt,
    get_prompt_template_versions,
    resolve_system_prompt_template_name,
)
from .examples import get_all_examples, get_relevant_examples, get_transformation_examples

__all__ = [
    'get_vectorization_patterns',
    'get_pattern_for_issue',
    'build_optimization_prompt',
    'build_retry_prompt',
    'get_prompt_template_versions',
    'resolve_system_prompt_template_name',
    'get_all_examples',
    'get_relevant_examples',
    'get_transformation_examples',
]
