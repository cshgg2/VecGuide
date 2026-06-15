# VecGuide 项目文档

> 当前 `README.md` 主要保留代码层说明。项目级文件索引、研究材料、实验归档、临时记录和论文目录说明见 [`PROJECT_INDEX.md`](PROJECT_INDEX.md)。复查已有结果和复现实验的最短说明见 [`docs/reproduction.md`](docs/reproduction.md)。

## 项目概述

论文题目暂定为：**VecGuide: Compiler-Diagnostic-Guided LLM Source Rewriting for Automatic Vectorization**。

**VecGuide** 是一个编译诊断引导的大语言模型源码重写实验系统，目标是帮助 C/C++ 循环暴露更多自动向量化机会。系统分析 Clang 的未向量化诊断信息，结合案例卡约束，引导大语言模型生成可验证的源码候选。

## 核心特性

- **自动诊断分析**：从 Clang 编译器提取循环向量化失败的诊断信息
- **智能代码优化**：利用大语言模型应用各种向量化优化技术
- **多轮迭代优化**：支持多轮反馈迭代，逐步消除向量化障碍
- **正确性保证**：三层验证机制确保优化后的代码语义等价
- **性能评估**：自动对比优化前后的执行性能

## Public/Private Boundary

The public repository contains code, reproducibility notes, selected run artifacts, and sanitized evidence documents under `docs/`. Local planning notes, weekly reports, terminal transcripts, thesis drafts, and scratch archives may exist in the working tree, but are ignored by git through `.gitignore`.

If a local note becomes useful for collaboration, summarize it into a public document under `docs/` rather than committing the private file directly.

## 项目结构

```
VecGuide/
├── main.py                    # 统一入口，提供分析/优化/评估一站式工作流
├── config.py                  # 全局配置管理
├── data_collector.py          # 数据收集器：提取 Clang 向量化诊断信息
├── optimizer_pipeline.py      # 优化流水线：多轮迭代优化核心
├── evaluate_optimization.py   # 优化结果评估：检查向量化成功率
├── correctness_verifier.py    # 正确性验证：三层验证机制
├── benchmark.py               # 性能基准测试
├── state_manager.py           # 优化状态管理
├── logger.py                  # 日志模块
├── verify_cli.py              # 正确性验证 CLI
├── boundary_test.py           # 边界条件测试
├── prompts/                   # Prompt 工程模块
│   ├── __init__.py
│   ├── knowledge_base.py      # 向量化知识库
│   ├── templates.py           # Prompt 模板
│   └── examples.py            # Few-shot 示例
├── TSVC_2/                    # TSVC 测试套件
│   ├── src/
│   │   ├── tsvc.c            # 测试用例源文件
│   │   ├── common.h          # 公共头文件
│   │   └── ...
│   └── README.md
├── docs/                      # 文档入口和复现说明
├── experiments/runs/          # run 级正式实验归档
└── problem_map.json           # 问题映射文件
```

## 核心模块说明

### 1. 数据收集模块 (data_collector.py)

从 Clang 编译器提取循环向量化失败的诊断信息：

- 解析编译器的 `-Rpass-missed=loop-vectorize` 输出
- 按函数归类诊断信息
- 构建问题映射（Problem Map），标注严重程度

**关键函数：**
- `extract_functions_from_source()` - 提取源文件中的所有函数
- `run_clang_analysis()` - 运行 Clang 分析
- `parse_diagnostics()` - 解析诊断输出
- `build_problem_map()` - 构建问题映射

### 2. 优化流水线 (optimizer_pipeline.py)

整合多轮优化流程的核心模块：

- 调用 LLM API（DeepSeek/Anthropic 兼容接口）
- 管理多轮迭代优化
- 自动评估每轮优化结果
- 集成正确性验证

**关键函数：**
- `optimize_single_function()` - 单函数多轮优化
- `run_batch_optimization()` - 批量优化
- `call_deepseek_anthropic_api()` - LLM API 调用

