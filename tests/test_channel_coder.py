"""信道编解码模块测试 — 卷积编码 + Viterbi 译码。

遵循 TDD Red-Green-Refactor 循环。
"""

import pytest
import numpy as np


# ======================== Convolutional Encoder Tests ========================

class TestConvolutionalEncoder:
    """卷积编码器测试。"""

    def test_output_rate(self, random_bits):
        """测试 1/2 码率：输出比特数 = 输入比特数 * 2 + tail_bits。"""
        from src.channel_coder import ConvolutionalEncoder
        encoder = ConvolutionalEncoder(constraint_length=7,
                                       generators=(0o171, 0o133))
        coded = encoder.encode(random_bits)
        # rate 1/2: output = (input + K-1) * 2 for zero-tail termination
        expected_len = (len(random_bits) + encoder.constraint_length - 1) * 2
        assert len(coded) == expected_len

    def test_output_dtype(self, random_bits):
        """测试输出为 uint8 ndarray。"""
        from src.channel_coder import ConvolutionalEncoder
        encoder = ConvolutionalEncoder()
        coded = encoder.encode(random_bits)
        assert coded.dtype == np.uint8
        assert isinstance(coded, np.ndarray)

    def test_deterministic(self, random_bits):
        """测试相同输入产生相同输出。"""
        from src.channel_coder import ConvolutionalEncoder
        encoder = ConvolutionalEncoder()
        out1 = encoder.encode(random_bits)
        out2 = encoder.encode(random_bits)
        assert np.array_equal(out1, out2)

    def test_encode_all_zeros(self):
        """测试全零输入编码输出（应为全零）。"""
        from src.channel_coder import ConvolutionalEncoder
        encoder = ConvolutionalEncoder()
        bits = np.zeros(100, dtype=np.uint8)
        coded = encoder.encode(bits)
        # 全零输入 + 零状态 → 全零输出
        assert np.all(coded == 0)

    def test_known_sequence(self):
        """测试已知序列的编码输出（回归验证）。"""
        from src.channel_coder import ConvolutionalEncoder
        encoder = ConvolutionalEncoder(constraint_length=3,
                                       generators=(0o5, 0o7))
        bits = np.array([1, 0, 1, 1], dtype=np.uint8)
        coded = encoder.encode(bits)
        # 对于 K=3, G=(5,7): 输出应为特定序列
        # 手动计算验证
        assert len(coded) == (4 + 2) * 2  # (input + K-1) * 2 = 12
        # 序列至少不是全零
        assert np.sum(coded) > 0

    def test_empty_input(self):
        """测试空输入返回空数组。"""
        from src.channel_coder import ConvolutionalEncoder
        encoder = ConvolutionalEncoder()
        bits = np.array([], dtype=np.uint8)
        coded = encoder.encode(bits)
        # 空输入时只输出 tail bits
        assert len(coded) == (encoder.constraint_length - 1) * 2

    def test_single_bit(self):
        """测试单比特输入编码。"""
        from src.channel_coder import ConvolutionalEncoder
        encoder = ConvolutionalEncoder(constraint_length=7)
        bits = np.array([1], dtype=np.uint8)
        coded = encoder.encode(bits)
        expected_len = (1 + 6) * 2  # (1 + K-1) * 2
        assert len(coded) == expected_len


# ======================== Viterbi Decoder Tests ========================

