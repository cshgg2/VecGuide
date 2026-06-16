#!/usr/bin/env python3
"""
VecGuide 正确性验证模块
============================
提供三层正确性保证机制：
1. 编译检查 - 确保代码可编译
2. 语义等价性验证 - 校验和比对
3. 运行时测试 - 实际执行验证
"""

import os
import subprocess
import tempfile
import re
from statistics import mean, median, stdev
from typing import Dict, Tuple, Optional
from config import config
from evaluate_optimization import MINIMAL_UNIT_TEMPLATE, build_support_code


_DRIVER_METRIC_KEYS = ("CHECKSUM", "STATE_SUM", "STATE_ABS_SUM", "STATE_WEIGHTED_SUM")
_DEFAULT_ARG_CASE = (1, 1)
_PARAMETERIZED_ARG_CASES = {
    "s122": [(1, 1), (2, 2), (4, 3)],
    "s172": [(1, 1), (1, 2), (3, 4)],
    "s174": [(1, 1), (64, 1), (256, 1)],
}
_RUNTIME_TEST_SCALES = (1.0, 2.0, -1.0)
_BOUNDARY_TEST_COUNT = 7
_SCALAR_INT_ARG_FUNCS = {"s162", "s174"}
_INDIRECT_INDEX_ARG_FUNCS = {"s4113", "s4115"}


def _get_arg_cases(func_name: str) -> list[tuple[int, int]]:
    """返回函数需要覆盖的 arg_info 取值集合。"""
    return list(_PARAMETERIZED_ARG_CASES.get(func_name, [_DEFAULT_ARG_CASE]))


def _format_arg_case(arg_case: tuple[int, int]) -> str:
    """格式化 arg_info，便于日志和错误信息定位。"""
    return f"n1={arg_case[0]}, n3={arg_case[1]}"


def _arg_case_dict(arg_case: tuple[int, int]) -> Dict[str, int]:
    """将参数对转换为可序列化结构。"""
    return {'a': arg_case[0], 'b': arg_case[1]}


def _build_driver_arg_setup_code(func_name: str) -> str:
    """为测试驱动生成与函数签名兼容的 arg_info 初始化代码。"""
    if func_name in _SCALAR_INT_ARG_FUNCS:
        return (
            "    int scalar_arg_info = arg_a;\n"
            "    args.arg_info = &scalar_arg_info;"
        )

    if func_name in _INDIRECT_INDEX_ARG_FUNCS:
        return "    args.arg_info = indx;"

    if func_name == "s4112":
        return (
            "    struct { int * __restrict__ a; real_t b; } indirect_arg_info = {indx, (real_t)arg_a};\n"
            "    args.arg_info = &indirect_arg_info;"
        )

    if func_name == "s4114":
        return (
            "    struct { int * __restrict__ a; int b; } indirect_arg_info = {indx, arg_a};\n"
            "    args.arg_info = &indirect_arg_info;"
        )

    if func_name == "s4116":
        return (
            "    struct { int * __restrict__ a; int b; int c; } indirect_arg_info = {indx, arg_a, arg_b};\n"
            "    args.arg_info = &indirect_arg_info;"
        )

    return (
        "    struct { int a; int b; } default_arg_info = {arg_a, arg_b};\n"
        "    args.arg_info = &default_arg_info;"
    )


def _parse_driver_metrics(output: str) -> Dict[str, float]:
    """解析测试驱动输出的关键度量。"""
    metrics = {}
    for line in output.splitlines():
        if ':' not in line:
            continue
        key, raw_value = line.split(':', 1)
        key = key.strip()
        if key not in _DRIVER_METRIC_KEYS:
            continue
        try:
            metrics[key] = float(raw_value.strip())
        except ValueError:
            continue
    return metrics


def _compare_driver_metrics(
    original_metrics: Dict[str, float],
    optimized_metrics: Dict[str, float],
    tolerance: float,
) -> Optional[str]:
    """比较测试驱动输出的关键度量，返回首个不匹配的错误信息。"""
    missing = [
        key for key in _DRIVER_METRIC_KEYS
        if key not in original_metrics or key not in optimized_metrics
    ]
    if missing:
        return f"缺少关键输出字段: {', '.join(missing)}"

    for key in _DRIVER_METRIC_KEYS:
        lhs = original_metrics[key]
        rhs = optimized_metrics[key]
        diff = abs(lhs - rhs)
        allowed = tolerance * max(abs(lhs), abs(rhs), 1.0)
        if diff > allowed:
            return (
                f"{key} 不匹配: 原始={lhs:.6f}, 优化={rhs:.6f}, "
                f"diff={diff:.6f}, tol={allowed:.6f}"
            )
    return None