### 3. 评估模块 (evaluate_optimization.py)

评估优化后的代码向量化情况：

- 创建最小可编译单元进行精确评估
- 解析 Clang 向量化成功/失败的诊断信息
- 判断代码是否完全向量化

**关键函数：**
- `analyze_single_function()` - 分析单个函数
- `parse_diagnostics()` - 解析向量化诊断
- `check_compilation_success()` - 编译检查

### 4. 正确性验证 (correctness_verifier.py)

三层正确性保证机制：

1. **编译检查**：确保代码可编译
2. **语义等价性验证**：通过校验和比对验证语义等价
3. **运行时测试**：多输入测试验证鲁棒性

**关键函数：**
- `verify_compilation()` - 第一层：编译检查
- `verify_semantic_equivalence()` - 第二层：校验和比对
- `verify_with_multiple_inputs()` - 第三层：多输入测试
- `full_correctness_verification()` - 完整三层验证

### 5. Prompt 工程模块 (prompts/)

#### knowledge_base.py - 向量化知识库

包含以下知识：

- **COMPILER_HINTS**: 编译器指令（pragma、restrict 等）
- **COMPILER_OPTIONS**: 编译选项知识
- **VECTORIZATION_PATTERNS**: 向量化障碍模式与解决方案
- **FUNDAMENTAL_LIMITATIONS**: 本质限制检测

**关键函数：**
- `analyze_issue_depth()` - 深度分析向量化失败原因
- `check_fundamental_limitation()` - 检测本质限制
- `get_compiler_hints_guide()` - 获取编译器指令指南

#### templates.py - Prompt 模板

提供各种场景下的结构化 Prompt：

- `SYSTEM_PROMPT_BASE` - 基础系统提示
- `SYSTEM_PROMPT_MULTI_ROUND` - 多轮优化系统提示
- `build_optimization_prompt()` - 构建优化 Prompt
- `build_retry_prompt()` - 编译失败重试 Prompt

#### examples.py - Few-shot 示例

成功优化案例库，包含：

- 标量依赖案例
- 归纳变量案例
- 别名分析案例
- 控制流案例

### 6. 状态管理 (state_manager.py)

管理多轮优化历史记录：

- 记录每轮优化的代码和结果
- 跟踪最佳结果
- 管理函数优化状态（pending/optimizing/success/partial_success/failed）

**关键函数：**
- `load_state()` / `save_state()` - 状态加载/保存
- `add_round()` - 添加优化轮次记录
- `get_best_code()` - 获取最佳代码
- `determine_final_status()` - 确定最终状态

## 使用方法

### 快速开始

1. **运行完整流水线**（分析 → 优化 → 评估）：
```bash
python main.py pipeline
```

2. **只分析代码**：
```bash
python main.py analyze
```

3. **优化指定函数**：
```bash
# 单轮优化
python main.py optimize s111 s112 --single-round

# 多轮优化（默认3轮）
python main.py optimize s111 --rounds 3

# 基于问题映射自动优化
python main.py optimize --from-analysis problem_map.json --rounds 3
```

4. **评估优化结果**：
```bash
# 评估所有优化后的代码
python main.py evaluate

# 评估指定函数
python main.py evaluate s111 s112
```

5. **验证正确性**：
```bash
# 验证指定函数
python main.py verify s122

# 验证所有轮次
python main.py verify s122 --all-rounds
```

6. **性能测试**：
```bash
# 测试所有成功优化的函数
python main.py benchmark

# 测试指定函数
python main.py benchmark s122 s111

# 生成 Markdown 报告
python main.py benchmark --md --csv
```

### 配置说明

在 `config.py` 中修改配置：

```python
class Config:
    # API 配置
    DEEPSEEK_API_KEY = "your-api-key"
    ANTHROPIC_MODEL = "glm-4.7"
    DEEPSEEK_BASE_URL = "https://open.bigmodel.cn/api/anthropic"

    # 编译器配置
    DEFAULT_CLANG_PATH = "/path/to/clang"

    # 源代码配置
    DEFAULT_SOURCE_FILE = "./TSVC_2/src/tsvc.c"

    # 优化配置
    DEFAULT_MAX_ROUNDS = 3
```

