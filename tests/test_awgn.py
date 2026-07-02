"""AWGN 信道模块测试。

遵循 TDD Red-Green-Refactor 循环。
"""

import pytest
import numpy as np


class TestAWGNChannel:
    """AWGN 信道测试。"""

    def test_output_shape(self):
        """测试输出形状与输入一致。"""
        from src.awgn import awgn_channel
        symbols = np.random.randn(100) + 1j * np.random.randn(100)
        noisy = awgn_channel(symbols, snr_db=10.0)
        assert noisy.shape == symbols.shape

    def test_output_is_complex(self):
        """测试输出为复数。"""
        from src.awgn import awgn_channel
        symbols = np.ones(50, dtype=np.complex128)
        noisy = awgn_channel(symbols, snr_db=10.0)
        assert np.iscomplexobj(noisy)

    def test_high_snr_nearly_noiseless(self):
        """测试极高 SNR 时信号几乎不变。"""
        from src.awgn import awgn_channel
        symbols = np.ones(1000, dtype=np.complex128) * (1 + 1j) / np.sqrt(2)
        noisy = awgn_channel(symbols, snr_db=100.0)
        # SNR=100dB: noise_var = 10^(-10), MSE ≈ 1e-10
        mse = np.mean(np.abs(noisy - symbols) ** 2)
        assert mse < 1e-8  # 允许统计波动

    def test_low_snr_adds_noise(self):
        """测试低 SNR 时信号明显变化。"""
        from src.awgn import awgn_channel
        symbols = np.ones(1000, dtype=np.complex128) * (1 + 1j) / np.sqrt(2)
        noisy = awgn_channel(symbols, snr_db=-10.0)
        # SNR=-10dB: noise_var = 10^(10/10) = 10, MSE ≈ 10
        mse = np.mean(np.abs(noisy - symbols) ** 2)
        assert mse > 5.0  # 预期 ~10，保留裕度

    def test_seed_reproducibility(self):
        """测试相同 seed 产生相同噪声。"""
        from src.awgn import awgn_channel
        symbols = np.random.RandomState(0).randn(100) + 1j * np.random.RandomState(0).randn(100)
        noisy1 = awgn_channel(symbols, snr_db=10.0, seed=42)
        noisy2 = awgn_channel(symbols, snr_db=10.0, seed=42)
        assert np.allclose(noisy1, noisy2)

    def test_different_seeds_different_noise(self):
        """测试不同 seed 产生不同噪声。"""
        from src.awgn import awgn_channel
        symbols = np.ones(500, dtype=np.complex128)
        noisy1 = awgn_channel(symbols, snr_db=10.0, seed=1)
        noisy2 = awgn_channel(symbols, snr_db=10.0, seed=2)
        assert not np.allclose(noisy1, noisy2)

    def test_snr_increases_reduces_noise(self):
        """测试 SNR 越高噪声方差越小。"""
        from src.awgn import awgn_channel
        symbols = np.ones(1000, dtype=np.complex128) * (1 + 1j) / np.sqrt(2)
        noise_var_low_snr = np.var(
            awgn_channel(symbols, snr_db=0.0, seed=42) - symbols
        )
        noise_var_high_snr = np.var(
            awgn_channel(symbols, snr_db=20.0, seed=42) - symbols
        )
        # 高 SNR 噪声方差应更小
        assert noise_var_high_snr < noise_var_low_snr

    def test_empty_input(self):
        """测试空输入。"""
        from src.awgn import awgn_channel
        symbols = np.array([], dtype=np.complex128)
        noisy = awgn_channel(symbols, snr_db=10.0)
        assert len(noisy) == 0

    def test_zero_snr_finite_output(self):
        """测试 SNR=0 dB 时输出有限（不溢出）。"""
        from src.awgn import awgn_channel
        symbols = np.ones(100, dtype=np.complex128) * (1 + 1j) / np.sqrt(2)
        noisy = awgn_channel(symbols, snr_db=0.0)
        assert np.all(np.isfinite(noisy.real))
        assert np.all(np.isfinite(noisy.imag))


class TestNoisePower:
    """噪声功率计算测试。"""

    def test_snr_db_to_noise_var_es_n0(self):
        """测试 Es/N0 SNR 到噪声方差的关系。"""
        from src.awgn import snr_db_to_noise_var
        # Es/N0 = 10 dB → Es/N0_linear = 10
        # noise_var_complex = 1 / 10 = 0.1
        noise_var = snr_db_to_noise_var(snr_db=10.0)
        assert abs(noise_var - 0.1) < 0.001

    def test_eb_n0_to_es_n0(self):
        """测试 Eb/N0 与 Es/N0 的转换。"""
        from src.awgn import eb_n0_to_es_n0
        # QPSK: 2 bits/symbol, code_rate=1/2 → effective bits/symbol = 1
        # Es/N0 = Eb/N0 + 10*log10(1) = Eb/N0
        es_n0 = eb_n0_to_es_n0(eb_n0_db=5.0, bits_per_symbol=2, code_rate=0.5)
        assert abs(es_n0 - 5.0) < 0.01

        # code_rate=1, bits_per_symbol=2 → Es/N0 = Eb/N0 + 10*log10(2) = Eb/N0 + 3.01
        es_n0 = eb_n0_to_es_n0(eb_n0_db=5.0, bits_per_symbol=2, code_rate=1.0)
        assert abs(es_n0 - 8.01) < 0.1