# 测试驱动模板 - 用于运行优化后的函数并计算校验和
TEST_DRIVER_TEMPLATE = '''/* Auto-generated test driver for {func_name} */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <sys/time.h>
#include <math.h>

#define iterations 100000
#define LEN_1D 32000
#define LEN_2D 256
#define ARRAY_ALIGNMENT 64

struct args_t {{
    struct timeval t1;
    struct timeval t2;
    void * __restrict__ arg_info;
}};

typedef float real_t;

// Global arrays
__attribute__((aligned(ARRAY_ALIGNMENT))) real_t flat_2d_array[LEN_2D*LEN_2D];
__attribute__((aligned(ARRAY_ALIGNMENT))) real_t x[LEN_1D];
__attribute__((aligned(ARRAY_ALIGNMENT))) real_t a[LEN_1D],b[LEN_1D],c[LEN_1D],d[LEN_1D],e[LEN_1D];
__attribute__((aligned(ARRAY_ALIGNMENT))) real_t aa[LEN_2D][LEN_2D],bb[LEN_2D][LEN_2D],cc[LEN_2D][LEN_2D],tt[LEN_2D][LEN_2D];
__attribute__((aligned(ARRAY_ALIGNMENT))) int indx[LEN_1D];
real_t* __restrict__ xx;
real_t* yy;

// dummy: prevent dead-code elimination, mimic TSVC behavior
int dummy(real_t a[LEN_1D], real_t b[LEN_1D], real_t c[LEN_1D], real_t d[LEN_1D],
          real_t e[LEN_1D], real_t aa[LEN_2D][LEN_2D], real_t bb[LEN_2D][LEN_2D],
          real_t cc[LEN_2D][LEN_2D], real_t s) {{
    (void)a; (void)b; (void)c; (void)d; (void)e;
    (void)aa; (void)bb; (void)cc; (void)s;
    return 0;
}}

// Array initialization for {func_name}
void init_arrays_for_{func_name}() {{
    xx = flat_2d_array;
    yy = flat_2d_array;

    for (int i = 0; i < LEN_1D; i++) {{
        a[i] = 1.0 + i;
        b[i] = 2.0 + i;
        c[i] = 3.0 + i;
        d[i] = 4.0 + i;
        e[i] = 5.0 + i;
        x[i] = 1.0;
        indx[i] = ((i + 1) % 4) + 1;
    }}

    for (int i = 0; i < LEN_2D; i++) {{
        for (int j = 0; j < LEN_2D; j++) {{
            int flat_idx = i * LEN_2D + j;
            flat_2d_array[flat_idx] = (real_t)(flat_idx + 1) * 0.125f;
            aa[i][j] = 1.0f / (i + 1);
            bb[i][j] = 1.0f / (j + 1);
            cc[i][j] = 1.0f / (i + j + 1);
            tt[i][j] = (real_t)(i - j);
        }}
    }}
}}

// Wrappers mapping TSVC-style calls to local implementations
int initialise_arrays(const char* name) {{
    (void)name;
    init_arrays_for_{func_name}();
    return 0;
}}

// Helper function f used by some TSVC functions (e.g., s4121)
real_t f(real_t a, real_t b) {{
    return a * b;
}}

// Checksum calculation
real_t calc_checksum_simple() {{
    real_t sum = 0.0;
    for (int i = 0; i < LEN_1D; i++) {{
        sum += a[i];
    }}
    return sum;
}}

real_t calc_checksum(const char* name) {{
    (void)name;
    return calc_checksum_simple();
}}

double sum_real_1d(const real_t* arr) {{
    double sum = 0.0;
    for (int i = 0; i < LEN_1D; i++) {{
        sum += (double)arr[i];
    }}
    return sum;
}}

double abs_sum_real_1d(const real_t* arr) {{
    double sum = 0.0;
    for (int i = 0; i < LEN_1D; i++) {{
        sum += fabs((double)arr[i]);
    }}
    return sum;
}}

double weighted_sum_real_1d(const real_t* arr) {{
    double sum = 0.0;
    for (int i = 0; i < LEN_1D; i++) {{
        sum += (double)arr[i] * (double)(i + 1);
    }}
    return sum;
}}

double sum_real_2d(real_t arr[LEN_2D][LEN_2D]) {{
    double sum = 0.0;
    for (int i = 0; i < LEN_2D; i++) {{
        for (int j = 0; j < LEN_2D; j++) {{
            sum += (double)arr[i][j];
        }}
    }}
    return sum;
}}

double abs_sum_real_2d(real_t arr[LEN_2D][LEN_2D]) {{
    double sum = 0.0;
    for (int i = 0; i < LEN_2D; i++) {{
        for (int j = 0; j < LEN_2D; j++) {{
            sum += fabs((double)arr[i][j]);
        }}
    }}
    return sum;
}}

double weighted_sum_real_2d(real_t arr[LEN_2D][LEN_2D]) {{
    double sum = 0.0;
    int weight = 1;
    for (int i = 0; i < LEN_2D; i++) {{
        for (int j = 0; j < LEN_2D; j++) {{
            sum += (double)arr[i][j] * (double)weight++;
        }}
    }}
    return sum;
}}

double sum_real_flat(const real_t* arr, int len) {{
    double sum = 0.0;
    for (int i = 0; i < len; i++) {{
        sum += (double)arr[i];
    }}
    return sum;
}}

double abs_sum_real_flat(const real_t* arr, int len) {{
    double sum = 0.0;
    for (int i = 0; i < len; i++) {{
        sum += fabs((double)arr[i]);
    }}
    return sum;
}}

double weighted_sum_real_flat(const real_t* arr, int len) {{
    double sum = 0.0;
    for (int i = 0; i < len; i++) {{
        sum += (double)arr[i] * (double)(i + 1);
    }}
    return sum;
}}

double sum_int_1d(const int* arr) {{
    double sum = 0.0;
    for (int i = 0; i < LEN_1D; i++) {{
        sum += (double)arr[i];
    }}
    return sum;
}}

double abs_sum_int_1d(const int* arr) {{
    double sum = 0.0;
    for (int i = 0; i < LEN_1D; i++) {{
        sum += fabs((double)arr[i]);
    }}
    return sum;
}}

double weighted_sum_int_1d(const int* arr) {{
    double sum = 0.0;
    for (int i = 0; i < LEN_1D; i++) {{
        sum += (double)arr[i] * (double)(i + 1);
    }}
    return sum;
}}

void capture_state_summary(double* state_sum, double* state_abs_sum, double* state_weighted_sum) {{
    *state_sum =
        sum_real_1d(a) + sum_real_1d(b) + sum_real_1d(c) + sum_real_1d(d) + sum_real_1d(e) + sum_real_1d(x) +
        sum_real_2d(aa) + sum_real_2d(bb) + sum_real_2d(cc) + sum_real_2d(tt) +
        sum_real_flat(flat_2d_array, LEN_2D * LEN_2D) + sum_int_1d(indx);

    *state_abs_sum =
        abs_sum_real_1d(a) + abs_sum_real_1d(b) + abs_sum_real_1d(c) + abs_sum_real_1d(d) + abs_sum_real_1d(e) + abs_sum_real_1d(x) +
        abs_sum_real_2d(aa) + abs_sum_real_2d(bb) + abs_sum_real_2d(cc) + abs_sum_real_2d(tt) +
        abs_sum_real_flat(flat_2d_array, LEN_2D * LEN_2D) + abs_sum_int_1d(indx);

    *state_weighted_sum =
        weighted_sum_real_1d(a) + weighted_sum_real_1d(b) + weighted_sum_real_1d(c) + weighted_sum_real_1d(d) + weighted_sum_real_1d(e) + weighted_sum_real_1d(x) +
        weighted_sum_real_2d(aa) + weighted_sum_real_2d(bb) + weighted_sum_real_2d(cc) + weighted_sum_real_2d(tt) +
        weighted_sum_real_flat(flat_2d_array, LEN_2D * LEN_2D) + weighted_sum_int_1d(indx);
}}

// Original function (for comparison)
{original_code}

// Optimized function
{optimized_code}

int main(int argc, char** argv) {{
    int test_original = (argc > 1 && strcmp(argv[1], "original") == 0);
    int arg_offset = test_original ? 2 : 1;
    int arg_a = (argc > arg_offset) ? atoi(argv[arg_offset]) : 1;
    int arg_b = (argc > arg_offset + 1) ? atoi(argv[arg_offset + 1]) : 1;

    struct args_t args;
{arg_setup_code}
    real_t checksum;
    double state_sum, state_abs_sum, state_weighted_sum;
    
    // Initialize arrays
    init_arrays_for_{func_name}();
    
    // Run function
    if (test_original) {{
        checksum = {func_name}_original(&args);
    }} else {{
        checksum = {func_name}(&args);
    }}
    
    capture_state_summary(&state_sum, &state_abs_sum, &state_weighted_sum);
    
    printf("CHECKSUM: %.17g\\n", (double)checksum);
    printf("STATE_SUM: %.17g\\n", state_sum);
    printf("STATE_ABS_SUM: %.17g\\n", state_abs_sum);
    printf("STATE_WEIGHTED_SUM: %.17g\\n", state_weighted_sum);
    
    return 0;
}}
'''


def verify_compilation(code: str, func_name: str, clang_path: str) -> Tuple[bool, str]:
    """
    第一层：编译检查
    使用最小可编译单元模板，包含必要的头文件
    
    Returns:
        (success, error_message)
    """
    # 使用最小可编译单元模板
    compile_unit = MINIMAL_UNIT_TEMPLATE.format(
        func_name=func_name,
        func_code=code,
        support_code=build_support_code(code),
    )
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.c', delete=False) as f:
        f.write(compile_unit)
        temp_file = f.name
    
    try:
        cmd = [
            clang_path,
            '-O3',
            '-c',
            temp_file,
            '-o', '/dev/null'
        ]
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode == 0:
            return True, ""
        else:
            return False, result.stderr
    except Exception as e:
        return False, str(e)
    finally:
        os.unlink(temp_file)


