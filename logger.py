#!/usr/bin/env python3
"""
VecGuide 日志模块
提供统一的日志输出，包含文件名、函数名和行号信息
"""

import sys
import os
from datetime import datetime
from typing import Optional
from functools import wraps

# 日志级别
DEBUG = 0
INFO = 1
WARNING = 2
ERROR = 3
CRITICAL = 4

# 全局日志级别设置
_current_level = INFO

# 颜色代码（用于终端输出）
_COLORS = {
    'DEBUG': '\033[36m',      # 青色
    'INFO': '\033[32m',       # 绿色
    'WARNING': '\033[33m',    # 黄色
    'ERROR': '\033[31m',      # 红色
    'CRITICAL': '\033[35m',   # 紫色
    'RESET': '\033[0m',       # 重置
    'GRAY': '\033[90m',       # 灰色（用于元信息）
}


def setup_logger(level: int = INFO, use_color: bool = True):
    """
    设置日志级别和颜色选项

    Args:
        level: 日志级别 (DEBUG=0, INFO=1, WARNING=2, ERROR=3, CRITICAL=4)
        use_color: 是否使用颜色输出
    """
    global _current_level
    _current_level = level

    if not use_color or not sys.stdout.isatty():
        # 禁用颜色
        for key in _COLORS:
            _COLORS[key] = ''


def _get_caller_info(depth: int = 1):
    """
    获取调用者的文件、函数、行号信息

    Args:
        depth: 需要向上追溯的额外层数（1 = 直接调用者）
    """
    import inspect
    frame = inspect.currentframe()
    try:
        # 栈结构: _get_caller_info -> _emit -> info/success/... -> 实际调用者
        # depth=1: _emit -> public_func -> caller (for direct calls)
        # depth=2: _emit -> wrapper -> public_func -> caller (for wrapped calls)
        caller_frame = frame
        for _ in range(depth + 1):  # +1 to skip _get_caller_info itself
            caller_frame = caller_frame.f_back
            if caller_frame is None:
                return "unknown", "unknown", 0
        filename = os.path.basename(caller_frame.f_code.co_filename)
        funcname = caller_frame.f_code.co_name
        lineno = caller_frame.f_lineno
        return filename, funcname, lineno
    finally:
        del frame


def _emit(level: str, level_val: int, message: str, show_meta: bool, depth: int = 2):
    """
    内部日志输出函数

    Args:
        level: 级别名称
        level_val: 级别数值
        message: 消息内容
        show_meta: 是否显示元信息
        depth: 调用栈深度（2=直接调用，3=包装器调用）
    """
    if _current_level > level_val:
        return

    filename, funcname, lineno = _get_caller_info(depth)
    formatted = _format_message(level, filename, funcname, lineno, message, show_meta)

    if level_val >= ERROR:
        print(formatted, file=sys.stderr)
    else:
        print(formatted)


def _format_message(level: str, filename: str, funcname: str, lineno: int,
                    message: str, show_meta: bool = True) -> str:
    """格式化日志消息"""
    color = _COLORS.get(level, '')
    reset = _COLORS['RESET']
    gray = _COLORS['GRAY']

    # 时间戳
    timestamp = datetime.now().strftime('%H:%M:%S')

    if show_meta:
        # 完整格式: [时间] [级别] [文件:函数:行] 消息
        meta_info = f"{gray}[{filename}:{funcname}:{lineno}]{reset}"
        return f"{gray}[{timestamp}]{reset} {color}[{level}]{reset} {meta_info} {message}"
    else:
        # 简洁格式: [时间] [级别] 消息
        return f"{gray}[{timestamp}]{reset} {color}[{level}]{reset} {message}"


def debug(message: str, show_meta: bool = True):
    """输出 DEBUG 级别日志"""
    _emit('DEBUG', DEBUG, message, show_meta, depth=2)


def info(message: str, show_meta: bool = True):
    """输出 INFO 级别日志"""
    _emit('INFO', INFO, message, show_meta, depth=2)


def warning(message: str, show_meta: bool = True):
    """输出 WARNING 级别日志"""
    _emit('WARNING', WARNING, message, show_meta, depth=2)


def error(message: str, show_meta: bool = True):
    """输出 ERROR 级别日志"""
    _emit('ERROR', ERROR, message, show_meta, depth=2)


def critical(message: str, show_meta: bool = True):
    """输出 CRITICAL 级别日志"""
    _emit('CRITICAL', CRITICAL, message, show_meta, depth=2)


# 便捷函数：带进度前缀的日志
def progress(current: int, total: int, message: str):
    """输出带进度信息的日志"""
    prefix = f"[{current}/{total}]"
    _emit('INFO', INFO, f"{prefix} {message}", False, depth=2)


def section(title: str, width: int = 70):
    """输出章节分隔线"""
    print(f"\n{'=' * width}")
    print(f"🎯 {title}")
    print(f"{'=' * width}")


def subsection(title: str, width: int = 60):
    """输出子章节分隔线"""
    print(f"\n{'-' * width}")
    print(f"📌 {title}")
    print(f"{'-' * width}")


def success(message: str, show_meta: bool = True):
    """输出成功信息"""
    _emit('INFO', INFO, f"✅ {message}", show_meta, depth=2)


def failure(message: str):
    """输出失败信息"""
    _emit('ERROR', ERROR, f"❌ {message}", True, depth=2)


def warning_icon(message: str):
    """输出警告信息"""
    _emit('WARNING', WARNING, f"⚠️  {message}", True, depth=2)


# 装饰器：记录函数入口和出口
def log_call(func):
    """装饰器：自动记录函数调用和返回"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        func_name = func.__name__
        module_name = func.__module__

        debug(f">> Entering {module_name}.{func_name}")
        try:
            result = func(*args, **kwargs)
            debug(f"<< Exiting {module_name}.{func_name}")
            return result
        except Exception as e:
            error(f"!! Exception in {module_name}.{func_name}: {e}")
            raise
    return wrapper


# 初始化
setup_logger(INFO, use_color=sys.stdout.isatty())