或通过环境变量配置：
```bash
export DEEPSEEK_API_KEY="your-api-key"
export CLANG_PATH="/path/to/clang"
export SOURCE_FILE="./TSVC_2/src/tsvc.c"
export MAX_ROUNDS=3
```

## 向量化优化技术

### 低成本方案（优先尝试）

1. **restrict 关键字**：消除别名分析障碍
   ```c
   real_t * __restrict__ a_ = a;
   ```

2. **vectorize pragma**：强制编译器向量化
   ```c
   #pragma clang loop vectorize(enable)
   for (int i = 0; i < n; i++) { ... }
   ```

3. **interleave pragma**：增加指令级并行
   ```c
   #pragma clang loop interleave(enable)
   ```

### 高成本方案（当低成本方案无效时使用）

4. **循环拆分（Loop Distribution）**：
   ```c
   // 拆分前：混合依赖
   for (int i = 0; i < n; i++) {
       a[i] = b[i] + c[i];  // 无依赖，可向量化
       d[i] = d[i-1] * e[i]; // 有依赖，不可向量化
   }

   // 拆分后：分离可向量化和不可向量化部分
   for (int i = 0; i < n; i++) {
       a[i] = b[i] + c[i];
   }
   for (int i = 0; i < n; i++) {
       d[i] = d[i-1] * e[i];
   }
   ```

5. **索引预计算**：
   ```c
   // 预计算阶段
   int k_values[LEN_1D];
   for (int i = 0; i < n; i++) {
       k += j;
       k_values[i] = k;
   }
   // 向量化数据访问阶段
   for (int i = 0; i < n; i++) {
       a[i] = b[k_values[i]];
   }
   ```

6. **条件转换**：
   ```c
   // 转换前
   if (b[i] > 0) {
       a[i] = b[i] * c[i];
   }
   // 转换后
   a[i] = (b[i] > 0) ? (b[i] * c[i]) : a[i];
   ```

## 优化状态定义

| 状态 | 说明 |
|------|------|
| `pending` | 待优化 |
| `optimizing` | 优化进行中 |
| `success` | 完全向量化 + 正确性通过 |
| `partial_success` | 部分向量化 + 正确性通过 |
| `failed` | 优化失败或未通过正确性验证 |

## 关键改进点

### 1. 区分"源码修改" vs "编译器指令"

- 变量边界、别名分析问题 → 优先使用 pragma/restrict
- 归纳变量、真依赖问题 → 必须重构代码

### 2. 深度诊断分析

- 提供根因分析
- 解决方案分类（compiler_hint_first / source_change_required）
- 成功率评估

### 3. 三层正确性保证

1. 编译检查
2. 语义等价性验证（校验和比对）
3. 运行时多输入测试

### 4. 本质限制检测

识别无法通过简单重构解决的向量化障碍：
- 真依赖（True Dependency）
- 动态内存访问
- 强制向量化也失败的情况

## 依赖安装

```bash
pip install -r acpo_train_requirements.txt
```

核心依赖：
- `httpx` - HTTP 客户端（用于 LLM API 调用）
- `numpy`, `pandas` - 数据处理
- `matplotlib`, `seaborn` - 可视化

## 注意事项

1. **正确性优先**：宁可不向量化，也不能破坏代码正确性
2. **dummy() 函数**：不可移动其在循环中的调用位置
3. **数组访问**：确保优化后所有数组访问都在合法范围内
4. **浮点精度**：注意运算顺序改变可能导致的精度损失

## 作者与致谢

- 项目名称：VecGuide
- 基于 TSVC 2 (Test Suite for Vectorizing Compilers)
- 使用 DeepSeek/Anthropic API 进行代码优化

## 许可证

参考 TSVC_2/license.txt
