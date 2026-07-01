# CONTEXT.md — 无线通信基带仿真系统 领域语言词汇表

## 链路组件

- **信源编码 (Source Coder)**: 将文本文件（UTF-8）转换为比特序列，并在接收端进行反向转换。输出包含 metadata（原始文件名、字节数、比特数）。
- **加扰器 (Scrambler)**: 使用 LFSR（线性反馈移位寄存器）对比特序列进行随机化，避免长连 0/1。本系统使用自同步扰码器，接收端无需显式同步扰码器状态。
- **信道编码 (Channel Coder)**: 添加冗余比特以对抗信道错误。本系统使用卷积码 (2,1,7) + Viterbi 译码。
- **帧封装 (Frame Packer)**: 将编码比特按帧组织，每帧 = 同步字 (32 bits) + 长度字段 (16 bits) + 有效载荷 (N bits)。填充比特补齐不足一帧的部分。
- **QPSK 调制 (QPSK Modulator)**: 将每 2 个比特映射为一个复基带符号。使用 Gray 映射（相邻星座点仅 1 bit 差异），星座点归一化至平均功率 = 1。
- **AWGN 信道 (AWGN Channel)**: 叠加复高斯白噪声。噪声功率由 SNR 决定。Seed 控制可复现性。
- **帧同步 (Frame Synchronizer)**: 使用滑动相关器在接收符号流中检测帧同步字，确定帧边界。阈值因子控制检测灵敏度。
- **QPSK 解调 (QPSK Demodulator)**: 从接收符号恢复比特。支持硬判决（直接判决星座点）和软判决（输出 LLR 对数似然比）。
- **信道译码 (Channel Decoder)**: Viterbi 算法进行最大似然序列估计 (MLSE) 译码。硬判决输入汉明距离度量；软判决输入欧氏距离度量。
- **解扰器 (Descrambler)**: 自同步解扰，与加扰器共享相同的 LFSR 多项式。
- **信源解码 (Source Decoder)**: 从比特序列恢复原始文本文件。

## 信号与度量

- **基带信号 (Baseband Signal)**: 未经射频调制的复基带符号序列。
- **符号 (Symbol)**: QPSK 调制后的一个复数值，携带 2 bits 信息。
- **SNR (Signal-to-Noise Ratio)**: 信噪比，单位 dB。定义为 Es/N0（每符号能量与噪声功率谱密度之比）。
- **Eb/N0**: 每比特能量与噪声功率谱密度之比。与 Es/N0 的关系: Es/N0 = Eb/N0 + 10*log10(code_rate * bits_per_symbol)。
- **BER (Bit Error Rate)**: 误比特率 = 接收错误比特数 / 发送总比特数。
- **FER (Frame Error Rate)**: 误帧率 = 接收错误帧数 / 发送总帧数。（一帧中任意比特错即算帧错）
- **文本恢复率 (Text Recovery Rate)**: 恢复文件与原文件一致的字符比例 (1 - 编辑距离/总字符数)。
- **星座图 (Constellation Diagram)**: 接收符号在复平面上的散点图，反映信号受噪声影响程度。

## 工程术语

- **TDD (Test-Driven Development)**: 红-绿-重构循环。先写失败测试 → 最小实现通过 → 重构。
- **垂直切片 (Vertical Slice)**: 跨越所有系统层的端到端功能实现，而非按层级水平切片。
- **PRD (Product Requirements Document)**: 产品需求文档，定义系统行为边界和验收标准。
- **Mock 测试**: 使用简化/理想化模块替代真实模块，验证接口和流程正确性。

## 避免使用的术语
- "Ticket" — 使用 "Issue"
- "Backlog" — 使用 "Issue tracker" 或直接列表
- "Pipeline"（仅指 CI/CD 时）— 本项目中使用 "链路" 或 "Chain"
