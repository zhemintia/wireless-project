"""性能指标计算与可视化模块。

提供 BER、FER、文本恢复率等指标计算，以及星座图、BER 曲线、
同步相关峰值图等可视化功能。
"""

import numpy as np
from pathlib import Path
from typing import Optional, List


def compute_ber(tx_bits: np.ndarray, rx_bits: np.ndarray) -> float:
    """计算误比特率 (Bit Error Rate)。

    Args:
        tx_bits: 发送比特序列。
        rx_bits: 接收比特序列。

    Returns:
        BER = 错误比特数 / 总比特数。
    """
    if len(tx_bits) == 0:
        return 0.0
    min_len = min(len(tx_bits), len(rx_bits))
    errors = np.sum(tx_bits[:min_len] != rx_bits[:min_len])
    return float(errors / min_len)


def compute_fer(
    tx_frames: List[np.ndarray],
    rx_frames: List[np.ndarray],
) -> float:
    """计算误帧率 (Frame Error Rate)。

    一帧中任意比特错误即算该帧错误。

    Args:
        tx_frames: 发送帧列表。
        rx_frames: 接收帧列表。

    Returns:
        FER = 错误帧数 / 总帧数。
    """
    if len(tx_frames) == 0:
        return 0.0

    frame_errors = abs(len(tx_frames) - len(rx_frames))
    for i in range(min(len(tx_frames), len(rx_frames))):
        tx = tx_frames[i]
        rx = rx_frames[i]
        min_len = min(len(tx), len(rx))
        if not np.array_equal(tx[:min_len], rx[:min_len]):
            frame_errors += 1

    return float(frame_errors / len(tx_frames))


def compute_text_recovery_rate(original_path: str, received_path: str) -> float:
    """计算文本恢复率。

    比较原始文件和恢复文件的字符级匹配率。

    Args:
        original_path: 原始文件路径。
        received_path: 恢复文件路径。

    Returns:
        恢复率 (0.0 ~ 1.0)。
    """
    try:
        original = Path(original_path).read_text(encoding='utf-8')
        received = Path(received_path).read_text(encoding='utf-8')
    except (FileNotFoundError, UnicodeDecodeError):
        return 0.0

    if not original:
        return 1.0 if not received else 0.0

    min_len = min(len(original), len(received))
    matches = sum(1 for i in range(min_len) if original[i] == received[i])
    return matches / len(original)


def plot_constellation(
    symbols: np.ndarray,
    output_path: Optional[str] = None,
    title: str = "Received Constellation",
    show: bool = False,
):
    """绘制接收信号星座图。

    Args:
        symbols: 接收复符号序列。
        output_path: 保存路径（PNG 文件）。
        title: 图标题。
        show: 是否显示图形。
    """
    if len(symbols) == 0:
        return

    try:
        import matplotlib.pyplot as plt
    except ImportError:
        print("matplotlib not installed, skipping plot.")
        return

    fig, ax = plt.subplots(figsize=(7, 7))
    ax.scatter(symbols.real, symbols.imag, s=4, alpha=0.5, color='steelblue',
               edgecolors='none')
    ax.axhline(y=0, color='gray', linestyle='--', linewidth=0.8)
    ax.axvline(x=0, color='gray', linestyle='--', linewidth=0.8)

    # 标注理想星座点
    ideal = np.array([1 + 1j, -1 + 1j, -1 - 1j, 1 - 1j]) / np.sqrt(2)
    ax.scatter(ideal.real, ideal.imag, s=80, marker='x', color='red',
               linewidths=2, label='Ideal QPSK')

    ax.set_xlabel('In-phase (I)')
    ax.set_ylabel('Quadrature (Q)')
    ax.set_title(title)
    ax.set_aspect('equal')
    ax.grid(True, alpha=0.3)
    ax.legend()

    max_val = max(np.abs(symbols.real).max(), np.abs(symbols.imag).max(), 2.0)
    ax.set_xlim(-max_val * 1.2, max_val * 1.2)
    ax.set_ylim(-max_val * 1.2, max_val * 1.2)

    if output_path:
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(output_path, dpi=150, bbox_inches='tight')
    if show:
        plt.show()
    else:
        plt.close(fig)


def plot_ber_curve(
    snr_values: List[float],
    ber_values: List[float],
    output_path: Optional[str] = None,
    show: bool = False,
):
    """绘制 BER vs SNR 曲线。

    Args:
        snr_values: SNR 值列表 (dB)。
        ber_values: 对应的 BER 值列表。
        output_path: 保存路径。
        show: 是否显示图形。
    """
    try:
        import matplotlib.pyplot as plt
    except ImportError:
        print("matplotlib not installed, skipping plot.")
        return

    fig, ax = plt.subplots(figsize=(8, 5))
    ax.semilogy(snr_values, ber_values, 'o-', color='steelblue',
                linewidth=1.5, markersize=5, label='Simulated BER')

    # 理论 QPSK BER (无编码): 0.5 * erfc(sqrt(Eb/N0))
    try:
        from scipy.special import erfc
        snr_linear = 10 ** (np.array(snr_values) / 10.0)
        theoretical_ber = 0.5 * erfc(np.sqrt(snr_linear))
        ax.semilogy(snr_values, theoretical_ber, '--', color='red',
                    linewidth=1.5, label='Uncoded QPSK (theory)')
    except ImportError:
        pass  # scipy 不可用时跳过理论曲线

    ax.set_xlabel('SNR $E_s/N_0$ (dB)')
    ax.set_ylabel('BER')
    ax.set_title('BER vs SNR Performance')
    ax.grid(True, alpha=0.3, which='both')
    ax.legend()
    ax.set_ylim(1e-5, 1)

    if output_path:
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(output_path, dpi=150, bbox_inches='tight')
    if show:
        plt.show()
    else:
        plt.close(fig)


def plot_sync_correlation(
    correlation: np.ndarray,
    peak_indices: List[int],
    output_path: Optional[str] = None,
    show: bool = False,
):
    """绘制同步相关峰值图。

    Args:
        correlation: 相关值序列。
        peak_indices: 检测到的峰值索引列表。
        output_path: 保存路径。
        show: 是否显示图形。
    """
    try:
        import matplotlib.pyplot as plt
    except ImportError:
        print("matplotlib not installed, skipping plot.")
        return

    fig, ax = plt.subplots(figsize=(10, 4))
    ax.plot(correlation, color='steelblue', linewidth=1.0, label='Correlation')
    ax.scatter(peak_indices, correlation[peak_indices],
               color='red', s=50, marker='v', zorder=5, label='Detected Peaks')

    ax.set_xlabel('Symbol Offset')
    ax.set_ylabel('Normalized Correlation')
    ax.set_title('Frame Synchronization — Correlation Peaks')
    ax.grid(True, alpha=0.3)
    ax.legend()

    if output_path:
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(output_path, dpi=150, bbox_inches='tight')
    if show:
        plt.show()
    else:
        plt.close(fig)
