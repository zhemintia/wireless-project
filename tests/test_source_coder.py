"""信源编解码模块测试。

遵循 TDD Red-Green-Refactor 循环：先写测试，再写实现。
"""

import pytest
import numpy as np
from pathlib import Path


class TestTextToBits:
    """text_to_bits 函数测试。"""

    def test_output_types(self):
        """测试返回值类型：应返回 (ndarray, dict)。"""
        from src.source_coder import text_to_bits
        import tempfile

        with tempfile.NamedTemporaryFile(
            mode='w', suffix='.txt', delete=False, encoding='utf-8'
        ) as f:
            f.write("Hello")
            tmp = f.name

        try:
            bits, meta = text_to_bits(tmp)
            assert isinstance(bits, np.ndarray)
            assert bits.dtype == np.uint8
            assert isinstance(meta, dict)
            assert 'filename' in meta
            assert 'num_bytes' in meta
            assert 'num_bits' in meta
        finally:
            Path(tmp).unlink(missing_ok=True)

    def test_empty_file(self):
        """测试空文件：应返回空比特数组，num_bits=0。"""
        from src.source_coder import text_to_bits
        import tempfile

        with tempfile.NamedTemporaryFile(
            mode='w', suffix='.txt', delete=False, encoding='utf-8'
        ) as f:
            f.write("")
            tmp = f.name

        try:
            bits, meta = text_to_bits(tmp)
            assert len(bits) == 0
            assert meta['num_bytes'] == 0
            assert meta['num_bits'] == 0
        finally:
            Path(tmp).unlink(missing_ok=True)

    def test_simple_ascii(self):
        """测试简单 ASCII 文本：比特数 = 字节数 * 8。"""
        from src.source_coder import text_to_bits
        import tempfile

        content = "ABC"
        with tempfile.NamedTemporaryFile(
            mode='w', suffix='.txt', delete=False, encoding='utf-8'
        ) as f:
            f.write(content)
            tmp = f.name

        try:
            bits, meta = text_to_bits(tmp)
            assert len(bits) == len(content.encode('utf-8')) * 8
            assert meta['num_bytes'] == len(content.encode('utf-8'))
        finally:
            Path(tmp).unlink(missing_ok=True)

    def test_unicode_text(self):
        """测试包含中文等多字节字符的文本。"""
        from src.source_coder import text_to_bits
        import tempfile

        content = "中文测试 Test 日本語"
        with tempfile.NamedTemporaryFile(
            mode='w', suffix='.txt', delete=False, encoding='utf-8'
        ) as f:
            f.write(content)
            tmp = f.name

        try:
            bits, meta = text_to_bits(tmp)
            expected_bytes = len(content.encode('utf-8'))
            assert len(bits) == expected_bytes * 8
            assert meta['num_bytes'] == expected_bytes
        finally:
            Path(tmp).unlink(missing_ok=True)


class TestBitsToText:
    """bits_to_text 函数测试。"""

    def test_roundtrip_ascii(self, tmp_output_dir):
        """测试 ASCII 文本完整往返：写入→编码→解码→读取，内容一致。"""
        from src.source_coder import text_to_bits, bits_to_text
        import tempfile

        content = "Hello, World!\nLine 2\nLine 3"
        with tempfile.NamedTemporaryFile(
            mode='w', suffix='.txt', delete=False, encoding='utf-8'
        ) as f:
            f.write(content)
            tmp = f.name

        try:
            bits, meta = text_to_bits(tmp)
            out_path = Path(tmp_output_dir) / 'received.txt'
            bits_to_text(bits, meta, str(out_path))

            recovered = out_path.read_text(encoding='utf-8')
            assert recovered == content
        finally:
            Path(tmp).unlink(missing_ok=True)

    def test_roundtrip_unicode(self, tmp_output_dir):
        """测试包含 Unicode 文本的完整往返。"""
        from src.source_coder import text_to_bits, bits_to_text
        import tempfile

        content = "中文测试\n日本語テスト\n한국어\nEmoji: 🎉💻✨"
        with tempfile.NamedTemporaryFile(
            mode='w', suffix='.txt', delete=False, encoding='utf-8'
        ) as f:
            f.write(content)
            tmp = f.name

        try:
            bits, meta = text_to_bits(tmp)
            out_path = Path(tmp_output_dir) / 'received_unicode.txt'
            bits_to_text(bits, meta, str(out_path))

            recovered = out_path.read_text(encoding='utf-8')
            assert recovered == content
        finally:
            Path(tmp).unlink(missing_ok=True)

    def test_roundtrip_with_test_file(self, test_text_file, tmp_output_dir):
        """使用 conftest 中的标准测试文件进行往返测试。"""
        from src.source_coder import text_to_bits, bits_to_text

        original = Path(test_text_file).read_text(encoding='utf-8')
        bits, meta = text_to_bits(test_text_file)
        out_path = Path(tmp_output_dir) / 'received.txt'
        bits_to_text(bits, meta, str(out_path))

        recovered = out_path.read_text(encoding='utf-8')
        assert recovered == original

    def test_metadata_preserved(self, test_text_file):
        """测试 metadata 中文件名和大小正确。"""
        from src.source_coder import text_to_bits

        _, meta = text_to_bits(test_text_file)
        assert 'filename' in meta
        assert meta['filename'] == Path(test_text_file).name
        assert meta['num_bits'] % 8 == 0
        assert meta['num_bits'] // 8 == meta['num_bytes']

    def test_one_byte_file(self, tmp_output_dir):
        """测试单字节文件的编解码。"""
        from src.source_coder import text_to_bits, bits_to_text
        import tempfile

        content = "A"
        with tempfile.NamedTemporaryFile(
            mode='w', suffix='.txt', delete=False, encoding='utf-8'
        ) as f:
            f.write(content)
            tmp = f.name

        try:
            bits, meta = text_to_bits(tmp)
            assert len(bits) == 8
            out_path = Path(tmp_output_dir) / 'received_one_byte.txt'
            bits_to_text(bits, meta, str(out_path))
            assert out_path.read_text(encoding='utf-8') == "A"
        finally:
            Path(tmp).unlink(missing_ok=True)
