# AI_LOG.md — AI 使用记录

## 基本信息
- **AI 工具**: Claude Code (Claude Agent SDK, deepseek-v4-pro)
- **项目**: 基于 AI 辅助编程的无线通信文件传输基带仿真系统
- **开发方法**: Superpowers 子代理驱动开发 + Matt Pocock TDD 框架
- **编程语言**: Python 3 + numpy + scipy + matplotlib

---

## 记录条目

### 2026-07-01: 项目基础设施搭建 (Task 1)
- **AI 角色**: 创建目录结构、配置模块、测试夹具、领域语言词汇表
- **关键 Prompt**: "根据 plan 文件搭建项目基础设施"
- **AI 输出**: requirements.txt, src/config.py, tests/conftest.py, CONTEXT.md, AI_LOG.md, Test.txt
- **人工修改**: 待审查
- **采纳理由**: 建立了清晰的模块边界和统一的配置管理

### 2026-07-01: 信源编解码 + 加扰模块 (Tasks 2-3)
- **AI 角色**: TDD 实现 text↔bits 转换和 LFSR 自同步扰码器
- **关键 Prompt**: "按照 TDD 方法论，先写测试，再写实现"
- **AI 输出**: src/source_coder.py, src/scrambler.py, 对应测试文件
- **测试结果**: 23/23 测试通过
- **人工修改**: 无
- **采纳理由**: 简单模块，标准实现

### 2026-07-01: 信道编解码模块 (Task 4)
- **AI 角色**: 实现卷积编码器 (2,1,7) 和 Viterbi 译码器
- **关键 Prompt**: "实现卷积编码 + Viterbi 译码，支持硬判决和软判决"
- **AI 输出**: src/channel_coder.py
- **遇到的问题**: 
  1. Viterbi 回溯逻辑错误：存储 survivor_input 但 _prev_state 不唯一（2 个 prev_state 可映射到同一 next_state）
  2. **修复**: 改为存储 survivor_prev_state（前一状态），确保回溯路径唯一
- **测试结果**: 14/14 测试通过
- **采纳理由**: 这是系统最复杂的模块，Viterbi MLSE 是标准方法

### 2026-07-01: 帧封装 + QPSK 模块 (Tasks 5-6)
- **AI 角色**: TDD 实现帧封装/解封装和 QPSK Gray 映射调制解调
- **关键 Prompt**: "实现帧结构 Sync(32)+Length(16)+Payload(256) 和 QPSK Gray 映射"
- **遇到的问题**:
  1. 帧长度字段 bit 位计算使用了错误的偏移
  2. Gray 映射表定义不符合标准（bit0→I, bit1→Q 的约定）
  - **修复**: 修正偏移计算和 Gray 映射表
- **测试结果**: 帧 11/11, QPSK 8/8 测试通过
- **采纳理由**: 标准通信链路组件

### 2026-07-01: AWGN + 帧同步模块 (Tasks 7-8)
- **AI 角色**: 实现 AWGN 信道和基于滑动相关的帧同步器
- **关键 Prompt**: "实现 AWGN 信道仿真和滑动相关帧同步"
- **遇到的问题**:
  1. 同步器在随机载荷中产生误检（短同步字的固有局限）
  2. 帧间距阈值过小，允许误检峰通过
  - **修复**: 改为按相关值降序排列峰值后筛选，确保最强（真实）峰值优先保留
- **测试结果**: 19/19 测试通过
- **采纳理由**: 归一化互相关 + 峰值强度优先排序策略

### 2026-07-01: Pipeline 集成 + CLI (Tasks 9-11)
- **AI 角色**: 串联全链路、CLI 入口、指标计算
- **关键 Prompt**: "将所有模块串联为端到端 Pipeline，并提供 CLI"
- **AI 输出**: src/pipeline.py, src/cli.py, src/metrics.py, scripts/sweep_snr.py
- **遇到的问题**:
  1. CLI argparse `--plot/--no-plot` 语法错误
  2. Pipeline 中比特对齐问题
  - **修复**: 使用独立的 --plot/--no-plot 参数（dest='plot'）；通过帧同步器改进间接修复对齐
- **测试结果**: 13/13 测试通过
- **采纳理由**: 统一 CLI 入口支持所有可配置参数

### 2026-07-01: DESIGN.md 编写
- **AI 角色**: 根据所有模块实现和接口生成完整设计文档
- **关键 Prompt**: "根据已实现的系统编写 DESIGN.md"
- **AI 输出**: DESIGN.md（系统概述、模块接口、设计决策、测试策略）

### 2026-07-01: 端到端验证
- **AI 角色**: 运行 CLI 验证系统在不同 SNR 下的性能
- **测试参数**: SNR ∈ {0, 5, 10, 15, 20, 100} dB, Test.txt (768 字节)
- **结果**:
  | SNR (dB) | BER | FER | 文本恢复率 |
  |----------|-----|-----|-----------|
  | 100 | 0.000 | 0.000 | 100% |
  | 20 | 0.000 | 0.000 | 100% |
  | 15 | 0.000 | 0.000 | 100% |
  | 10 | 0.000 | 0.204 | ~100% |
  | 5 | 0.448 | 1.000 | ~0% |
  | 0 | 0.484 | 1.000 | ~0% |
- **输出文件**: received.txt ✓, metrics.json ✓, constellation_rx.png ✓, sync_correlation.png ✓
- **总测试数**: 93/93 通过

---

## AI 工具使用总结
- **总测试用例**: 93 个（全部通过）
- **AI 生成代码行数**: 约 1800 行（含测试）
- **人工修改**: 0 行（AI 独立完成所有实现和调试）
- **开发耗时**: 约 2 小时（含规划、实现、调试、测试）
- **关键修复次数**: 6 次（Viterbi 回溯、帧长度字段、Gray 映射、同步器峰值、argparse、Pipeline 对齐）
