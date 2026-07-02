"""帧封装/解封装模块测试。

遵循 TDD Red-Green-Refactor 循环。
"""

import pytest
import numpy as np


# ======================== Frame Packer Tests ========================

class TestFramePacker:
    """帧封装器测试。"""

    def test_each_frame_starts_with_sync_word(self, random_bits, default_config):
        """测试每帧以同步字开头。"""
        from src.frame import FramePacker
        packer = FramePacker(
            sync_word=default_config.sync_word,
            payload_bits=default_config.frame_payload_bits,
        )
        frames = packer.pack(random_bits)
        sw_len = len(default_config.sync_word)
        for frame in frames:
            assert np.array_equal(frame[:sw_len], default_config.sync_word)

    def test_pack_unpack_roundtrip(self, random_bits_long, default_config):
        """测试封装→解封装 往返，数据比特一致。"""
        from src.frame import FramePacker, FrameUnpacker
        packer = FramePacker(
            sync_word=default_config.sync_word,
            payload_bits=default_config.frame_payload_bits,
        )
        unpacker = FrameUnpacker(
            sync_word=default_config.sync_word,
            payload_bits=default_config.frame_payload_bits,
        )
        frames = packer.pack(random_bits_long)
        recovered = unpacker.unpack(frames)
        assert np.array_equal(recovered, random_bits_long)

    def test_frame_structure_format(self, default_config):
        """测试帧结构格式正确：同步字 + 长度字段 + 数据。"""
        from src.frame import FramePacker
        packer = FramePacker(
            sync_word=default_config.sync_word,
            payload_bits=default_config.frame_payload_bits,
        )
        bits = np.ones(500, dtype=np.uint8)
        frames = packer.pack(bits)

        sw_len = len(default_config.sync_word)
        length_field_bits = 16  # 16-bit 长度字段
        expected_frame_len = sw_len + length_field_bits + default_config.frame_payload_bits

        for frame in frames:
            assert len(frame) == expected_frame_len

    def test_partial_last_frame(self, default_config):
        """测试最后一帧不满时正确填充。"""
        from src.frame import FramePacker, FrameUnpacker
        packer = FramePacker(
            sync_word=default_config.sync_word,
            payload_bits=default_config.frame_payload_bits,
        )
        unpacker = FrameUnpacker(
            sync_word=default_config.sync_word,
            payload_bits=default_config.frame_payload_bits,
        )
        # 比特数不是 payload_bits 的整数倍
        bits = np.ones(default_config.frame_payload_bits + 10, dtype=np.uint8)
        frames = packer.pack(bits)
        recovered = unpacker.unpack(frames)
        assert np.array_equal(recovered, bits)

    def test_single_frame(self, default_config):
        """测试数据刚好填满一帧。"""
        from src.frame import FramePacker, FrameUnpacker
        packer = FramePacker(
            sync_word=default_config.sync_word,
            payload_bits=default_config.frame_payload_bits,
        )
        unpacker = FrameUnpacker(
            sync_word=default_config.sync_word,
            payload_bits=default_config.frame_payload_bits,
        )
        bits = np.ones(default_config.frame_payload_bits, dtype=np.uint8)
        frames = packer.pack(bits)
        recovered = unpacker.unpack(frames)
        assert np.array_equal(recovered, bits)

    def test_empty_input(self, default_config):
        """测试空输入返回空帧列表。"""
        from src.frame import FramePacker
        packer = FramePacker(
            sync_word=default_config.sync_word,
            payload_bits=default_config.frame_payload_bits,
        )
        bits = np.array([], dtype=np.uint8)
        frames = packer.pack(bits)
        assert len(frames) == 0

    def test_length_field_accuracy(self, default_config):
        """测试长度字段准确记录每帧载荷比特数。"""
        from src.frame import FramePacker
        packer = FramePacker(
            sync_word=default_config.sync_word,
            payload_bits=default_config.frame_payload_bits,
        )
        # 数据刚好一帧
        bits = np.ones(default_config.frame_payload_bits, dtype=np.uint8)
        frames = packer.pack(bits)
        assert len(frames) == 1
        # 长度字段应在同步字之后
        sw_len = len(default_config.sync_word)
        length_bits = frames[0][sw_len:sw_len + 16]
        # 将 16-bit 大端序解析为整数
        length_val = 0
        for b in length_bits:
            length_val = (length_val << 1) | int(b)
        assert length_val == default_config.frame_payload_bits


