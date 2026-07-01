# DESIGN.md — 无线通信文件传输基带仿真系统设计文档

## 1. 系统概述

### 1.1 项目目标
构建一个完整的无线通信基带仿真系统，实现文本文件 `Test.txt` 经过模拟无线链路传输后在接收端恢复为 `received.txt`。

### 1.2 系统链路
```
Test.txt → [信源编码] → bits → [加扰器] → bits → [卷积编码] → bits
→ [帧封装] → frames → [QPSK调制] → 复基带符号
→ [AWGN信道] → 噪声符号 → [帧同步] → 对齐符号
→ [QPSK解调] → bits/LLR → [Viterbi译码] → bits → [解扰] → bits
→ [信源解码] → received.txt
```

### 1.3 技术参数
| 参数 | 值 |
|------|-----|
| 调制方式 | QPSK (Gray 映射) |
| 信道编码 | 卷积码 (2,1,7)，生成多项式 G1=171₈, G2=133₈ |
| 帧同步字 | 32-bit PN 序列 |
| 帧结构 | Sync(32) + Length(16) + Payload(256 bits) |
| 扰码器 | 自同步 LFSR，多项式 x⁷+x⁴+1 |
| 信道模型 | AWGN，可配置 Es/N₀ |
| 译码方式 | Viterbi MLSE（硬判决/软判决） |

---

## 2. 模块接口设计

### 2.1 信源编解码 (`source_coder.py`)
```
text_to_bits(file_path) → (bits: ndarray[uint8], metadata: dict)
bits_to_text(bits, metadata, output_path) → output_path: str
```
- UTF-8 编码，支持 Unicode 多语言文本
- metadata 包含：filename, num_bytes, num_bits

### 2.2 加扰/解扰 (`scrambler.py`)
```
scramble(bits, seed=0x7F, poly=0x91) → scrambled: ndarray[uint8]
descramble(bits, seed=0x7F, poly=0x91) → descrambled: ndarray[uint8]
```
- 自同步设计：解扰器自动从接收数据恢复 LFSR 状态
- 生成多项式：x⁷ + x⁴ + 1 (CCITT 标准)

### 2.3 信道编解码 (`channel_coder.py`)
```
ConvolutionalEncoder(K=7, generators=(171₈, 133₈))
    .encode(bits) → coded_bits

ViterbiDecoder(K=7, generators=(171₈, 133₈))
    .decode_hard(coded_bits) → decoded_bits
    .decode_soft(soft_values) → decoded_bits
```
- 码率 1/2，零尾比特终止
- 硬判决：汉明距离度量
- 软判决：欧氏距离度量（BPSK 映射 0→+1, 1→-1）
- 回溯：存储幸存前一状态，确保正确路径恢复

### 2.4 帧封装 (`frame.py`)
```
FramePacker(sync_word, payload_bits=256)
    .pack(bits) → List[ndarray]  # 每帧 304 bits

FrameUnpacker(sync_word, payload_bits=256)
    .unpack(frames) → bits
```
- 帧结构: | Sync Word (32) | Length (16) | Payload (256) |
- Length 字段：大端序 16-bit 无符号整数
- 最后一帧不足时零填充

### 2.5 QPSK 调制解调 (`qpsk.py`)
```
qpsk_modulate(bits) → symbols: ndarray[complex128]
qpsk_demodulate_hard(symbols) → bits: ndarray[uint8]
qpsk_demodulate_soft(symbols, noise_var) → llr: ndarray[float64]
```
- Gray 映射：bit0→I 路，bit1→Q 路（0→+1, 1→-1）
- 星座点归一化至平均功率 = 1
- 软判决 LLR：LLR(b₀) = √2/σ² · Re(r)，LLR(b₁) = √2/σ² · Im(r)

### 2.6 AWGN 信道 (`awgn.py`)
```
awgn_channel(symbols, snr_db, seed=None) → noisy_symbols
snr_db_to_noise_var(snr_db) → noise_var
eb_n0_to_es_n0(eb_n0_db, bits_per_symbol, code_rate) → es_n0_db
```
- 复高斯噪声：n ~ CN(0, N₀)，N₀ = 10^(-SNR/10)
- Seed 可复现噪声生成

### 2.7 帧同步 (`synchronizer.py`)
```
FrameSynchronizer(sync_word, frame_length_symbols, threshold_factor=0.5)
    .find_frame_starts(symbols) → List[int]
    .extract_frames(symbols, starts) → List[ndarray]
```
- 滑动归一化互相关检测
- 峰值按相关值降序排序，确保最强峰值优先
- 最小帧间距：frame_length - sync_length

### 2.8 Pipeline 编排 (`pipeline.py`)
```
WirelessPipeline(config)
    .run(input_path, output_dir, snr_db, seed, sync_offset) → metrics: dict
```
- 串联完整发射→信道→接收链路
- 输出：received.txt, metrics.json

---

## 3. 关键设计决策

### 3.1 帧同步字选择
使用 32-bit PN 序列（非 Barker 码），具有良好自相关特性。调制为 16 QPSK 符号后提供足够的处理增益用于可靠同步检测。

### 3.2 同步算法
- 归一化互相关：消除信号幅度影响
- 峰值按相关值降序排列后筛选：确保最强（真实）峰值优先保留
- 最小帧间距 = 帧长 - 同步字长：防止同一帧内误检

### 3.3 卷积码参数
- (2,1,7) 卷积码在 AWGN 信道下提供约 5-6 dB 编码增益
- Viterbi 译码器存储"前一状态"而非"输入比特"，确保回溯路径唯一

### 3.4 误码性能预期
| SNR (dB) | BER (预期) | 文本恢复率 (预期) |
|----------|-----------|------------------|
| ∞ (无噪声) | 0 | 100% |
| 20 | ~0 | ~100% |
| 15 | ~0 | ~100% |
| 10 | <10⁻⁴ | >99% |
| 5 | ~10⁻² | ~50% |
| 0 | ~5×10⁻² | ~0% |

---

## 4. 测试策略

### 4.1 单元测试 (80 个测试用例)
- 每个模块独立测试，遵循 TDD 红-绿-重构
- 覆盖：正常输入、边界条件（空输入、单比特、超大输入）、错误输入

### 4.2 集成测试 (7 个测试用例)
- 端到端无噪声：100% 恢复
- 高/低 SNR：BER 单调性验证
- 输出文件完整性检查
- Seed 可复现性验证

### 4.3 CLI 测试 (6 个测试用例)
- 参数解析正确性
- 默认参数运行
- 自定义参数运行
- 错误处理（文件不存在）

---

## 5. 文件结构
```
d:/class/wireless/
├── DESIGN.md              ← 本文档
├── AI_LOG.md              # AI 使用记录
├── CONTEXT.md             # 领域语言词汇表
├── Test.txt               # 测试输入文件
├── requirements.txt       # Python 依赖
├── src/                   # 源代码
│   ├── cli.py             # CLI 入口
│   ├── config.py          # 全局配置
│   ├── pipeline.py        # 链路编排
│   ├── source_coder.py    # 信源编解码
│   ├── scrambler.py       # 加扰/解扰
│   ├── channel_coder.py   # 卷积编解码
│   ├── frame.py           # 帧封装
│   ├── qpsk.py            # QPSK 调制解调
│   ├── awgn.py            # AWGN 信道
│   ├── synchronizer.py    # 帧同步
│   └── metrics.py         # 指标与可视化
├── tests/                 # 测试
├── output/                # 输出目录
└── scripts/
    └── sweep_snr.py       # SNR 扫描
```
