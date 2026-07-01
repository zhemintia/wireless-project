"""加扰/解扰模块测试。

遵循 TDD Red-Green-Refactor 循环：先写测试，再写实现。
"""

import pytest
import numpy as np


class TestScrambler:
    """加扰器 (scramble) 函数测试。"""

    def test_output_same_length(self, random_bits):
        """测试加扰前后比特数不变。"""
        from src.scrambler import scramble
        scrambled = scramble(random_bits)
        assert len(scrambled) == len(random_bits)
        assert scrambled.dtype == np.uint8

    def test_output_is_different_from_input(self, random_bits_long):
        """测试加扰确实改变了比特序列（非全零输入时）。"""
        from src.scrambler import scramble
        scrambled = scramble(random_bits_long)
        # 加扰后的序列应与输入不同（概率极高）
        assert not np.array_equal(scrambled, random_bits_long)

    def test_seed_reproducibility(self, random_bits):
        """测试相同 seed 产生相同的加扰输出。"""
        from src.scrambler import scramble
        result1 = scramble(random_bits, seed=0x5A)
        result2 = scramble(random_bits, seed=0x5A)
        assert np.array_equal(result1, result2)

    def test_different_seeds_different_outputs(self, random_bits_long):
        """测试不同 seed 产生不同的加扰输出。"""
        from src.scrambler import scramble
        result1 = scramble(random_bits_long, seed=0x5A)
        result2 = scramble(random_bits_long, seed=0x3C)
        assert not np.array_equal(result1, result2)

    def test_scramble_not_all_zeros(self, random_bits_long):
        """测试加扰输出不是全零（对于随机输入）。"""
        from src.scrambler import scramble
        scrambled = scramble(random_bits_long)
        assert np.sum(scrambled) > 0  # 对于 10000 bits，几乎不可能全零

    def test_empty_input(self):
        """测试空输入返回空数组。"""
        from src.scrambler import scramble
        result = scramble(np.array([], dtype=np.uint8))
        assert len(result) == 0

    def test_deterministic_known_input(self):
        """测试已知输入的加扰输出（用于回归验证）。"""
        from src.scrambler import scramble

        # 使用固定 seed 和已知输入验证输出确定性
        bits = np.array([1, 0, 1, 0, 1, 0, 1, 0, 1, 1, 0, 0, 1, 1, 1, 0],
                        dtype=np.uint8)
        result1 = scramble(bits, seed=0x7F)
        result2 = scramble(bits, seed=0x7F)
        assert np.array_equal(result1, result2)
        # 加扰后序列不应等于原始序列
        assert not np.array_equal(result1, bits)


class TestDescrambler:
    """解扰器 (descramble) 函数测试。"""

    def test_output_same_length(self, random_bits):
        """测试解扰前后比特数不变。"""
        from src.scrambler import scramble, descramble
        scrambled = scramble(random_bits)
        descrambled = descramble(scrambled)
        assert len(descrambled) == len(random_bits)

    def test_roundtrip(self, random_bits_long):
        """测试加扰→解扰 完整往返，应恢复原始比特。"""
        from src.scrambler import scramble, descramble
        scrambled = scramble(random_bits_long)
        recovered = descramble(scrambled)
        assert np.array_equal(recovered, random_bits_long)

    def test_roundtrip_different_seeds(self, random_bits_long):
        """测试不同 seed 下的往返，seed 匹配时解扰正确。"""
        from src.scrambler import scramble, descramble

        for seed in [0x12, 0x34, 0x56, 0x78, 0x7F]:
            scrambled = scramble(random_bits_long, seed=seed)
            recovered = descramble(scrambled, seed=seed)
            assert np.array_equal(recovered, random_bits_long), \
                f"Roundtrip failed for seed={seed:#04x}"

    def test_roundtrip_empty(self):
        """测试空数组的往返。"""
        from src.scrambler import scramble, descramble
        bits = np.array([], dtype=np.uint8)
        scrambled = scramble(bits)
        recovered = descramble(scrambled)
        assert len(recovered) == 0

    def test_roundtrip_single_bit(self):
        """测试单比特的往返。"""
        from src.scrambler import scramble, descramble
        for bit in [0, 1]:
            bits = np.array([bit], dtype=np.uint8)
            scrambled = scramble(bits, seed=0x7F)
            recovered = descramble(scrambled, seed=0x7F)
            assert recovered[0] == bit

    def test_roundtrip_all_zeros(self):
        """测试全零输入的往返。"""
        from src.scrambler import scramble, descramble
        bits = np.zeros(500, dtype=np.uint8)
        scrambled = scramble(bits)
        recovered = descramble(scrambled)
        assert np.array_equal(recovered, bits)

    def test_roundtrip_all_ones(self):
        """测试全一输入的往返。"""
        from src.scrambler import scramble, descramble
        bits = np.ones(500, dtype=np.uint8)
        scrambled = scramble(bits)
        recovered = descramble(scrambled)
        assert np.array_equal(recovered, bits)
