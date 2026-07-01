"""信源编解码模块 — 文本文件 ↔ 比特序列转换。

将文本文件（UTF-8 编码）转换为比特序列，并支持反向恢复。
"""

import numpy as np
import warnings
from pathlib import Path


def text_to_bits(file_path: str) -> tuple[np.ndarray, dict]:
    """读取文本文件，编码为比特序列。

    Args:
        file_path: 输入文本文件路径。

    Returns:
        bits: 比特序列 (uint8 ndarray, 每个元素 0 或 1)。
        metadata: 包含 filename, num_bytes, num_bits 的字典。
    """
    path = Path(file_path)
    raw_bytes = path.read_bytes()
    num_bytes = len(raw_bytes)
    num_bits = num_bytes * 8

    bits = np.unpackbits(np.frombuffer(raw_bytes, dtype=np.uint8))

    metadata = {
        'filename': path.name,
        'num_bytes': num_bytes,
        'num_bits': num_bits,
    }
    return bits, metadata


def bits_to_text(bits: np.ndarray, metadata: dict, output_path: str) -> str:
    """将比特序列解码为文本文件。

    Args:
        bits: 比特序列 (uint8 ndarray)。
        metadata: text_to_bits 返回的 metadata 字典（用于截断到原始比特数）。
        output_path: 输出文件路径。

    Returns:
        output_path: 写入的文件路径。
    """
    # 使用 metadata 中的原始比特数截断
    expected_bits = metadata.get('num_bits', len(bits))
    if len(bits) > expected_bits:
        bits = bits[:expected_bits]

    num_bits = len(bits)

    # 丢弃不足一个字节的尾部比特（通常由噪声导致译码输出长度不匹配）
    byte_aligned_bits = num_bits - (num_bits % 8)
    if byte_aligned_bits < num_bits:
        warnings.warn(
            f"Dropping {num_bits - byte_aligned_bits} trailing bits "
            f"(not byte-aligned). Check for pipeline alignment issues "
            f"or transmission errors."
        )
        bits = bits[:byte_aligned_bits]

    if len(bits) == 0:
        raw_bytes = b''
    else:
        raw_bytes = np.packbits(bits).tobytes()

    out_path = Path(output_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_bytes(raw_bytes)

    return str(out_path)