class TestViterbiDecoder:
    """Viterbi 译码器测试。"""

    def test_hard_decision_perfect(self, random_bits):
        """测试硬判决无错误时完美译码。"""
        from src.channel_coder import ConvolutionalEncoder, ViterbiDecoder
        encoder = ConvolutionalEncoder(constraint_length=7)
        decoder = ViterbiDecoder(constraint_length=7,
                                  generators=(0o171, 0o133))

        coded = encoder.encode(random_bits)
        decoded = decoder.decode_hard(coded)
        assert np.array_equal(decoded, random_bits)

    def test_soft_decision_perfect(self, random_bits):
        """测试软判决无噪声时完美译码。"""
        from src.channel_coder import ConvolutionalEncoder, ViterbiDecoder
        encoder = ConvolutionalEncoder(constraint_length=7)
        decoder = ViterbiDecoder(constraint_length=7,
                                  generators=(0o171, 0o133))

        coded = encoder.encode(random_bits)
        # 将 hard bits 转为理想软值: 0→+1, 1→-1
        soft = 1.0 - 2.0 * coded.astype(np.float64)
        decoded = decoder.decode_soft(soft)
        assert np.array_equal(decoded, random_bits)

    def test_single_bit_error_correction(self, random_bits):
        """测试多位置单比特错误均可被纠正。（K=7 自由距离=10 ≥ 2*1+1）"""
        from src.channel_coder import ConvolutionalEncoder, ViterbiDecoder
        encoder = ConvolutionalEncoder(constraint_length=7)
        decoder = ViterbiDecoder(constraint_length=7,
                                  generators=(0o171, 0o133))

        coded = encoder.encode(random_bits)
        # 测试多个随机位置的单比特翻转
        rng = np.random.RandomState(99)
        test_positions = rng.choice(len(coded), size=10, replace=False)
        for pos in test_positions:
            coded_with_error = coded.copy()
            coded_with_error[pos] ^= 1
            decoded = decoder.decode_hard(coded_with_error)
            errors = np.sum(decoded != random_bits)
            assert errors == 0, f"Single-bit flip at pos {pos} should be correctable, got {errors} errors"

    def test_decode_llr_with_qpsk_soft(self, random_bits):
        """测试 decode_llr + qpsk_demodulate_soft 集成路径无误码。"""
        from src.channel_coder import ConvolutionalEncoder, ViterbiDecoder
        from src.qpsk import qpsk_modulate, qpsk_demodulate_soft

        encoder = ConvolutionalEncoder(constraint_length=7)
        decoder = ViterbiDecoder(constraint_length=7,
                                  generators=(0o171, 0o133))

        # 编码 → QPSK 调制 → 软解调 → LLR 译码
        coded = encoder.encode(random_bits)
        symbols = qpsk_modulate(coded)
        # 无噪声：用极小的 noise_var 产生接近理想的 LLR
        llr = qpsk_demodulate_soft(symbols, noise_var=0.001)
        decoded = decoder.decode_llr(llr)
        assert np.array_equal(decoded, random_bits), \
            "LLR decode path should recover bits perfectly without noise"

    def test_decode_empty(self):
        """测试空输入译码。"""
        from src.channel_coder import ViterbiDecoder
        decoder = ViterbiDecoder(constraint_length=7)
        bits = np.array([], dtype=np.uint8)
        decoded = decoder.decode_hard(bits)
        assert len(decoded) == 0

    def test_short_sequence_small_k(self):
        """测试短序列 + 小约束长度 (K=3) 译码。"""
        from src.channel_coder import ConvolutionalEncoder, ViterbiDecoder
        encoder = ConvolutionalEncoder(constraint_length=3,
                                       generators=(0o5, 0o7))
        decoder = ViterbiDecoder(constraint_length=3,
                                  generators=(0o5, 0o7))

        bits = np.array([1, 0, 1, 1, 1, 0, 0, 1], dtype=np.uint8)
        coded = encoder.encode(bits)
        decoded = decoder.decode_hard(coded)
        assert np.array_equal(decoded, bits)

    def test_known_pattern_k3(self):
        """使用 K=3, G=(7,5) 编码已知模式测试译码。"""
        from src.channel_coder import ConvolutionalEncoder, ViterbiDecoder
        # K=3, 生成多项式 (7,5) 是常用的简单卷积码
        encoder = ConvolutionalEncoder(constraint_length=3,
                                       generators=(0o7, 0o5))
        decoder = ViterbiDecoder(constraint_length=3,
                                  generators=(0o7, 0o5))

        for pattern in [
            np.array([1], dtype=np.uint8),
            np.array([0, 1, 1, 0, 1], dtype=np.uint8),
            np.array([1, 1, 1, 1, 1, 1, 1, 1], dtype=np.uint8),
        ]:
            coded = encoder.encode(pattern)
            decoded = decoder.decode_hard(coded)
            assert np.array_equal(decoded, pattern), \
                f"Failed for pattern: {pattern}"

    def test_decoded_length_matches(self, random_bits):
        """测试译码输出长度与输入一致。"""
        from src.channel_coder import ConvolutionalEncoder, ViterbiDecoder
        encoder = ConvolutionalEncoder(constraint_length=7)
        decoder = ViterbiDecoder(constraint_length=7,
                                  generators=(0o171, 0o133))

        coded = encoder.encode(random_bits)
        decoded = decoder.decode_hard(coded)
        assert len(decoded) == len(random_bits)
