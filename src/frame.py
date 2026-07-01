"""帧封装/解封装模块。

将编码比特流组织为固定长度的帧结构:
+-----------+----------+----------------+
| Sync Word | Length   | Payload        |
| (32 bits) | (16 bits)| (N bits)       |
+-----------+----------+----------------+

- Sync Word: 用于帧同步的唯一字（32-bit PN 序列）。
- Length: 16-bit 无符号整数（大端序），记录本帧载荷比特数。
- Payload: 可变长度，不足时零填充。
"""

import numpy as np
from typing import List, Union


class FramePacker:
    """帧封装器：将比特流组织为带同步字的帧。"""

    def __init__(self, sync_word: np.ndarray, payload_bits: int = 256):
        """
        Args:
            sync_word: 帧同步字 (uint8 ndarray, 推荐 32 bits)。
            payload_bits: 每帧有效载荷比特数。
        """
        self.sync_word = sync_word.astype(np.uint8)
        self.payload_bits = payload_bits
        self._sw_len = len(sync_word)
        self._len_field_bits = 16
        self._header_bits = self._sw_len + self._len_field_bits
        self._frame_bits = self._header_bits + payload_bits

    def pack(self, bits: np.ndarray) -> List[np.ndarray]:
        """将比特序列封装为帧列表。

        Args:
            bits: 输入比特序列 (uint8 ndarray)。

        Returns:
            帧列表，每个帧为 uint8 ndarray，长度 = sw_len + 16 + payload_bits。
        """
        if len(bits) == 0:
            return []

        frames = []
        pos = 0
        total_bits = len(bits)

        while pos < total_bits:
            remaining = total_bits - pos
            payload_len = min(remaining, self.payload_bits)

            # 构建帧
            frame = np.zeros(self._frame_bits, dtype=np.uint8)

            # 同步字
            frame[:self._sw_len] = self.sync_word

            # 长度字段 (16-bit 大端序)
            length_val = payload_len
            for i in range(self._len_field_bits):
                bit_pos = self._len_field_bits - 1 - i
                frame[self._sw_len + i] = (length_val >> bit_pos) & 1

            # 载荷
            frame[self._header_bits:self._header_bits + payload_len] = \
                bits[pos:pos + payload_len]

            # 剩余部分保持零填充
            frames.append(frame)
            pos += payload_len

        return frames

    @property
    def frame_length(self) -> int:
        """获取每帧的总比特数。"""
        return self._frame_bits


class FrameUnpacker:
    """帧解封装器：从帧中提取有效载荷比特。"""

    def __init__(self, sync_word: np.ndarray, payload_bits: int = 256):
        """
        Args:
            sync_word: 帧同步字。
            payload_bits: 每帧有效载荷比特数（用于确定 header 长度）。
        """
        self.sync_word = sync_word.astype(np.uint8)
        self.payload_bits = payload_bits
        self._sw_len = len(sync_word)
        self._len_field_bits = 16
        self._header_bits = self._sw_len + self._len_field_bits
        self._frame_bits = self._header_bits + payload_bits

    def unpack(self, frames: Union[List[np.ndarray], np.ndarray]) -> np.ndarray:
        """从帧列表中提取数据比特。

        Args:
            frames: 帧列表（list of 1D arrays 或 2D ndarray）。

        Returns:
            提取的比特序列 (uint8 ndarray)。

        Raises:
            TypeError: 如果 frames 不是 list 或 ndarray。
        """
        if isinstance(frames, np.ndarray) and frames.ndim == 1 and len(frames) == 0:
            return np.array([], dtype=np.uint8)

        if isinstance(frames, list) and len(frames) == 0:
            return np.array([], dtype=np.uint8)

        if isinstance(frames, np.ndarray) and frames.ndim == 1:
            # 单个帧展平？尝试作为 list 处理
            frames = [frames]

        all_bits = []
        unpacked_total = 0

        # 从最后一帧获取总比特数（第一帧可能不包含总数信息）
        # 累积所有数据，最后截断到正确长度
        for frame in frames:
            frame = np.atleast_1d(frame)
            if len(frame) == 0:
                continue
            # 读取长度字段
            length_bits = frame[self._sw_len:self._sw_len + self._len_field_bits]
            if len(length_bits) < self._len_field_bits:
                continue
            length_val = 0
            for b in length_bits:
                length_val = (length_val << 1) | int(b)
            if length_val > self.payload_bits:
                import warnings
                warnings.warn(
                    f"Frame length field corrupted: {length_val} > {self.payload_bits}. "
                    f"Clipping to max payload. Data may be unrecoverable."
                )
                length_val = self.payload_bits
            # 读取载荷
            payload = frame[self._header_bits:self._header_bits + length_val]
            all_bits.append(payload)
            unpacked_total += length_val

        if not all_bits:
            return np.array([], dtype=np.uint8)

        return np.concatenate(all_bits)

    def unpack_with_sync_check(self, frames) -> tuple[np.ndarray, list]:
        """解封装并检查同步字是否正确。

        Args:
            frames: 帧列表。

        Returns:
            (bits, sync_errors): 数据比特和同步错误帧索引列表。
        """
        sync_errors = []
        valid_frames = []
        for i, frame in enumerate(frames):
            frame = np.atleast_1d(frame)
            if len(frame) < self._sw_len:
                sync_errors.append(i)
                continue
            if not np.array_equal(frame[:self._sw_len], self.sync_word):
                sync_errors.append(i)
                continue
            valid_frames.append(frame)

        bits = self.unpack(valid_frames)
        return bits, sync_errors
