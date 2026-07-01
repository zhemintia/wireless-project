"""帧同步模块 — 基于滑动相关的帧边界检测。

使用已知同步字 (Sync Word) 的匹配滤波器进行滑动相关检测。
通过设置阈值，在接收符号流中定位各帧的起始位置。

算法:
1. 将同步字 QPSK 调制为参考符号序列。
2. 在接收符号流上滑动参考序列，计算互相关。
3. 检测相关峰值（超过阈值的局部最大值）。
4. 从峰值位置提取各帧的符号块。
"""

import numpy as np
from typing import List, Optional


class FrameSynchronizer:
    """帧同步器：检测并提取帧边界。

    Attributes:
        sync_word: 同步字比特序列。
        sync_symbols: 同步字的 QPSK 调制符号（参考信号）。
        frame_length_symbols: 每帧包含的符号数。
        threshold_factor: 检测阈值 = threshold_factor * max(correlation)。
    """

    def __init__(
        self,
        sync_word: np.ndarray,
        frame_length_symbols: int = None,
        threshold_factor: float = 0.5,
    ):
        """
        Args:
            sync_word: 32-bit 同步字 (uint8 ndarray)。
            frame_length_symbols: 每帧符号数。
                None 时自动从 sync_word + 16 + payload_bits 推算。
            threshold_factor: 峰值检测阈值因子 (0~1)。
        """
        self.sync_word = sync_word.astype(np.uint8)
        self.threshold_factor = threshold_factor

        # 将同步字调制为参考符号
        self.sync_symbols = self._bits_to_qpsk_symbols(self.sync_word)

        # 帧长
        if frame_length_symbols is None:
            # 默认: 32-bit 同步字 + 16-bit 长度 + 256-bit 载荷
            frame_bits = len(sync_word) + 16 + 256
            frame_length_symbols = frame_bits // 2
        self.frame_length_symbols = frame_length_symbols

    @staticmethod
    def _bits_to_qpsk_symbols(bits: np.ndarray) -> np.ndarray:
        """将比特序列 QPSK 调制为复符号（内部使用）。"""
        from src.qpsk import qpsk_modulate
        return qpsk_modulate(bits)

    def compute_correlation(self, symbols: np.ndarray) -> np.ndarray:
        """计算接收符号与同步字参考的滑动互相关。

        Args:
            symbols: 接收复符号序列。

        Returns:
            相关值序列（长度 = len(symbols) - len(sync_symbols) + 1）。
        """
        ref = self.sync_symbols
        ref_len = len(ref)

        if len(symbols) < ref_len:
            return np.array([], dtype=np.float64)

        # 滑动互相关: corr[k] = sum(conj(ref[i]) * symbols[k+i])
        # 使用信号处理方式：归一化互相关
        correlation = np.zeros(len(symbols) - ref_len + 1, dtype=np.float64)
        ref_conj = np.conj(ref)
        ref_norm = np.sqrt(np.sum(np.abs(ref) ** 2))

        for k in range(len(correlation)):
            segment = symbols[k:k + ref_len]
            seg_norm = np.sqrt(np.sum(np.abs(segment) ** 2))
            if seg_norm > 1e-12:
                corr_val = np.abs(np.sum(ref_conj * segment)) / (ref_norm * seg_norm)
            else:
                corr_val = 0.0
            correlation[k] = corr_val

        return correlation

    def find_frame_starts(
        self,
        symbols: np.ndarray,
        min_distance: int = None,
    ) -> List[int]:
        """在接收符号流中检测帧起始位置。

        使用滑动相关 + 峰值检测。阈值 = threshold_factor * max(correlation)。
        峰值按相关值降序排列后筛选，确保最强峰值优先保留。

        Args:
            symbols: 接收复符号序列。
            min_distance: 帧之间的最小符号间距。默认为帧长减去同步字长。

        Returns:
            帧起始符号索引列表（按时间排序）。
        """
        if min_distance is None:
            min_distance = self.frame_length_symbols - len(self.sync_symbols)

        correlation = self.compute_correlation(symbols)
        if len(correlation) == 0:
            return []

        # 检测阈值
        max_corr = np.max(correlation)
        if max_corr < 0.1:
            return []
        threshold = max_corr * self.threshold_factor

        # 找到所有超过阈值的局部最大值，记录 (位置, 相关值)
        peaks = []
        i = 0
        while i < len(correlation) - 1:
            if correlation[i] >= threshold:
                local_max = correlation[i]
                local_max_idx = i
                while i < len(correlation) - 1 and correlation[i + 1] >= correlation[i]:
                    i += 1
                    if correlation[i] > local_max:
                        local_max = correlation[i]
                        local_max_idx = i
                while i < len(correlation) - 1 and correlation[i + 1] <= correlation[i]:
                    i += 1
                peaks.append((local_max_idx, local_max))
            i += 1

        if not peaks:
            return []

        # 按相关值降序排列：最强峰值优先保留
        peaks.sort(key=lambda x: x[1], reverse=True)

        # 按 min_distance 筛选：保留最强峰值，排除其附近的其他峰值
        filtered = [peaks[0][0]]
        for pos, _ in peaks[1:]:
            if all(abs(pos - f) >= min_distance for f in filtered):
                filtered.append(pos)

        # 按位置升序返回
        filtered.sort()
        return filtered

    def extract_frames(
        self,
        symbols: np.ndarray,
        frame_starts: List[int],
    ) -> List[np.ndarray]:
        """从检测到的帧起始位置提取各帧符号。

        Args:
            symbols: 接收复符号序列。
            frame_starts: find_frame_starts 返回的起始索引列表。

        Returns:
            帧符号列表，每个元素为一个帧的复符号 ndarray。
        """
        frames = []
        for start in frame_starts:
            end = start + self.frame_length_symbols
            if end <= len(symbols):
                frames.append(symbols[start:end])
        return frames
