"""全局配置参数模块。

所有可配置的系统参数集中管理，通过命令行参数或直接修改此文件来调整。
"""

from dataclasses import dataclass, field
from typing import Optional
import numpy as np


@dataclass
class WirelessConfig:
    """无线通信基带仿真系统配置。

    Attributes:
        sync_word: 帧同步字（32-bit PN 序列，具有良好的自相关特性）。
        frame_payload_bits: 每帧有效载荷比特数（不含同步字和长度字段）。
        channel_code_rate: 卷积码码率（编码器输入比特与输出比特之比）。
        constraint_length: 卷积码约束长度。
        generator_polynomials: 卷积码生成多项式（八进制表示）。
        scrambler_poly: 扰码器 LFSR 生成多项式 (x^7 + x^4 + 1)。
        scrambler_init: 扰码器初始状态。
        default_snr_db: 默认信噪比（dB）。
        default_seed: 默认随机数种子。
        sync_offset: 仿真同步偏移（符号数），0 表示无偏移。
        qpsk_gray: 是否使用 Gray 映射。
    """

    # --- 帧结构参数 ---
    sync_word: np.ndarray = field(default_factory=lambda: np.array(
        [1, 1, 1, 0, 1, 1, 1, 0, 0, 1, 0, 1, 1, 0, 0, 1,
         1, 0, 1, 0, 0, 1, 1, 1, 0, 1, 1, 0, 0, 0, 0, 1],
        dtype=np.uint8
    ))
    frame_payload_bits: int = 256

    # --- 信道编码参数 ---
    channel_code_rate: float = 0.5  # 1/2 卷积码码率
    constraint_length: int = 7
    generator_polynomials: tuple = (0o171, 0o133)

    # --- 扰码器参数 ---
    scrambler_poly: int = 0x91  # x^7 + x^4 + 1 → 10010001
    scrambler_init: int = 0x7F  # 全 1 初始状态

    # --- 仿真参数 ---
    default_snr_db: float = 10.0
    default_seed: int = 42
    sync_offset: int = 0

    # --- QPSK 参数 ---
    qpsk_gray: bool = True

    # --- 同步参数 ---
    sync_threshold_factor: float = 0.5  # 检测阈值 = factor * max(correlation)


# 全局默认配置实例
default_config = WirelessConfig()
