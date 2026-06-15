#!/usr/bin/env python3
"""
ACPO-LLM 配置管理模块
统一管理所有配置项，避免硬编码
"""

import os
from pathlib import Path


class Config:
    """全局配置类"""

    # #API 配置 deepseek-v4pro
    # DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "sk-0ff4867d02eb477c9a8341c69039fb28")
    # ANTHROPIC_MODEL = os.environ.get("ANTHROPIC_MODEL", "deepseek-v4-pro")
    # DEEPSEEK_BASE_URL = "https://api.deepseek.com/anthropic"

    # API 配置 glm-4.7（论文主模型）
    DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "0c83754792574ba9a3783880aaf75706.FXkfwsneUxV1yAiN")
    ANTHROPIC_MODEL = os.environ.get("ANTHROPIC_MODEL", "glm-4.7")
    DEEPSEEK_BASE_URL = "https://open.bigmodel.cn/api/anthropic"

    # 编译器配置
    DEFAULT_CLANG_PATH = "/home/cshgg2/test/llvm-project/build/bin/clang"
    CLANG_PATH = os.environ.get("CLANG_PATH", DEFAULT_CLANG_PATH)

    # 源代码配置
    DEFAULT_SOURCE_FILE = "./TSVC_2/src/tsvc.c"
    SOURCE_FILE = os.environ.get("SOURCE_FILE", DEFAULT_SOURCE_FILE)

    # TSVC 包含路径
    TSVC_INCLUDE_PATH = "./TSVC_2/src"

    # 优化配置
    DEFAULT_MAX_ROUNDS = 3
    MAX_ROUNDS = int(os.environ.get("MAX_ROUNDS", DEFAULT_MAX_ROUNDS))

    # 文件命名配置
    OPTIMIZED_FILE_PREFIX = os.environ.get("OPTIMIZED_FILE_PREFIX", "optimized_")
    PROBLEM_MAP_FILE = os.environ.get("PROBLEM_MAP_FILE", "problem_map.json")
    OPTIMIZATION_STATE_FILE = os.environ.get("OPTIMIZATION_STATE_FILE", "optimization_state.json")

    # 编译配置
    ARRAY_ALIGNMENT = 64
    LEN_1D = 32000
    LEN_2D = 256
    ITERATIONS = 100000

    # Benchmark 协议配置
    DEFAULT_BENCHMARK_WARMUP_RUNS = 3
    DEFAULT_BENCHMARK_TIMING_RUNS = 10
    DEFAULT_BENCHMARK_BATCHES = 1


# 全局配置实例
config = Config()


def get_clang_path():
    """获取 Clang 编译器路径"""
    return config.CLANG_PATH


def get_source_file():
    """获取源文件路径"""
    return config.SOURCE_FILE


def get_api_key():
    """获取 API 密钥"""
    return config.DEEPSEEK_API_KEY


def get_model_name():
    """获取模型名称"""
    return config.ANTHROPIC_MODEL


def check_clang_available(clang_path=None):
    """检查 Clang 编译器是否可用"""
    if clang_path is None:
        clang_path = config.CLANG_PATH

    if not os.path.isfile(clang_path):
        return False, f"Clang 编译器不存在: {clang_path}"

    if not os.access(clang_path, os.X_OK):
        return False, f"Clang 编译器没有执行权限: {clang_path}"

    return True, None


def check_source_file_exists(source_file=None):
    """检查源文件是否存在"""
    if source_file is None:
        source_file = config.SOURCE_FILE

    if not os.path.exists(source_file):
        return False, f"源文件不存在: {source_file}"

    return True, None