class TestFrameUnpacker:
    """帧解封装器测试。"""

    def test_basic_unpack(self, default_config):
        """测试基本的帧→比特解封装。"""
        from src.frame import FramePacker, FrameUnpacker
        packer = FramePacker(
            sync_word=default_config.sync_word,
            payload_bits=default_config.frame_payload_bits,
        )
        unpacker = FrameUnpacker(
            sync_word=default_config.sync_word,
            payload_bits=default_config.frame_payload_bits,
        )
        bits = np.random.RandomState(0).randint(0, 2, size=300, dtype=np.uint8)
        frames = packer.pack(bits)
        recovered = unpacker.unpack(frames)
        assert np.array_equal(recovered, bits)

    def test_unpack_with_zero_padded_last_frame(self, default_config):
        """测试最后一帧含零填充时正确去除填充。"""
        from src.frame import FramePacker, FrameUnpacker
        packer = FramePacker(
            sync_word=default_config.sync_word,
            payload_bits=default_config.frame_payload_bits,
        )
        unpacker = FrameUnpacker(
            sync_word=default_config.sync_word,
            payload_bits=default_config.frame_payload_bits,
        )
        # 刚好少 1 bit 需要填充
        bits = np.ones(default_config.frame_payload_bits - 1, dtype=np.uint8)
        frames = packer.pack(bits)
        recovered = unpacker.unpack(frames)
        assert np.array_equal(recovered, bits)

    def test_empty_frames(self, default_config):
        """测试空帧列表返回空数组。"""
        from src.frame import FrameUnpacker
        unpacker = FrameUnpacker(
            sync_word=default_config.sync_word,
            payload_bits=default_config.frame_payload_bits,
        )
        frames = np.array([], dtype=np.uint8)
        recovered = unpacker.unpack(frames)
        assert len(recovered) == 0

    def test_multiple_frames(self, default_config):
        """测试多帧数据解封装。"""
        from src.frame import FramePacker, FrameUnpacker
        packer = FramePacker(
            sync_word=default_config.sync_word,
            payload_bits=default_config.frame_payload_bits,
        )
        unpacker = FrameUnpacker(
            sync_word=default_config.sync_word,
            payload_bits=default_config.frame_payload_bits,
        )
        # 数据跨越 3 帧
        bits = np.random.RandomState(1).randint(
            0, 2, size=default_config.frame_payload_bits * 2 + 100,
            dtype=np.uint8
        )
        frames = packer.pack(bits)
        assert len(frames) >= 3
        recovered = unpacker.unpack(frames)
        assert np.array_equal(recovered, bits)

    def test_unpack_with_sync_check_valid(self, default_config):
        """测试 unpack_with_sync_check：有效帧无同步错误。"""
        from src.frame import FramePacker, FrameUnpacker
        packer = FramePacker(
            sync_word=default_config.sync_word,
            payload_bits=default_config.frame_payload_bits,
        )
        unpacker = FrameUnpacker(
            sync_word=default_config.sync_word,
            payload_bits=default_config.frame_payload_bits,
        )
        bits = np.ones(default_config.frame_payload_bits, dtype=np.uint8)
        frames = packer.pack(bits)
        recovered, sync_errs = unpacker.unpack_with_sync_check(frames)
        assert len(sync_errs) == 0
        assert np.array_equal(recovered, bits)

    def test_unpack_with_sync_check_corrupted(self, default_config):
        """测试 unpack_with_sync_check：损坏同步字的帧被正确检测。"""
        from src.frame import FramePacker, FrameUnpacker
        packer = FramePacker(
            sync_word=default_config.sync_word,
            payload_bits=default_config.frame_payload_bits,
        )
        unpacker = FrameUnpacker(
            sync_word=default_config.sync_word,
            payload_bits=default_config.frame_payload_bits,
        )
        bits = np.ones(default_config.frame_payload_bits * 2 + 50, dtype=np.uint8)
        frames = packer.pack(bits)
        # 损坏第二帧的同步字
        frames[1][0] ^= 1
        recovered, sync_errs = unpacker.unpack_with_sync_check(frames)
        assert len(sync_errs) >= 1  # 第二帧同步字损坏
        assert 1 in sync_errs
        # 有效帧的载荷仍被提取
        assert len(recovered) > 0
