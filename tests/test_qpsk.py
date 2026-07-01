"""QPSK 调制解调模块测试。

遵循 TDD Red-Green-Refactor 循环。
"""

import pytest
import numpy as np


# ======================== QPSK Modulator Tests ========================

class TestQPSKModulator:
    """QPSK 调制器测试。"""

    def test_output_is_complex(self, random_bits):
        """测试输出为复数 ndarray。"""
        from src.qpsk import qpsk_modulate
        symbols = qpsk_modulate(random_bits)
        assert np.iscomplexobj(symbols)

    def test_symbol_count(self, random_bits):
        """测试每 2 bits 产生 1 个符号。"""
        from src.qpsk import qpsk_modulate
        symbols = qpsk_modulate(random_bits)
        # 偶数比特数
        even_bits = random_bits[:len(random_bits) - (len(random_bits) % 2)]
        expected_symbols = len(even_bits) // 2
        assert len(symbols) == expected_symbols

    def test_odd_bits_truncated(self):
        """测试奇数个比特时丢弃最后一比特。"""
        from src.qpsk import qpsk_modulate
        bits = np.array([1, 0, 1, 1, 0], dtype=np.uint8)  # 5 bits
        symbols = qpsk_modulate(bits)
        assert len(symbols) == 2  # 地板除法

    def test_power_normalization(self, random_bits_long):
        """测试调制符号平均功率 ≈ 1。"""
        from src.qpsk import qpsk_modulate
        symbols = qpsk_modulate(random_bits_long)
        avg_power = np.mean(np.abs(symbols) ** 2)
        assert abs(avg_power - 1.0) < 0.01

    def test_four_constellation_points(self, random_bits_long):
        """测试 QPSK 产生 4 个星座点。"""
        from src.qpsk import qpsk_modulate
        symbols = qpsk_modulate(random_bits_long)
        # 四舍五入到合理精度后应有恰好 4 个唯一点
        rounded = np.round(symbols, decimals=6)
        unique = np.unique(rounded)
        assert len(unique) == 4


class TestQPSKDemodulatorHard:
    """QPSK 硬判决解调器测试。"""

    def test_perfect_recovery(self, random_bits):
        """测试无噪声时完美恢复比特。"""
        from src.qpsk import qpsk_modulate, qpsk_demodulate_hard
        symbols = qpsk_modulate(random_bits)
        recovered = qpsk_demodulate_hard(symbols)
        # 对齐到偶数
        even_len = len(random_bits) - (len(random_bits) % 2)
        assert np.array_equal(recovered, random_bits[:even_len])

    def test_output_dtype(self, random_bits):
        """测试输出为 uint8 ndarray。"""
        from src.qpsk import qpsk_modulate, qpsk_demodulate_hard
        symbols = qpsk_modulate(random_bits)
        recovered = qpsk_demodulate_hard(symbols)
        assert recovered.dtype == np.uint8

    def test_empty_input(self):
        """测试空输入。"""
        from src.qpsk import qpsk_modulate, qpsk_demodulate_hard
        bits = np.array([], dtype=np.uint8)
        symbols = qpsk_modulate(bits)
        recovered = qpsk_demodulate_hard(symbols)
        assert len(recovered) == 0


class TestQPSKDemodulatorSoft:
    """QPSK 软判决 (LLR) 解调器测试。"""

    def test_output_is_float(self, random_bits):
        """测试软判决输出为浮点数。"""
        from src.qpsk import qpsk_modulate, qpsk_demodulate_soft
        symbols = qpsk_modulate(random_bits)
        llr = qpsk_demodulate_soft(symbols, noise_var=1.0)
        assert llr.dtype == np.float64

    def test_llr_sign_matches_bit(self, random_bits):
        """测试 LLR 符号匹配比特值（正 LLR → bit=0, 负 LLR → bit=1）。"""
        from src.qpsk import qpsk_modulate, qpsk_demodulate_soft
        symbols = qpsk_modulate(random_bits)
        llr = qpsk_demodulate_soft(symbols, noise_var=1.0)
        # 对无噪声信号，LLR 绝对值应很大
        hard_bits = (llr < 0).astype(np.uint8)
        even_len = len(random_bits) - (len(random_bits) % 2)
        assert np.array_equal(hard_bits, random_bits[:even_len])

    def test_high_noise_llr_smaller(self, random_bits):
        """测试高噪声时 LLR 绝对值变小（置信度降低）。"""
        from src.qpsk import qpsk_modulate, qpsk_demodulate_soft
        symbols = qpsk_modulate(random_bits)
        llr_low_noise = qpsk_demodulate_soft(symbols, noise_var=0.1)
        llr_high_noise = qpsk_demodulate_soft(symbols, noise_var=10.0)
        # 高噪声时平均 |LLR| 更小
        assert np.mean(np.abs(llr_high_noise)) < np.mean(np.abs(llr_low_noise))

    def test_empty_input(self):
        """测试空输入。"""
        from src.qpsk import qpsk_demodulate_soft
        bits = np.array([], dtype=np.uint8)
        symbols = np.array([], dtype=np.complex128)
        llr = qpsk_demodulate_soft(symbols, noise_var=1.0)
        assert len(llr) == 0


class TestGrayMapping:
    """Gray 映射测试。"""

    def test_adjacent_symbols_one_bit_diff(self):
        """测试相邻星座点仅 1 bit 差异（Gray 映射特性）。"""
        from src.qpsk import qpsk_modulate
        # 相邻的 2-bit 组合
        pairs = [
            np.array([0, 0], dtype=np.uint8),
            np.array([0, 1], dtype=np.uint8),
            np.array([1, 1], dtype=np.uint8),
            np.array([1, 0], dtype=np.uint8),
        ]
        symbols = [qpsk_modulate(p)[0] for p in pairs]
        # 取相位角度
        angles = np.angle(symbols)
        # 每个相邻对的角度差应约为 π/2
        for i in range(4):
            diff = abs(angles[i] - angles[(i + 1) % 4])
            # 角度差应在 π/2 附近
            assert abs(diff - np.pi / 2) < 0.1 or abs(diff - 3 * np.pi / 2) < 0.1
