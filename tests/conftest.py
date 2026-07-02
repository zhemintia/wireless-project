"""共享测试夹具 (fixtures)。

为所有测试模块提供可复用的测试数据和工具函数。
"""

import pytest
import numpy as np
import tempfile
from pathlib import Path


@pytest.fixture
def rng():
    """可复现的随机数生成器。"""
    return np.random.default_rng(42)


@pytest.fixture
def random_bits(rng):
    """生成 1024 个随机比特。"""
    return rng.integers(0, 2, size=1024, dtype=np.uint8)


@pytest.fixture
def random_bits_short(rng):
    """生成 256 个随机比特。"""
    return rng.integers(0, 2, size=256, dtype=np.uint8)


@pytest.fixture
def random_bits_long(rng):
    """生成 10000 个随机比特（用于测试多帧场景）。"""
    return rng.integers(0, 2, size=10000, dtype=np.uint8)


@pytest.fixture
def test_text_file():
    """创建临时测试文本文件，返回路径。"""
    content = (
        "Hello, Wireless Communication!\n"
        "This is a test file for the baseband simulation system.\n"
        "Testing: 1234567890!@#$%^&*()\n"
        "中文测试：无线通信基带仿真系统。\n"
        "Multiple lines to ensure proper encoding/decoding.\n"
    )
    with tempfile.NamedTemporaryFile(
        mode='w', suffix='.txt', delete=False, encoding='utf-8'
    ) as f:
        f.write(content)
        tmp_path = f.name
    yield tmp_path
    Path(tmp_path).unlink(missing_ok=True)


@pytest.fixture
def tmp_output_dir():
    """创建临时输出目录。"""
    d = tempfile.mkdtemp(prefix='wireless_test_')
    yield d
    import shutil
    shutil.rmtree(d, ignore_errors=True)


@pytest.fixture
def default_config():
    """返回默认配置（避免修改全局单例）。"""
    from src.config import WirelessConfig
    return WirelessConfig()
