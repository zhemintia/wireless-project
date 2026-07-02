"""AWGN 信道仿真模块。

模拟加性高斯白噪声 (AWGN) 信道，对输入复基带符号叠加复高斯噪声。

噪声模型:
    r = s + n
    其中 n ~ CN(0, σ²), σ² = N0 (每复维) 或 σ² = N0/2 (每实维)

SNR 定义:
    Es/N0 = 1 / (2 * noise_var_per_real_dim) = 1 / noise_var_per_complex_dim
    noise_var_complex = 10^(-SNR_dB/10)
    每实维噪声方差 = noise_var_complex / 2

Seed 控制: 可复现的随机噪声生成。
"""

import numpy as np
from typing import Optional


def snr_db_to_noise_var(snr_db: float) -> float:
    """将 Es/N0 (dB) 转换为复噪声方差。

    对于单位平均功率信号:
        Es = E[|s|²] = 1
        noise_var (复) = Es / (10^(SNR/10)) = 10^(-SNR/10)

    Args:
        snr_db: Es/N0 信噪比 (dB)。

    Returns:
        复噪声方差 σ²（每复维）。
    """
    snr_linear = 10 ** (snr_db / 10.0)
    return 1.0 / snr_linear


def eb_n0_to_es_n0(eb_n0_db: float, bits_per_symbol: int = 2,
                    code_rate: float = 1.0) -> float:
    """Eb/N0 (dB) 转换为 Es/N0 (dB)。

    Es/N0 (dB) = Eb/N0 (dB) + 10*log10(bits_per_symbol * code_rate)

    Args:
        eb_n0_db: 每比特信噪比 (dB)。
        bits_per_symbol: 每符号比特数（QPSK = 2, BPSK = 1）。
        code_rate: 信道编码码率（0 < code_rate ≤ 1）。

    Returns:
        Es/N0 (dB)。
    """
    return eb_n0_db + 10.0 * np.log10(bits_per_symbol * code_rate)


def awgn_channel(
    symbols: np.ndarray,
    snr_db: float,
    seed: Optional[int] = None
) -> np.ndarray:
    """AWGN 信道：叠加复高斯白噪声。

    噪声模型: r = s + n, n ~ CN(0, N0)
    N0 = 10^(-SNR_dB/10)（对于单位平均功率信号）

    Args:
        symbols: 输入复基带符号序列 (complex ndarray)。
        snr_db: Es/N0 信噪比 (dB)。
        seed: 随机数种子（可复现噪声）。

    Returns:
        叠加噪声后的接收符号序列 (complex ndarray)。
    """
    if len(symbols) == 0:
        return np.array([], dtype=np.complex128)

    if not np.isfinite(snr_db):
        raise ValueError(f"SNR must be finite, got {snr_db}")

    noise_var = snr_db_to_noise_var(snr_db)

    # 每实维噪声标准差
    std_per_dim = np.sqrt(noise_var / 2.0)

    # 生成复高斯噪声
    rng = np.random.default_rng(seed)
    noise = std_per_dim * (
        rng.standard_normal(len(symbols)) +
        1j * rng.standard_normal(len(symbols))
    )

    return symbols + noise
