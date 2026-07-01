"""WirelessConfig 配置验证测试。"""

import numpy as np


class TestWirelessConfig:
    def test_default_values(self):
        from src.config import WirelessConfig
        cfg = WirelessConfig()

        # Sync word should be 32 bits
        assert len(cfg.sync_word) == 32
        assert cfg.sync_word.dtype == np.uint8

        # Frame payload should be positive
        assert cfg.frame_payload_bits > 0

        # Code rate
        assert 0 < cfg.channel_code_rate <= 1.0

        # SNR should be reasonable
        assert -20 <= cfg.default_snr_db <= 100

    def test_channel_code_rate_consistency(self):
        from src.config import WirelessConfig
        cfg = WirelessConfig()
        # For rate-1/2 code, the ratio should be 0.5
        assert cfg.channel_code_rate == 0.5

    def test_sync_word_is_valid(self):
        from src.config import WirelessConfig
        cfg = WirelessConfig()
        # Sync word should have both 0s and 1s
        assert np.sum(cfg.sync_word) > 0
        assert np.sum(cfg.sync_word) < len(cfg.sync_word)
