"""QPSK 调制解调模块 — Gray 映射。

QPSK (Quadrature Phase Shift Keying) 将每 2 个比特映射为一个复基带符号。

Gray 映射星座:
    00 →  (1 + 1j) / sqrt(2)   (45°)
    01 →  (-1 + 1j) / sqrt(2)  (135°)
    11 →  (-1 - 1j) / sqrt(2)  (225°)
    10 →  (1 - 1j) / sqrt(2)   (315°)

相邻星座点仅 1 bit 差异，最小化解调错误时的比特错误数。

解调支持:
- 硬判决: 直接判星座点最近邻。
- 软判决: 计算对数似然比 (LLR)，用于软输入 Viterbi 译码。
"""

import numpy as np


def qpsk_modulate(bits: np.ndarray) -> np.ndarray:
    """QPSK 调制（Gray 映射）。

    将每 2 个比特映射为 1 个复基带符号。符号归一化至平均功率 = 1。

    Args:
        bits: 输入比特序列 (uint8 ndarray)。

    Returns:
        复基带符号序列 (complex128 ndarray)，长度为 len(bits) // 2。
    """
    num_symbols = len(bits) // 2
    if num_symbols == 0:
        return np.array([], dtype=np.complex128)

    # 截断为偶数长度（丢弃最后一个奇数比特）
    even_bits = bits[:num_symbols * 2]

    # 向量化实现: b0→I路, b1→Q路, 0→+1, 1→-1
    b0 = even_bits[0::2].astype(np.float64)
    b1 = even_bits[1::2].astype(np.float64)
    scale = 1.0 / np.sqrt(2)
    symbols = ((1.0 - 2.0 * b0) + 1j * (1.0 - 2.0 * b1)) * scale

    return symbols


def qpsk_demodulate_hard(symbols: np.ndarray) -> np.ndarray:
    """QPSK 硬判决解调。

    将每个复符号判为最近的星座点，恢复对应比特。

    Args:
        symbols: 接收复符号序列 (complex ndarray)。

    Returns:
        恢复的比特序列 (uint8 ndarray)，长度为 2 * len(symbols)。
    """
    if len(symbols) == 0:
        return np.array([], dtype=np.uint8)

    # 硬判决: 根据符号的实部和虚部符号
    real = symbols.real
    imag = symbols.imag

    # bit0: 实部 ≥ 0 → 0, 实部 < 0 → 1
    # bit1: 虚部 ≥ 0 → 0, 虚部 < 0 → 1
    bits = np.zeros(2 * len(symbols), dtype=np.uint8)
    bits[0::2] = (real < 0).astype(np.uint8)
    bits[1::2] = (imag < 0).astype(np.uint8)

    return bits


def qpsk_demodulate_soft(
    symbols: np.ndarray,
    noise_var: float = 1.0
) -> np.ndarray:
    """QPSK 软判决解调（LLR 计算）— 预留，当前 Pipeline 使用硬判决。

    计算每个比特的对数似然比 (LLR):
    LLR(b) = log(P(b=0|r) / P(b=1|r))

    对于 AWGN 信道和 Gray QPSK:
    LLR(b0) ≈ (sqrt(2) / σ²_real) * Re(r)
    LLR(b1) ≈ (sqrt(2) / σ²_real) * Im(r)

    ⚠ noise_var 是**每实维**噪声方差 σ²_real = N0/2（非复维方差 N0）。
    如果从 snr_db_to_noise_var(snr_db) 获得复方差 N0，需除以 2：
        noise_var_real = snr_db_to_noise_var(snr_db) / 2.0

    Args:
        symbols: 接收复符号序列 (complex ndarray)。
        noise_var: 噪声方差 σ²_real（每实维 = N0/2）。

    Returns:
        LLR 序列 (float64 ndarray)，长度 = 2 * len(symbols)。
        正值表示 bit=0 更有信心，负值表示 bit=1 更有信心。
    """
    if len(symbols) == 0:
        return np.array([], dtype=np.float64)

    # 避免除零
    if noise_var < 1e-12:
        noise_var = 1e-12

    # 最大似然近似 LLR
    scale = np.sqrt(2) / noise_var

    llr = np.zeros(2 * len(symbols), dtype=np.float64)
    llr[0::2] = scale * symbols.real
    llr[1::2] = scale * symbols.imag

    return llr
