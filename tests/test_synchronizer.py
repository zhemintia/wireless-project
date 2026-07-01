"""帧同步模块测试。

遵循 TDD Red-Green-Refactor 循环。
"""

import pytest
import numpy as np


# 共享的测试夹具
@pytest.fixture
def sync_word():
    """32-bit 同步字（从 WirelessConfig 导入，确保与其他测试一致）。"""
    from src.config import WirelessConfig
    return WirelessConfig().sync_word.copy()


class TestFrameSynchronizer:
    """帧同步器测试。"""

    def test_no_offset_detection(self, sync_word):
        """测试无偏移时正确检测帧起始位置。"""
        from src.synchronizer import FrameSynchronizer
        from src.qpsk import qpsk_modulate

        frame_len_bits = len(sync_word) + 16 + 256
        frame_len_sym = frame_len_bits // 2

        syncer = FrameSynchronizer(
            sync_word=sync_word,
            frame_length_symbols=frame_len_sym
        )

        # 构造: [sync_word | length | payload | sync_word | length | payload]
        payload = np.random.RandomState(0).randint(0, 2, size=256, dtype=np.uint8)
        length_bits = np.zeros(16, dtype=np.uint8)
        for i in range(16):
            length_bits[i] = (256 >> (15 - i)) & 1
        frame1 = np.concatenate([sync_word, length_bits, payload])
        frame2 = np.concatenate([sync_word, length_bits, payload])
        bits = np.concatenate([frame1, frame2])

        # 调制为符号
        symbols = qpsk_modulate(bits)

        # 同步
        frame_starts = syncer.find_frame_starts(symbols)

        # 应检测到 2 帧起始位置
        assert len(frame_starts) == 2
        assert frame_starts[0] == 0
        assert abs(frame_starts[1] - frame_len_sym) < 3

    def test_known_offset_detection(self, sync_word):
        """测试已知偏移量下的检测。"""
        from src.synchronizer import FrameSynchronizer
        from src.qpsk import qpsk_modulate

        frame_len_bits = len(sync_word) + 16 + 256
        frame_len_sym = frame_len_bits // 2

        syncer = FrameSynchronizer(
            sync_word=sync_word,
            frame_length_symbols=frame_len_sym
        )

        # 前缀填充 + 完整帧（含长度字段）
        prefix_symbols_count = 50
        rng = np.random.RandomState(1)
        prefix = rng.randn(prefix_symbols_count) + 1j * rng.randn(prefix_symbols_count)
        prefix = prefix * 0.1  # 低幅度噪声

        length_bits = np.zeros(16, dtype=np.uint8)
        for i in range(16):
            length_bits[i] = (256 >> (15 - i)) & 1
        payload = np.random.RandomState(2).randint(0, 2, size=256, dtype=np.uint8)
        frame_bits = np.concatenate([sync_word, length_bits, payload])
        frame_symbols = qpsk_modulate(frame_bits)

        all_symbols = np.concatenate([prefix, frame_symbols])

        frame_starts = syncer.find_frame_starts(all_symbols)

        assert len(frame_starts) >= 1
        detected = frame_starts[0]
        assert abs(detected - prefix_symbols_count) < 5

    def test_multiple_frames_sync(self, sync_word):
        """测试多帧同步。"""
        from src.synchronizer import FrameSynchronizer
        from src.qpsk import qpsk_modulate

        # 帧 = 同步字 (32) + 长度 (16) + 载荷 (256) = 304 bits = 152 symbols
        frame_len_bits = len(sync_word) + 16 + 256
        frame_len_sym = frame_len_bits // 2

        syncer = FrameSynchronizer(
            sync_word=sync_word,
            frame_length_symbols=frame_len_sym
        )

        payload_len = 256
        length_bits = np.zeros(16, dtype=np.uint8)
        for i in range(16):
            length_bits[i] = (payload_len >> (15 - i)) & 1
        payload = np.random.RandomState(3).randint(0, 2, size=payload_len, dtype=np.uint8)
        frame_bits = np.concatenate([sync_word, length_bits, payload])
        frame_symbols = qpsk_modulate(frame_bits)

        # 3 帧拼接
        all_symbols = np.concatenate([frame_symbols, frame_symbols, frame_symbols])

        frame_starts = syncer.find_frame_starts(all_symbols)

        assert len(frame_starts) == 3
        for i, start in enumerate(frame_starts):
            assert abs(start - i * frame_len_sym) < 10  # 允许小幅误差

    def test_empty_input(self, sync_word):
        """测试空输入返回空列表。"""
        from src.synchronizer import FrameSynchronizer
        syncer = FrameSynchronizer(sync_word=sync_word)
        symbols = np.array([], dtype=np.complex128)
        starts = syncer.find_frame_starts(symbols)
        assert len(starts) == 0

    def test_short_input(self, sync_word):
        """测试短于同步字的输入返回空列表。"""
        from src.synchronizer import FrameSynchronizer
        syncer = FrameSynchronizer(sync_word=sync_word)
        symbols = np.array([1 + 1j, -1 - 1j], dtype=np.complex128)
        starts = syncer.find_frame_starts(symbols)
        assert len(starts) == 0

    def test_correlation_peak_value(self, sync_word):
        """测试同步字处的相关值远大于噪声处的相关值。"""
        from src.synchronizer import FrameSynchronizer
        from src.qpsk import qpsk_modulate

        syncer = FrameSynchronizer(sync_word=sync_word)

        # 构造含同步字和长度字段的符号流
        length_bits = np.zeros(16, dtype=np.uint8)
        for i in range(16):
            length_bits[i] = (256 >> (15 - i)) & 1
        payload = np.random.RandomState(4).randint(0, 2, size=256, dtype=np.uint8)
        frame_bits = np.concatenate([sync_word, length_bits, payload])
        symbols = qpsk_modulate(frame_bits)

        correlation = syncer.compute_correlation(symbols)

        # 第一位置（同步字位置）的相关值应为最大之一
        peak_idx = np.argmax(correlation)
        # 对于无噪声信号，峰值应在同步字位置
        assert peak_idx == 0  # 第一帧同步字位于位置 0

    def test_extract_frames(self, sync_word):
        """测试从同步位置提取帧符号。"""
        from src.synchronizer import FrameSynchronizer
        from src.qpsk import qpsk_modulate

        frame_len_bits = len(sync_word) + 16 + 256  # 同步字 + 长度 + 载荷
        frame_len_sym = frame_len_bits // 2

        syncer = FrameSynchronizer(
            sync_word=sync_word,
            frame_length_symbols=frame_len_sym
        )

        # 构造信号: 噪声前导 + 完整帧（含长度字段）
        rng = np.random.RandomState(5)
        prefix = (rng.randn(30) + 1j * rng.randn(30)) * 0.1

        # 构造含长度字段的完整帧
        length_bits = np.zeros(16, dtype=np.uint8)
        for i in range(16):
            length_bits[i] = (256 >> (15 - i)) & 1
        payload = np.random.RandomState(6).randint(0, 2, size=256, dtype=np.uint8)
        frame_bits = np.concatenate([sync_word, length_bits, payload])
        frame_sym = qpsk_modulate(frame_bits)

        all_sym = np.concatenate([prefix, frame_sym])

        frame_starts = syncer.find_frame_starts(all_sym)
        extracted = syncer.extract_frames(all_sym, frame_starts)

        assert len(extracted) == 1
        assert len(extracted[0]) == frame_len_sym

    def test_alignment_then_demodulate(self, sync_word):
        """测试同步 → 提取 → 解调 → 恢复的完整流程。"""
        from src.synchronizer import FrameSynchronizer
        from src.qpsk import qpsk_modulate, qpsk_demodulate_hard

        frame_len_bits = len(sync_word) + 16 + 256
        frame_len_sym = frame_len_bits // 2

        syncer = FrameSynchronizer(
            sync_word=sync_word,
            frame_length_symbols=frame_len_sym
        )

        # 构造完整帧
        length_bits = np.zeros(16, dtype=np.uint8)
        length_val = 256
        for i in range(16):
            length_bits[i] = (length_val >> (15 - i)) & 1
        payload = np.random.RandomState(7).randint(0, 2, size=256, dtype=np.uint8)
        frame_bits = np.concatenate([sync_word, length_bits, payload])
        symbols = qpsk_modulate(frame_bits)

        # 添加偏移
        offset = 20
        rng = np.random.RandomState(8)
        noisy_prefix = (rng.randn(offset) + 1j * rng.randn(offset)) * 0.05
        all_sym = np.concatenate([noisy_prefix, symbols])

        # 同步
        starts = syncer.find_frame_starts(all_sym)
        assert len(starts) >= 1

        # 提取并解调
        frames = syncer.extract_frames(all_sym, starts)
        recovered = qpsk_demodulate_hard(frames[0])
        assert np.array_equal(recovered, frame_bits)
