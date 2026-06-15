#!/usr/bin/env python3
"""
VecGuide configuration module.

Local secrets and machine-specific paths are loaded from `.env` when present.
The `.env` file is intentionally ignored by git; use `.env.example` as the
public template.
"""

import os
from pathlib import Path


def _load_dotenv(env_file=".env"):
    """Load simple KEY=VALUE pairs from a local .env file without extra deps."""
    env_path = Path(__file__).resolve().parent / env_file
    if not env_path.exists():
        return

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key:
            os.environ.setdefault(key, value)


_load_dotenv()


class Config:
    """全局配置类"""

    # API 配置。真实 key 写入本地 .env，不写入公开代码。
    DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")
    ANTHROPIC_MODEL = os.environ.get("ANTHROPIC_MODEL", "glm-4.7")
    DEEPSEEK_BASE_URL = os.environ.get(
        "DEEPSEEK_BASE_URL",
        "https://open.bigmodel.cn/api/anthropic",
    )

    # 编译器配置。本机路径可在 .env 中覆盖。
    DEFAULT_CLANG_PATH = os.environ.get("DEFAULT_CLANG_PATH", "clang")
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
