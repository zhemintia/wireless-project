"""metrics 模块的独立单元测试。"""

import pytest
import numpy as np
import tempfile
from pathlib import Path


class TestComputeBER:
    def test_no_errors(self):
        from src.metrics import compute_ber
        tx = np.array([0, 1, 0, 1, 1, 0, 1, 1], dtype=np.uint8)
        ber, errors = compute_ber(tx, tx)
        assert ber == 0.0
        assert errors == 0

    def test_all_errors(self):
        from src.metrics import compute_ber
        tx = np.array([0, 0, 0, 0], dtype=np.uint8)
        rx = np.array([1, 1, 1, 1], dtype=np.uint8)
        ber, errors = compute_ber(tx, rx)
        assert ber == 1.0
        assert errors == 4

    def test_half_errors(self):
        from src.metrics import compute_ber
        tx = np.array([0, 0, 1, 1], dtype=np.uint8)
        rx = np.array([1, 1, 1, 1], dtype=np.uint8)
        ber, errors = compute_ber(tx, rx)
        assert ber == 0.5
        assert errors == 2

    def test_different_lengths(self):
        from src.metrics import compute_ber
        tx = np.array([0, 1, 0, 1, 0, 1], dtype=np.uint8)
        rx = np.array([1, 1, 0, 1], dtype=np.uint8)
        ber, errors = compute_ber(tx, rx)
        assert 0 <= ber <= 1.0

    def test_empty(self):
        from src.metrics import compute_ber
        tx = np.array([], dtype=np.uint8)
        rx = np.array([], dtype=np.uint8)
        ber, errors = compute_ber(tx, rx)
        assert ber == 0.0
        assert errors == 0


class TestComputeFER:
    def test_no_errors(self):
        from src.metrics import compute_fer
        frames = [np.ones(10, dtype=np.uint8), np.zeros(5, dtype=np.uint8)]
        assert compute_fer(frames, frames) == 0.0

    def test_one_error(self):
        from src.metrics import compute_fer
        tx = [np.array([0, 1, 0], dtype=np.uint8)]
        rx = [np.array([1, 1, 0], dtype=np.uint8)]
        fer = compute_fer(tx, rx)
        assert fer == 1.0

    def test_empty(self):
        from src.metrics import compute_fer
        assert compute_fer([], []) == 0.0


class TestComputeTextRecoveryRate:
    def test_perfect(self):
        import tempfile
        content = "Hello World"
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
            f.write(content)
            orig = f.name
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
            f.write(content)
            recv = f.name
        try:
            from src.metrics import compute_text_recovery_rate
            rate = compute_text_recovery_rate(orig, recv)
            assert rate == 1.0
        finally:
            Path(orig).unlink(missing_ok=True)
            Path(recv).unlink(missing_ok=True)

    def test_completely_different(self):
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
            f.write("AAAAA")
            orig = f.name
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
            f.write("BBBBB")
            recv = f.name
        try:
            from src.metrics import compute_text_recovery_rate
            rate = compute_text_recovery_rate(orig, recv)
            assert rate == 0.0
        finally:
            Path(orig).unlink(missing_ok=True)
            Path(recv).unlink(missing_ok=True)

    def test_missing_file(self):
        import pytest
        from src.metrics import compute_text_recovery_rate
        # 原始文件不存在时应抛出 FileNotFoundError（而非返回 0.0 掩盖配置错误）
        with pytest.raises(FileNotFoundError):
            compute_text_recovery_rate('nonexistent_abc.txt', 'nonexistent_def.txt')