def verify_semantic_equivalence(
    original_code: str,
    optimized_code: str,
    func_name: str,
    clang_path: str,
    tolerance: float = 1e-5
) -> Dict:
    """
    第二层：语义等价性验证
    通过比较优化前后的校验和来验证语义等价性
    
    Returns:
        {
            'equivalent': bool,
            'original_checksum': float,
            'optimized_checksum': float,
            'error': str (if any)
        }
    """
    result = {
        'equivalent': False,
        'original_checksum': None,
        'optimized_checksum': None,
        'original_state_metrics': {},
        'optimized_state_metrics': {},
        'arg_cases': [],
        'arg_case_results': [],
        'error': None
    }
    arg_cases = _get_arg_cases(func_name)
    result['arg_cases'] = [_arg_case_dict(arg_case) for arg_case in arg_cases]
    
    # 构建测试驱动代码
    driver_code = TEST_DRIVER_TEMPLATE.format(
        func_name=func_name,
        original_code=original_code.replace(f'real_t {func_name}', f'real_t {func_name}_original'),
        optimized_code=optimized_code,
        arg_setup_code=_build_driver_arg_setup_code(func_name),
    )
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.c', delete=False) as f:
        f.write(driver_code)
        driver_file = f.name
    
    try:
        # 编译测试驱动
        exe_file = driver_file.replace('.c', '')
        compile_cmd = [
            clang_path,
            '-O3',
            driver_file,
            '-o', exe_file,
            '-lm'
        ]
        
        compile_result = subprocess.run(
            compile_cmd,
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if compile_result.returncode != 0:
            result['error'] = f"测试驱动编译失败: {compile_result.stderr}"
            return result
        
        for arg_case in arg_cases:
            arg_label = _format_arg_case(arg_case)
            arg_a, arg_b = arg_case

            # 运行原始版本
            orig_result = subprocess.run(
                [exe_file, 'original', str(arg_a), str(arg_b)],
                capture_output=True,
                text=True,
                timeout=30
            )
            if orig_result.returncode != 0:
                result['error'] = f"[{arg_label}] 原始版本运行失败: {orig_result.stderr[:200]}"
                return result
            
            # 运行优化版本
            opt_result = subprocess.run(
                [exe_file, str(arg_a), str(arg_b)],
                capture_output=True,
                text=True,
                timeout=30
            )
            if opt_result.returncode != 0:
                result['error'] = f"[{arg_label}] 优化版本运行失败: {opt_result.stderr[:200]}"
                return result
            
            # 解析返回值与全局状态摘要
            orig_metrics = _parse_driver_metrics(orig_result.stdout)
            opt_metrics = _parse_driver_metrics(opt_result.stdout)

            case_result = {
                'arg_info': _arg_case_dict(arg_case),
                'original_checksum': orig_metrics.get('CHECKSUM'),
                'optimized_checksum': opt_metrics.get('CHECKSUM'),
                'original_state_metrics': {
                    key: value for key, value in orig_metrics.items() if key != 'CHECKSUM'
                },
                'optimized_state_metrics': {
                    key: value for key, value in opt_metrics.items() if key != 'CHECKSUM'
                },
                'equivalent': False,
                'error': None,
            }
            result['arg_case_results'].append(case_result)

            comparison_error = _compare_driver_metrics(orig_metrics, opt_metrics, tolerance)
            if comparison_error is not None:
                case_result['error'] = comparison_error
                result['error'] = f"[{arg_label}] {comparison_error}"
                return result

            case_result['equivalent'] = True

        if result['arg_case_results']:
            first_case = result['arg_case_results'][0]
            result['original_checksum'] = first_case['original_checksum']
            result['optimized_checksum'] = first_case['optimized_checksum']
            result['original_state_metrics'] = first_case['original_state_metrics']
            result['optimized_state_metrics'] = first_case['optimized_state_metrics']
        result['equivalent'] = True
        
        return result
        
    except Exception as e:
        result['error'] = f"运行时错误: {str(e)}"
        return result
    finally:
        if os.path.exists(driver_file):
            os.unlink(driver_file)
        if os.path.exists(exe_file):
            os.unlink(exe_file)


_MULTI_INPUT_DRIVER_TEMPLATE = '''/* Multi-input test driver for {func_name} */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <sys/time.h>

#define iterations 1000
#define LEN_1D 32000
#define LEN_2D 256
#define ARRAY_ALIGNMENT 64

struct args_t {{
    struct timeval t1;
    struct timeval t2;
    void * __restrict__ arg_info;
}};

typedef float real_t;

__attribute__((aligned(ARRAY_ALIGNMENT))) real_t flat_2d_array[LEN_2D*LEN_2D];
__attribute__((aligned(ARRAY_ALIGNMENT))) real_t x[LEN_1D];
__attribute__((aligned(ARRAY_ALIGNMENT))) real_t a[LEN_1D],b[LEN_1D],c[LEN_1D],d[LEN_1D],e[LEN_1D];
__attribute__((aligned(ARRAY_ALIGNMENT))) real_t aa[LEN_2D][LEN_2D],bb[LEN_2D][LEN_2D],cc[LEN_2D][LEN_2D],tt[LEN_2D][LEN_2D];
__attribute__((aligned(ARRAY_ALIGNMENT))) int indx[LEN_1D];
real_t* __restrict__ xx;
real_t* yy;

int dummy(real_t a[LEN_1D], real_t b[LEN_1D], real_t c[LEN_1D], real_t d[LEN_1D],
          real_t e[LEN_1D], real_t aa[LEN_2D][LEN_2D], real_t bb[LEN_2D][LEN_2D],
          real_t cc[LEN_2D][LEN_2D], real_t s) {{
    (void)a; (void)b; (void)c; (void)d; (void)e;
    (void)aa; (void)bb; (void)cc; (void)s;
    return 0;
}}

// Helper function f used by some TSVC functions (e.g., s4121)
real_t f(real_t a, real_t b) {{
    return a * b;
}}

void init_arrays(real_t scale) {{
    xx = flat_2d_array;
    yy = flat_2d_array;

    for (int i = 0; i < LEN_1D; i++) {{
        a[i] = scale * (1.0f + i);
        b[i] = scale * (2.0f + i);
        c[i] = scale * (3.0f + i);
        d[i] = scale * (4.0f + i);
        e[i] = scale * (5.0f + i);
        x[i] = scale;
        indx[i] = ((i + 1) % 4) + 1;
    }}
    for (int i = 0; i < LEN_2D; i++) {{
        for (int j = 0; j < LEN_2D; j++) {{
            int flat_idx = i * LEN_2D + j;
            flat_2d_array[flat_idx] = scale * (real_t)(flat_idx + 1) * 0.125f;
            aa[i][j] = scale / (i + 1);
            bb[i][j] = scale / (j + 1);
            cc[i][j] = scale / (i + j + 1);
            tt[i][j] = scale * (real_t)(i - j);
        }}
    }}
}}

int initialise_arrays(const char* name) {{
    (void)name;
    init_arrays(1.0f);
    return 0;
}}

real_t calc_checksum_arr() {{
    real_t sum = 0.0f;
    for (int i = 0; i < LEN_1D; i++) sum += a[i];
    return sum;
}}

real_t calc_checksum(const char* name) {{
    (void)name;
    return calc_checksum_arr();
}}

double sum_real_1d(const real_t* arr) {{
    double sum = 0.0;
    for (int i = 0; i < LEN_1D; i++) sum += (double)arr[i];
    return sum;
}}

double abs_sum_real_1d(const real_t* arr) {{
    double sum = 0.0;
    for (int i = 0; i < LEN_1D; i++) sum += fabs((double)arr[i]);
    return sum;
}}

double weighted_sum_real_1d(const real_t* arr) {{
    double sum = 0.0;
    for (int i = 0; i < LEN_1D; i++) sum += (double)arr[i] * (double)(i + 1);
    return sum;
}}

double sum_real_2d(real_t arr[LEN_2D][LEN_2D]) {{
    double sum = 0.0;
    for (int i = 0; i < LEN_2D; i++) {{
        for (int j = 0; j < LEN_2D; j++) {{
            sum += (double)arr[i][j];
        }}
    }}
    return sum;
}}

double abs_sum_real_2d(real_t arr[LEN_2D][LEN_2D]) {{
    double sum = 0.0;
    for (int i = 0; i < LEN_2D; i++) {{
        for (int j = 0; j < LEN_2D; j++) {{
            sum += fabs((double)arr[i][j]);
        }}
    }}
    return sum;
}}

double weighted_sum_real_2d(real_t arr[LEN_2D][LEN_2D]) {{
    double sum = 0.0;
    int weight = 1;
    for (int i = 0; i < LEN_2D; i++) {{
        for (int j = 0; j < LEN_2D; j++) {{
            sum += (double)arr[i][j] * (double)weight++;
        }}
    }}
    return sum;
}}

double sum_real_flat(const real_t* arr, int len) {{
    double sum = 0.0;
    for (int i = 0; i < len; i++) sum += (double)arr[i];
    return sum;
}}

double abs_sum_real_flat(const real_t* arr, int len) {{
    double sum = 0.0;
    for (int i = 0; i < len; i++) sum += fabs((double)arr[i]);
    return sum;
}}

double weighted_sum_real_flat(const real_t* arr, int len) {{
    double sum = 0.0;
    for (int i = 0; i < len; i++) sum += (double)arr[i] * (double)(i + 1);
    return sum;
}}

double sum_int_1d(const int* arr) {{
    double sum = 0.0;
    for (int i = 0; i < LEN_1D; i++) sum += (double)arr[i];
    return sum;
}}

double abs_sum_int_1d(const int* arr) {{
    double sum = 0.0;
    for (int i = 0; i < LEN_1D; i++) sum += fabs((double)arr[i]);
    return sum;
}}

double weighted_sum_int_1d(const int* arr) {{
    double sum = 0.0;
    for (int i = 0; i < LEN_1D; i++) sum += (double)arr[i] * (double)(i + 1);
    return sum;
}}

void capture_state_summary(double* state_sum, double* state_abs_sum, double* state_weighted_sum) {{
    *state_sum =
        sum_real_1d(a) + sum_real_1d(b) + sum_real_1d(c) + sum_real_1d(d) + sum_real_1d(e) + sum_real_1d(x) +
        sum_real_2d(aa) + sum_real_2d(bb) + sum_real_2d(cc) + sum_real_2d(tt) +
        sum_real_flat(flat_2d_array, LEN_2D * LEN_2D) + sum_int_1d(indx);

    *state_abs_sum =
        abs_sum_real_1d(a) + abs_sum_real_1d(b) + abs_sum_real_1d(c) + abs_sum_real_1d(d) + abs_sum_real_1d(e) + abs_sum_real_1d(x) +
        abs_sum_real_2d(aa) + abs_sum_real_2d(bb) + abs_sum_real_2d(cc) + abs_sum_real_2d(tt) +
        abs_sum_real_flat(flat_2d_array, LEN_2D * LEN_2D) + abs_sum_int_1d(indx);

    *state_weighted_sum =
        weighted_sum_real_1d(a) + weighted_sum_real_1d(b) + weighted_sum_real_1d(c) + weighted_sum_real_1d(d) + weighted_sum_real_1d(e) + weighted_sum_real_1d(x) +
        weighted_sum_real_2d(aa) + weighted_sum_real_2d(bb) + weighted_sum_real_2d(cc) + weighted_sum_real_2d(tt) +
        weighted_sum_real_flat(flat_2d_array, LEN_2D * LEN_2D) + weighted_sum_int_1d(indx);
}}

double relative_diff(double lhs, double rhs) {{
    double diff = fabs(lhs - rhs);
    double base = fmax(fmax(fabs(lhs), fabs(rhs)), 1.0);
    return diff / base;
}}

// Original function
{original_code}

// Optimized function
{optimized_code}

int main(int argc, char** argv) {{
    int arg_a = (argc > 1) ? atoi(argv[1]) : 1;
    int arg_b = (argc > 2) ? atoi(argv[2]) : 1;
    struct args_t args;
{arg_setup_code}
    real_t scales[] = {{1.0f, 2.0f, -1.0f}};
    int n_tests = 3;
    int passed = 0;

    for (int t = 0; t < n_tests; t++) {{
        real_t orig_ret, opt_ret;
        double orig_state_sum, orig_state_abs_sum, orig_state_weighted_sum;
        double opt_state_sum, opt_state_abs_sum, opt_state_weighted_sum;

        init_arrays(scales[t]);
        orig_ret = {func_name}_original(&args);
        capture_state_summary(&orig_state_sum, &orig_state_abs_sum, &orig_state_weighted_sum);

        init_arrays(scales[t]);
        opt_ret = {func_name}(&args);
        capture_state_summary(&opt_state_sum, &opt_state_abs_sum, &opt_state_weighted_sum);

        double max_rel = relative_diff((double)orig_ret, (double)opt_ret);
        double state_sum_rel = relative_diff(orig_state_sum, opt_state_sum);
        double state_abs_rel = relative_diff(orig_state_abs_sum, opt_state_abs_sum);
        double state_weight_rel = relative_diff(orig_state_weighted_sum, opt_state_weighted_sum);
        if (state_sum_rel > max_rel) max_rel = state_sum_rel;
        if (state_abs_rel > max_rel) max_rel = state_abs_rel;
        if (state_weight_rel > max_rel) max_rel = state_weight_rel;

        int ok = (max_rel < 1e-4f);
        printf("TEST%d: ret_orig=%.6f ret_opt=%.6f max_rel=%.2e %s\\n",
               t, (double)orig_ret, (double)opt_ret, max_rel, ok ? "PASS" : "FAIL");
        if (ok) passed++;
    }}

    printf("PASSED %d/%d\\n", passed, n_tests);
    return (passed == n_tests) ? 0 : 1;
}}
'''


def verify_with_multiple_inputs(
    original_code: str,
    optimized_code: str,
    func_name: str,
    clang_path: str
) -> Dict:
    """
    第三层：多输入测试
    使用不同 scale 的数组初始化，验证优化代码在多种输入下的正确性。

    Returns:
        {
            'pass': bool,
            'tests_passed': int,
            'total_tests': int,
            'details': list
        }
    """
    result = {
        'pass': False,
        'tests_passed': 0,
        'total_tests': 0,
        'details': [],
        'arg_cases': []
    }
    arg_cases = _get_arg_cases(func_name)
    result['arg_cases'] = [_arg_case_dict(arg_case) for arg_case in arg_cases]
    result['total_tests'] = len(_RUNTIME_TEST_SCALES) * len(arg_cases)

    driver_code = _MULTI_INPUT_DRIVER_TEMPLATE.format(
        func_name=func_name,
        original_code=original_code.replace(
            f'real_t {func_name}', f'real_t {func_name}_original'
        ),
        optimized_code=optimized_code,
        arg_setup_code=_build_driver_arg_setup_code(func_name),
    )

    with tempfile.NamedTemporaryFile(mode='w', suffix='.c', delete=False) as f:
        f.write(driver_code)
        src_file = f.name

    exe_file = src_file.replace('.c', '')
    try:
        compile_result = subprocess.run(
            [clang_path, '-O2', src_file, '-o', exe_file, '-lm'],
            capture_output=True, text=True, timeout=30
        )
        if compile_result.returncode != 0:
            result['details'].append(f'编译失败: {compile_result.stderr[:200]}')
            return result

        for arg_case in arg_cases:
            arg_label = _format_arg_case(arg_case)
            run_result = subprocess.run(
                [exe_file, str(arg_case[0]), str(arg_case[1])],
                capture_output=True,
                text=True,
                timeout=60
            )

            case_test_lines = 0
            for line in run_result.stdout.splitlines():
                if line.startswith('TEST'):
                    case_test_lines += 1
                    prefixed_line = f"[{arg_label}] {line}"
                    result['details'].append(prefixed_line)
                    if line.endswith('PASS'):
                        result['tests_passed'] += 1
                elif line.startswith('PASSED'):
                    result['details'].append(f"[{arg_label}] {line}")

            if run_result.returncode not in (0, 1):
                result['details'].append(f'[{arg_label}] 运行失败: {run_result.stderr[:200]}')
                return result
            if case_test_lines == 0:
                result['details'].append(f'[{arg_label}] 未产生有效测试输出')
                if run_result.stderr:
                    result['details'].append(f'[{arg_label}] stderr: {run_result.stderr[:200]}')
                return result

        result['pass'] = (result['tests_passed'] == result['total_tests'])
        return result

    except Exception as e:
        result['details'].append(f'运行时错误: {str(e)}')
        return result
    finally:
        if os.path.exists(src_file):
            os.unlink(src_file)
        if os.path.exists(exe_file):
            os.unlink(exe_file)


def full_correctness_verification(
    original_code: str,
    optimized_code: str,
    func_name: str,
    clang_path: str
) -> Dict:
    """
    完整的三层正确性验证
    
    Returns:
        完整的验证结果报告
    """
    report = {
        'func_name': func_name,
        'layer1_compilation': {'passed': False, 'error': None},
        'layer2_semantic': {
            'passed': False, 
            'error': None,
            'original_checksum': None,
            'optimized_checksum': None
        },
        'layer3_runtime': {'passed': False, 'error': None, 'details': []},
        'overall': False
    }
    
    # 第一层：编译检查
    compile_ok, compile_error = verify_compilation(optimized_code, func_name, clang_path)
    report['layer1_compilation']['passed'] = compile_ok
    report['layer1_compilation']['error'] = compile_error
    
    if not compile_ok:
        report['overall'] = False
        return report
    
    # 第二层：语义等价性
    semantic_result = verify_semantic_equivalence(
        original_code, optimized_code, func_name, clang_path
    )
    report['layer2_semantic']['passed'] = semantic_result['equivalent']
    report['layer2_semantic']['error'] = semantic_result.get('error')
    report['layer2_semantic']['original_checksum'] = semantic_result.get('original_checksum')
    report['layer2_semantic']['optimized_checksum'] = semantic_result.get('optimized_checksum')
    report['layer2_semantic']['arg_cases'] = semantic_result.get('arg_cases', [])
    report['layer2_semantic']['arg_case_results'] = semantic_result.get('arg_case_results', [])
    
    if not semantic_result['equivalent']:
        report['overall'] = False
        return report
    
    # 第三层：运行时测试
    runtime_result = verify_with_multiple_inputs(original_code, optimized_code, func_name, clang_path)
    report['layer3_runtime']['passed'] = runtime_result['pass']
    report['layer3_runtime']['details'] = runtime_result.get('details', [])
    report['layer3_runtime']['arg_cases'] = runtime_result.get('arg_cases', [])
    
    # 总体结果
    report['overall'] = (
        report['layer1_compilation']['passed'] and
        report['layer2_semantic']['passed'] and
        report['layer3_runtime']['passed']
    )
    
    return report


# 性能测试驱动模板 - 高精度计时
PERFORMANCE_DRIVER_TEMPLATE = r'''/* Performance benchmark driver for {func_name} */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <math.h>
#include <sys/time.h>

#define iterations 100000
#define LEN_1D 32000
#define LEN_2D 256
#define ARRAY_ALIGNMENT 64
#define WARMUP_RUNS {warmup_runs}
#define TIMING_RUNS {timing_runs}

struct args_t {
    struct timeval t1;
    struct timeval t2;
    void * __restrict__ arg_info;
};

typedef float real_t;

__attribute__((aligned(ARRAY_ALIGNMENT))) real_t flat_2d_array[LEN_2D*LEN_2D];
__attribute__((aligned(ARRAY_ALIGNMENT))) real_t x[LEN_1D];
__attribute__((aligned(ARRAY_ALIGNMENT))) real_t a[LEN_1D],b[LEN_1D],c[LEN_1D],d[LEN_1D],e[LEN_1D];
__attribute__((aligned(ARRAY_ALIGNMENT))) real_t aa[LEN_2D][LEN_2D],bb[LEN_2D][LEN_2D],cc[LEN_2D][LEN_2D],tt[LEN_2D][LEN_2D];
__attribute__((aligned(ARRAY_ALIGNMENT))) int indx[LEN_1D];
real_t* __restrict__ xx;
real_t* yy;

int dummy(real_t a[LEN_1D], real_t b[LEN_1D], real_t c[LEN_1D], real_t d[LEN_1D],
          real_t e[LEN_1D], real_t aa[LEN_2D][LEN_2D], real_t bb[LEN_2D][LEN_2D],
          real_t cc[LEN_2D][LEN_2D], real_t s) {
    (void)a; (void)b; (void)c; (void)d; (void)e;
    (void)aa; (void)bb; (void)cc; (void)s;
    return 0;
}

// Helper function f used by some TSVC functions (e.g., s4121)
real_t f(real_t a, real_t b) {
    return a * b;
}

void init_arrays_for_{func_name}() {
    for (int i = 0; i < LEN_1D; i++) {
        a[i] = 1.0 + i;
        b[i] = 2.0 + i;
        c[i] = 3.0 + i;
        d[i] = 4.0 + i;
        e[i] = 5.0 + i;
        x[i] = 1.0;
    }
    for (int i = 0; i < LEN_2D; i++) {
        for (int j = 0; j < LEN_2D; j++) {
            aa[i][j] = 1.0 / (i+1);
            bb[i][j] = 1.0 / (i+1);
            cc[i][j] = 1.0 / (i+1);
        }
    }
}

int initialise_arrays(const char* name) {
    (void)name;
    init_arrays_for_{func_name}();
    return 0;
}

// High-precision timing using clock_gettime
double get_time_ns() {
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return ts.tv_sec * 1e9 + ts.tv_nsec;
}

// Dummy calc_checksum function for TSVC compatibility
real_t calc_checksum(const char* name) {
    (void)name;
    return 0.0;
}

// Original function
{original_code}

// Optimized function
{optimized_code}

// Compare function for qsort
int compare_double(const void* a, const void* b) {
    double diff = *(double*)a - *(double*)b;
    return (diff > 0) - (diff < 0);
}

int main(int argc, char** argv) {
    int arg_a = (argc > 1) ? atoi(argv[1]) : 1;
    int arg_b = (argc > 2) ? atoi(argv[2]) : 1;

    struct args_t args;
{arg_setup_code}

    double orig_times[TIMING_RUNS];
    double opt_times[TIMING_RUNS];

    // Warmup runs for original
    for (int w = 0; w < WARMUP_RUNS; w++) {
        init_arrays_for_{func_name}();
        {func_name}_original(&args);
    }

    // Timing runs for original
    for (int r = 0; r < TIMING_RUNS; r++) {
        init_arrays_for_{func_name}();
        double start = get_time_ns();
        {func_name}_original(&args);
        double end = get_time_ns();
        orig_times[r] = (end - start) / 1e6;
    }

    // Warmup runs for optimized
    for (int w = 0; w < WARMUP_RUNS; w++) {
        init_arrays_for_{func_name}();
        {func_name}(&args);
    }

    // Timing runs for optimized
    for (int r = 0; r < TIMING_RUNS; r++) {
        init_arrays_for_{func_name}();
        double start = get_time_ns();
        {func_name}(&args);
        double end = get_time_ns();
        opt_times[r] = (end - start) / 1e6;
    }

    // Sort to remove min and max
    qsort(orig_times, TIMING_RUNS, sizeof(double), compare_double);
    qsort(opt_times, TIMING_RUNS, sizeof(double), compare_double);

    // Calculate average (exclude min and max)
    double orig_avg = 0, opt_avg = 0;
    for (int i = 1; i < TIMING_RUNS - 1; i++) {
        orig_avg += orig_times[i];
        opt_avg += opt_times[i];
    }
    orig_avg /= (TIMING_RUNS - 2);
    opt_avg /= (TIMING_RUNS - 2);

    double speedup = orig_avg / opt_avg;

    // Output results in plain format (avoiding JSON parsing issues)
    printf("FUNC_NAME: %s\n", "{func_name}");
    printf("ORIGINAL_TIME_MS: %.6f\n", orig_avg);
    printf("OPTIMIZED_TIME_MS: %.6f\n", opt_avg);
    printf("SPEEDUP: %.4f\n", speedup);
    printf("IMPROVEMENT_PCT: %.2f\n", (speedup - 1.0) * 100);

    return 0;
}
'''


BASELINE_PERFORMANCE_DRIVER_TEMPLATE = r'''/* Baseline performance benchmark driver for {func_name} */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <math.h>
#include <sys/time.h>

#define iterations 100000
#define LEN_1D 32000
#define LEN_2D 256
#define ARRAY_ALIGNMENT 64
#define WARMUP_RUNS {warmup_runs}
#define TIMING_RUNS {timing_runs}

struct args_t {
    struct timeval t1;
    struct timeval t2;
    void * __restrict__ arg_info;
};

typedef float real_t;

__attribute__((aligned(ARRAY_ALIGNMENT))) real_t flat_2d_array[LEN_2D*LEN_2D];
__attribute__((aligned(ARRAY_ALIGNMENT))) real_t x[LEN_1D];
__attribute__((aligned(ARRAY_ALIGNMENT))) real_t a[LEN_1D],b[LEN_1D],c[LEN_1D],d[LEN_1D],e[LEN_1D];
__attribute__((aligned(ARRAY_ALIGNMENT))) real_t aa[LEN_2D][LEN_2D],bb[LEN_2D][LEN_2D],cc[LEN_2D][LEN_2D],tt[LEN_2D][LEN_2D];
__attribute__((aligned(ARRAY_ALIGNMENT))) int indx[LEN_1D];
real_t* __restrict__ xx;
real_t* yy;

int dummy(real_t a[LEN_1D], real_t b[LEN_1D], real_t c[LEN_1D], real_t d[LEN_1D],
          real_t e[LEN_1D], real_t aa[LEN_2D][LEN_2D], real_t bb[LEN_2D][LEN_2D],
          real_t cc[LEN_2D][LEN_2D], real_t s) {
    (void)a; (void)b; (void)c; (void)d; (void)e;
    (void)aa; (void)bb; (void)cc; (void)s;
    return 0;
}

real_t f(real_t a, real_t b) {
    return a * b;
}

void init_arrays_for_{func_name}() {
    for (int i = 0; i < LEN_1D; i++) {
        a[i] = 1.0 + i;
        b[i] = 2.0 + i;
        c[i] = 3.0 + i;
        d[i] = 4.0 + i;
        e[i] = 5.0 + i;
        x[i] = 1.0;
    }
    for (int i = 0; i < LEN_2D; i++) {
        for (int j = 0; j < LEN_2D; j++) {
            aa[i][j] = 1.0 / (i+1);
            bb[i][j] = 1.0 / (i+1);
            cc[i][j] = 1.0 / (i+1);
        }
    }
}

int initialise_arrays(const char* name) {
    (void)name;
    init_arrays_for_{func_name}();
    return 0;
}

double get_time_ns() {
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return ts.tv_sec * 1e9 + ts.tv_nsec;
}

real_t calc_checksum(const char* name) {
    (void)name;
    return 0.0;
}

{original_code}

int compare_double(const void* a, const void* b) {
    double diff = *(double*)a - *(double*)b;
    return (diff > 0) - (diff < 0);
}

int main(int argc, char** argv) {
    int arg_a = (argc > 1) ? atoi(argv[1]) : 1;
    int arg_b = (argc > 2) ? atoi(argv[2]) : 1;

    struct args_t args;
{arg_setup_code}

    double orig_times[TIMING_RUNS];

    for (int w = 0; w < WARMUP_RUNS; w++) {
        init_arrays_for_{func_name}();
        {func_name}(&args);
    }

    for (int r = 0; r < TIMING_RUNS; r++) {
        init_arrays_for_{func_name}();
        double start = get_time_ns();
        {func_name}(&args);
        double end = get_time_ns();
        orig_times[r] = (end - start) / 1e6;
    }

    qsort(orig_times, TIMING_RUNS, sizeof(double), compare_double);

    double orig_avg = 0;
    for (int i = 1; i < TIMING_RUNS - 1; i++) {
        orig_avg += orig_times[i];
    }
    orig_avg /= (TIMING_RUNS - 2);

    printf("FUNC_NAME: %s\n", "{func_name}");
    printf("ORIGINAL_TIME_MS: %.6f\n", orig_avg);
    printf("OPTIMIZED_TIME_MS: %.6f\n", orig_avg);
    printf("SPEEDUP: %.4f\n", 1.0);
    printf("IMPROVEMENT_PCT: %.2f\n", 0.0);

    return 0;
}
'''


def _parse_benchmark_output(output: str) -> Dict:
    """解析性能驱动输出。"""
    parsed = {
        'original_time_ms': None,
        'optimized_time_ms': None,
        'speedup': None,
        'improvement_pct': None,
    }

    for line in output.split('\n'):
        if ':' not in line:
            continue
        key, value = line.split(':', 1)
        key = key.strip()
        value = value.strip()
        if key == 'ORIGINAL_TIME_MS':
            parsed['original_time_ms'] = float(value)
        elif key == 'OPTIMIZED_TIME_MS':
            parsed['optimized_time_ms'] = float(value)
        elif key == 'SPEEDUP':
            parsed['speedup'] = float(value)
        elif key == 'IMPROVEMENT_PCT':
            parsed['improvement_pct'] = float(value)

    return parsed


def _safe_stddev(values) -> Optional[float]:
    """样本数不足时返回 None。"""
    if len(values) < 2:
        return None
    return stdev(values)


def _aggregate_benchmark_batches(func_name: str, batch_results: list[Dict]) -> Dict:
    """聚合多批次 benchmark 结果。"""
    original_samples = [item['original_time_ms'] for item in batch_results]
    optimized_samples = [item['optimized_time_ms'] for item in batch_results]
    speedup_samples = [item['speedup'] for item in batch_results]
    improvement_samples = [item['improvement_pct'] for item in batch_results]

    return {
        'success': True,
        'func_name': func_name,
        'batch_count': len(batch_results),
        'batches': batch_results,
        'original_time_ms': mean(original_samples),
        'optimized_time_ms': mean(optimized_samples),
        'speedup': mean(speedup_samples),
        'improvement_pct': mean(improvement_samples),
        'original_time_median_ms': median(original_samples),
        'optimized_time_median_ms': median(optimized_samples),
        'speedup_median': median(speedup_samples),
        'improvement_pct_median': median(improvement_samples),
        'original_time_stddev_ms': _safe_stddev(original_samples),
        'optimized_time_stddev_ms': _safe_stddev(optimized_samples),
        'speedup_stddev': _safe_stddev(speedup_samples),
        'improvement_pct_stddev': _safe_stddev(improvement_samples),
        'error': None,
    }


def _aggregate_benchmark_arg_cases(
    func_name: str,
    case_results: list[Dict],
    per_case_batches: int,
) -> Dict:
    """聚合多组 arg_info 的 benchmark 结果，并保留逐 case 统计。"""
    all_batches = []
    arg_case_summaries = []

    for case_item in case_results:
        arg_case = case_item['arg_case']
        case_summary = case_item['summary']
        arg_info = _arg_case_dict(arg_case)
        tagged_batches = []

        for batch_item in case_summary.get('batches', []):
            tagged_batch = dict(batch_item)
            tagged_batch['arg_info'] = arg_info
            tagged_batch['case_batch'] = tagged_batch.get('batch')
            tagged_batch['sample_index'] = len(all_batches) + 1
            tagged_batches.append(tagged_batch)
            all_batches.append(tagged_batch)

        arg_case_summaries.append({
            'arg_info': arg_info,
            'batch_count': case_summary.get('batch_count', 0),
            'original_time_ms': case_summary.get('original_time_ms'),
            'optimized_time_ms': case_summary.get('optimized_time_ms'),
            'speedup': case_summary.get('speedup'),
            'improvement_pct': case_summary.get('improvement_pct'),
            'original_time_median_ms': case_summary.get('original_time_median_ms'),
            'optimized_time_median_ms': case_summary.get('optimized_time_median_ms'),
            'speedup_median': case_summary.get('speedup_median'),
            'improvement_pct_median': case_summary.get('improvement_pct_median'),
            'original_time_stddev_ms': case_summary.get('original_time_stddev_ms'),
            'optimized_time_stddev_ms': case_summary.get('optimized_time_stddev_ms'),
            'speedup_stddev': case_summary.get('speedup_stddev'),
            'improvement_pct_stddev': case_summary.get('improvement_pct_stddev'),
            'batches': tagged_batches,
        })

    aggregated = _aggregate_benchmark_batches(func_name, all_batches)
    aggregated['batch_count'] = per_case_batches
    aggregated['arg_case_count'] = len(arg_case_summaries)
    aggregated['sample_count'] = len(all_batches)
    aggregated['benchmark_scope'] = 'batches_only' if len(arg_case_summaries) == 1 else 'arg_cases_x_batches'
    aggregated['arg_cases'] = [item['arg_info'] for item in arg_case_summaries]
    aggregated['arg_case_results'] = arg_case_summaries
    return aggregated


def run_performance_benchmark(
    original_code: str,
    optimized_code: str,
    func_name: str,
    clang_path: str,
    warmup_runs: int = config.DEFAULT_BENCHMARK_WARMUP_RUNS,
    timing_runs: int = config.DEFAULT_BENCHMARK_TIMING_RUNS,
    batches: int = config.DEFAULT_BENCHMARK_BATCHES,
    **benchmark_protocol_metadata,
) -> Dict:
    """
    性能基准测试
    对比原始代码和优化后代码的执行时间

    Returns:
        {
            'success': bool,
            'func_name': str,
            'original_time_ms': float,
            'optimized_time_ms': float,
            'speedup': float,
            'improvement_pct': float,
            'batch_count': int,
            'original_time_median_ms': float,
            'optimized_time_median_ms': float,
            'speedup_median': float,
            'speedup_stddev': float,
            'error': str (if any)
        }
    """
    result = {
        'success': False,
        'func_name': func_name,
        'protocol_name': benchmark_protocol_metadata.get('protocol_name'),
        'protocol_role': benchmark_protocol_metadata.get('protocol_role'),
        'protocol_display_name': benchmark_protocol_metadata.get('display_name'),
        'paper_main_table_eligible': benchmark_protocol_metadata.get('paper_main_table_eligible'),
        'batch_count': 0,
        'warmup_runs': warmup_runs,
        'timing_runs': timing_runs,
        'batches': [],
        'arg_cases': [],
        'arg_case_results': [],
        'arg_case_count': 0,
        'sample_count': 0,
        'benchmark_scope': 'batches_only',
        'original_time_ms': None,
        'optimized_time_ms': None,
        'speedup': None,
        'improvement_pct': None,
        'original_time_median_ms': None,
        'optimized_time_median_ms': None,
        'speedup_median': None,
        'improvement_pct_median': None,
        'original_time_stddev_ms': None,
        'optimized_time_stddev_ms': None,
        'speedup_stddev': None,
        'improvement_pct_stddev': None,
        'error': None
    }

    if warmup_runs < 0:
        result['error'] = "warmup_runs 不能小于 0"
        return result
    if timing_runs < 3:
        result['error'] = "timing_runs 不能小于 3，否则无法执行去极值平均"
        return result
    if batches < 1:
        result['error'] = "batches 不能小于 1"
        return result

    arg_cases = _get_arg_cases(func_name)
    result['arg_cases'] = [_arg_case_dict(arg_case) for arg_case in arg_cases]
    result['arg_case_count'] = len(arg_cases)
    result['benchmark_scope'] = 'batches_only' if len(arg_cases) == 1 else 'arg_cases_x_batches'

    same_code = original_code.strip() == optimized_code.strip()

    if same_code:
        driver_code = BASELINE_PERFORMANCE_DRIVER_TEMPLATE
        driver_code = driver_code.replace('{func_name}', func_name)
        driver_code = driver_code.replace('{warmup_runs}', str(warmup_runs))
        driver_code = driver_code.replace('{timing_runs}', str(timing_runs))
        driver_code = driver_code.replace('{original_code}', original_code)
        driver_code = driver_code.replace('{arg_setup_code}', _build_driver_arg_setup_code(func_name))
    else:
        original_code_renamed = original_code.replace(
            f'real_t {func_name}', f'real_t {func_name}_original'
        )

        driver_code = PERFORMANCE_DRIVER_TEMPLATE
        driver_code = driver_code.replace('{func_name}', func_name)
        driver_code = driver_code.replace('{warmup_runs}', str(warmup_runs))
        driver_code = driver_code.replace('{timing_runs}', str(timing_runs))
        driver_code = driver_code.replace('{original_code}', original_code_renamed)
        driver_code = driver_code.replace('{optimized_code}', optimized_code)
        driver_code = driver_code.replace('{arg_setup_code}', _build_driver_arg_setup_code(func_name))

    with tempfile.NamedTemporaryFile(mode='w', suffix='.c', delete=False) as f:
        f.write(driver_code)
        driver_file = f.name

    exe_file = driver_file.replace('.c', '')
    try:
        # 编译测试驱动
        compile_cmd = [
            clang_path,
            '-O3',
            driver_file,
            '-o', exe_file,
            '-lm'
        ]

        compile_result = subprocess.run(
            compile_cmd,
            capture_output=True,
            text=True,
            timeout=30
        )

        if compile_result.returncode != 0:
            result['error'] = f"性能测试驱动编译失败: {compile_result.stderr}"
            return result

        case_results = []
        for arg_case in arg_cases:
            arg_a, arg_b = arg_case
            arg_label = _format_arg_case(arg_case)
            case_batch_results = []

            for batch_index in range(batches):
                run_result = subprocess.run(
                    [exe_file, str(arg_a), str(arg_b)],
                    capture_output=True,
                    text=True,
                    timeout=120
                )

                if run_result.returncode != 0:
                    result['error'] = (
                        f"[{arg_label}] 性能测试运行失败(batch={batch_index + 1}): "
                        f"{run_result.stderr}"
                    )
                    return result

                try:
                    output = run_result.stdout.strip()
                    parsed = _parse_benchmark_output(output)
                    if not all(
                        parsed[key] is not None
                        for key in ['original_time_ms', 'optimized_time_ms', 'speedup', 'improvement_pct']
                    ):
                        result['error'] = (
                            f"[{arg_label}] 解析不完整(batch={batch_index + 1})，输出: {output[:200]}"
                        )
                        return result
                    parsed['batch'] = batch_index + 1
                    parsed['arg_info'] = _arg_case_dict(arg_case)
                    case_batch_results.append(parsed)
                except Exception as e:
                    result['error'] = (
                        f"[{arg_label}] 解析性能数据失败(batch={batch_index + 1}): "
                        f"{e}, 输出: {run_result.stdout[:200]}"
                    )
                    return result

            case_results.append({
                'arg_case': arg_case,
                'summary': _aggregate_benchmark_batches(func_name, case_batch_results),
            })

        result.update(_aggregate_benchmark_arg_cases(func_name, case_results, batches))
        result['warmup_runs'] = warmup_runs
        result['timing_runs'] = timing_runs
        return result

    except Exception as e:
        result['error'] = f"运行时错误: {str(e)}"
        return result
    finally:
        if os.path.exists(driver_file):
            os.unlink(driver_file)
        if os.path.exists(exe_file):
            os.unlink(exe_file)


# 边界条件测试驱动模板 - 测试极端情况
_BOUNDARY_TEST_DRIVER_TEMPLATE = r'''/* Boundary condition test driver for {func_name} */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <math.h>
#include <sys/time.h>
#include <stdint.h>

// Use same array setup as other tests
#define ARRAY_ALIGNMENT 64
#define LEN_1D 32000
#define LEN_2D 256

struct args_t {
    struct timeval t1;
    struct timeval t2;
    void * __restrict__ arg_info;
};

typedef float real_t;

// Global arrays (same as TSVC test templates)
__attribute__((aligned(ARRAY_ALIGNMENT))) real_t flat_2d_array[LEN_2D*LEN_2D];
__attribute__((aligned(ARRAY_ALIGNMENT))) real_t x[LEN_1D];
__attribute__((aligned(ARRAY_ALIGNMENT))) real_t a[LEN_1D],b[LEN_1D],c[LEN_1D],d[LEN_1D],e[LEN_1D];
__attribute__((aligned(ARRAY_ALIGNMENT))) real_t aa[LEN_2D][LEN_2D],bb[LEN_2D][LEN_2D],cc[LEN_2D][LEN_2D],tt[LEN_2D][LEN_2D];
__attribute__((aligned(ARRAY_ALIGNMENT))) int indx[LEN_1D];
real_t* __restrict__ xx;
real_t* yy;
int current_len_1d = LEN_1D;  // Track actual test length
int current_iterations = 0;    // Track actual iterations

// Helper function f used by some TSVC functions (e.g., s4121)
real_t f(real_t a, real_t b) {
    return a * b;
}

// Dummy function - same signature as TSVC
int dummy(real_t a[LEN_1D], real_t b[LEN_1D], real_t c[LEN_1D], real_t d[LEN_1D],
          real_t e[LEN_1D], real_t aa[LEN_2D][LEN_2D], real_t bb[LEN_2D][LEN_2D],
          real_t cc[LEN_2D][LEN_2D], real_t s) {
    (void)a; (void)b; (void)c; (void)d; (void)e;
    (void)aa; (void)bb; (void)cc; (void)s;
    return 0;
}

// Initialize arrays with specific pattern and effective length
void init_arrays_pattern(int effective_len_1d, int effective_len_2d, real_t scale, int use_special_values) {
    current_len_1d = effective_len_1d;

    // Only initialize up to effective length
    for (int i = 0; i < effective_len_1d && i < LEN_1D; i++) {
        if (use_special_values && i == effective_len_1d / 4) {
            a[i] = INFINITY;  // +Inf
        } else if (use_special_values && i == effective_len_1d / 2) {
            a[i] = -INFINITY; // -Inf
        } else if (use_special_values && i == 3 * effective_len_1d / 4) {
            a[i] = NAN;       // NaN
        } else {
            a[i] = scale * (1.0f + i);
        }
        b[i] = scale * (2.0f + i);
        c[i] = scale * (3.0f + i);
        d[i] = scale * (4.0f + i);
        e[i] = scale * (5.0f + i);
        x[i] = scale;
        indx[i] = i;
    }

    // Initialize rest with zeros to avoid noise
    for (int i = effective_len_1d; i < LEN_1D; i++) {
        a[i] = 0.0f;
        b[i] = 0.0f;
        c[i] = 0.0f;
        d[i] = 0.0f;
        e[i] = 0.0f;
        x[i] = 0.0f;
    }

    for (int i = 0; i < effective_len_2d && i < LEN_2D; i++) {
        for (int j = 0; j < effective_len_2d && j < LEN_2D; j++) {
            aa[i][j] = scale / (i + 1);
            bb[i][j] = scale / (i + 1);
            cc[i][j] = scale / (i + 1);
        }
    }
}

// Calculate checksum only for effective length
real_t calc_checksum_arr() {
    real_t sum = 0.0f;
    for (int i = 0; i < current_len_1d && i < LEN_1D; i++) {
        // Handle NaN/Inf gracefully - skip them
        if (!isnan(a[i]) && !isinf(a[i])) {
            sum += a[i];
        }
    }
    return sum;
}

// Override iterations for boundary testing
int iterations = 100000;

// TSVC-compatible wrappers
int initialise_arrays(const char* name) {
    (void)name;
    return 0;
}

real_t calc_checksum(const char* name) {
    (void)name;
    return calc_checksum_arr();
}

// Original function
{original_code}

// Optimized function
{optimized_code}

// Run a single test case
int run_test_case(int test_id, int effective_len, int effective_len_2d, int iters, int use_special, int arg_a, int arg_b) {
    struct args_t args;
{arg_setup_code}

    // Set global iterations for this test
    iterations = iters;
    current_iterations = iters;

    // Run original
    init_arrays_pattern(effective_len, effective_len_2d, 1.0f, use_special);
    real_t orig_checksum = {func_name}_original(&args);

    // Run optimized
    init_arrays_pattern(effective_len, effective_len_2d, 1.0f, use_special);
    real_t opt_checksum = {func_name}(&args);

    // Compare (use larger tolerance for special values)
    float diff = fabsf(orig_checksum - opt_checksum);
    float rel = (fabsf(orig_checksum) > 1e-10f) ? diff / fabsf(orig_checksum) : diff;
    int passed = (rel < 1e-3f);  // Slightly relaxed tolerance for boundary conditions

    const char* desc = "";
    switch(test_id) {
        case 0: desc = "Empty arrays (len=0)"; break;
        case 1: desc = "Single element (len=1)"; break;
        case 2: desc = "16 elements (cache line)"; break;
        case 3: desc = "Iterations=0"; break;
        case 4: desc = "Iterations=1"; break;
        case 5: desc = "Iterations=2"; break;
        case 6: desc = "Special values (NaN/Inf)"; break;
        default: desc = "Unknown"; break;
    }

    printf("TEST%d [%s]: len=%d iter=%d orig=%.6f opt=%.6f rel_diff=%.2e %s\n",
           test_id, desc, effective_len, iters, orig_checksum, opt_checksum,
           rel, passed ? "PASS" : "FAIL");

    return passed;
}

int main(int argc, char** argv) {
    int arg_a = (argc > 1) ? atoi(argv[1]) : 1;
    int arg_b = (argc > 2) ? atoi(argv[2]) : 1;

    printf("=== Boundary Condition Tests for {func_name} ===\n\n");

    int total_tests = 7;
    int passed = 0;

    // Test 0: Empty arrays (effective_len=0)
    passed += run_test_case(0, 0, 0, 1, 0, arg_a, arg_b);

    // Test 1: Single element
    passed += run_test_case(1, 1, 1, 10, 0, arg_a, arg_b);

    // Test 2: Cache line boundary (16 floats = 64 bytes)
    passed += run_test_case(2, 16, 16, 100, 0, arg_a, arg_b);

    // Test 3: Zero iterations
    passed += run_test_case(3, 100, 16, 0, 0, arg_a, arg_b);

    // Test 4: Single iteration
    passed += run_test_case(4, 100, 16, 1, 0, arg_a, arg_b);

    // Test 5: Two iterations
    passed += run_test_case(5, 100, 16, 2, 0, arg_a, arg_b);

    // Test 6: Special values (NaN, Inf)
    passed += run_test_case(6, 100, 16, 10, 1, arg_a, arg_b);

    printf("\n=== Results: PASSED %d/%d ===\n", passed, total_tests);

    return (passed == total_tests) ? 0 : 1;
}
'''


def verify_with_boundary_conditions(
    original_code: str,
    optimized_code: str,
    func_name: str,
    clang_path: str
) -> Dict:
    """
    边界条件测试
    测试空数组、小数组、特殊数值、迭代次数边界等极端情况

    Returns:
        {
            'pass': bool,
            'tests_passed': int,
            'total_tests': int,
            'details': list
        }
    """
    result = {
        'pass': False,
        'tests_passed': 0,
        'total_tests': 0,
        'details': [],
        'arg_cases': []
    }
    arg_cases = _get_arg_cases(func_name)
    result['arg_cases'] = [_arg_case_dict(arg_case) for arg_case in arg_cases]
    result['total_tests'] = _BOUNDARY_TEST_COUNT * len(arg_cases)

    # 准备代码替换（处理函数名）
    original_code_renamed = original_code.replace(
        f'real_t {func_name}', f'real_t {func_name}_original'
    )

    # 使用 replace 而不是 format 来避免花括号问题
    driver_code = _BOUNDARY_TEST_DRIVER_TEMPLATE
    driver_code = driver_code.replace('{func_name}', func_name)
    driver_code = driver_code.replace('{original_code}', original_code_renamed)
    driver_code = driver_code.replace('{optimized_code}', optimized_code)
    driver_code = driver_code.replace('{arg_setup_code}', _build_driver_arg_setup_code(func_name))

    with tempfile.NamedTemporaryFile(mode='w', suffix='.c', delete=False) as f:
        f.write(driver_code)
        src_file = f.name

    exe_file = src_file.replace('.c', '')
    try:
        # 编译测试驱动
        compile_result = subprocess.run(
            [clang_path, '-O2', src_file, '-o', exe_file, '-lm'],
            capture_output=True, text=True, timeout=30
        )
        if compile_result.returncode != 0:
            result['details'].append(f'编译失败: {compile_result.stderr[:200]}')
            return result

        # 运行边界条件测试
        for arg_case in arg_cases:
            arg_label = _format_arg_case(arg_case)
            run_result = subprocess.run(
                [exe_file, str(arg_case[0]), str(arg_case[1])],
                capture_output=True,
                text=True,
                timeout=60
            )

            case_test_lines = 0
            for line in run_result.stdout.splitlines():
                if line.startswith('TEST'):
                    case_test_lines += 1
                    result['details'].append(f'[{arg_label}] {line}')
                    if line.endswith('PASS'):
                        result['tests_passed'] += 1
                elif line.startswith('=== Results:'):
                    result['details'].append(f'[{arg_label}] {line}')

            if run_result.returncode not in (0, 1):
                result['details'].append(f'[{arg_label}] 运行失败: {run_result.stderr[:200]}')
                return result
            if case_test_lines == 0:
                result['details'].append(f'[{arg_label}] 未产生有效测试输出')
                if run_result.stderr:
                    result['details'].append(f'[{arg_label}] stderr: {run_result.stderr[:200]}')
                return result

        result['pass'] = (result['tests_passed'] == result['total_tests'])
        return result

    except Exception as e:
        result['details'].append(f'运行时错误: {str(e)}')
        return result
    finally:
        if os.path.exists(src_file):
            os.unlink(src_file)
        if os.path.exists(exe_file):
            os.unlink(exe_file)


def format_verification_report(report: Dict) -> str:
    """格式化验证报告"""
    lines = []
    lines.append("=" * 60)
    lines.append("正确性验证报告")
    lines.append("=" * 60)
    
    # 第一层
    l1 = report['layer1_compilation']
    status = "✅" if l1.get('passed') else "❌"
    lines.append(f"\n{status} 第一层：编译检查")
    if l1.get('error'):
        lines.append(f"   错误: {l1['error'][:100]}")
    
    # 第二层
    l2 = report['layer2_semantic']
    status = "✅" if l2['passed'] else "❌"
    lines.append(f"\n{status} 第二层：语义等价性")
    if l2.get('original_checksum') is not None:
        lines.append(f"   原始校验和: {l2['original_checksum']:.6f}")
        lines.append(f"   优化校验和: {l2['optimized_checksum']:.6f}")
    if l2.get('error'):
        lines.append(f"   错误: {l2['error']}")
    
    # 第三层
    l3 = report['layer3_runtime']
    status = "✅" if l3.get('passed') else "❌"
    lines.append(f"\n{status} 第三层：运行时测试")
    for detail in l3.get('details', []):
        lines.append(f"   - {detail}")
    
    # 总体
    lines.append("\n" + "=" * 60)
    overall = "✅ 通过" if report['overall'] else "❌ 失败"
    lines.append(f"总体结果: {overall}")
    lines.append("=" * 60)
    
    return "\n".join(lines)


if __name__ == '__main__':
    # 测试代码
    print("正确性验证模块已加载")
