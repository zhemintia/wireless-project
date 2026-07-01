"""加扰/解扰模块 — 基于 LFSR 的自同步扰码器。

使用线性反馈移位寄存器 (LFSR) 实现加扰和解扰。
自同步设计意味着解扰器无需显式同步：通过接收数据自动恢复状态。

生成多项式: x^7 + x^4 + 1 (CCITT 标准)
"""

import numpy as np


def _lfsr_scramble_bit(bit: int, state: int, poly: int) -> tuple[int, int]:
    """对单个比特进行扰码处理（内部函数）。

    Args:
        bit: 输入比特 (0 或 1)。
        state: LFSR 当前状态（7-bit）。
        poly: 生成多项式。

    Returns:
        (output_bit, new_state): 输出比特和更新后的状态。
    """
    # 反馈比特 = 多项式抽头的 XOR
    # 将 state 左移 1 位后与 poly 做 AND，使 bit 7 对应 x^7 抽头
    feedback = bin(((state << 1) & poly)).count('1') % 2
    output = bit ^ feedback
    new_state = ((state << 1) | output) & 0x7F  # 保持 7-bit
    return output, new_state


def scramble(bits: np.ndarray, seed: int = 0x7F, poly: int = 0x91) -> np.ndarray:
    """加扰器：对比特序列进行加扰。

    使用自同步扰码方式，将每个输入比特与 LFSR 反馈比特 XOR。

    Args:
        bits: 输入比特序列 (uint8 ndarray, 每个元素 0 或 1)。
        seed: LFSR 初始状态（默认 0x7F，7-bit 全 1）。
        poly: 生成多项式（默认 0x91 = x^7 + x^4 + 1）。

    Returns:
        加扰后的比特序列 (uint8 ndarray)。
    """
    if len(bits) == 0:
        return np.array([], dtype=np.uint8)

    state = seed & 0x7F
    result = np.zeros(len(bits), dtype=np.uint8)

    for i in range(len(bits)):
        bit = int(bits[i])
        output, state = _lfsr_scramble_bit(bit, state, poly)
        result[i] = output

    return result


def descramble(bits: np.ndarray, seed: int = 0x7F, poly: int = 0x91) -> np.ndarray:
    """解扰器：对比特序列进行解扰。

    自同步解扰：使用与加扰器完全相同的 LFSR 结构。
    由于自同步特性，即使初始状态不同，经过 7 个比特后也能自动同步。

    Args:
        bits: 加扰后的比特序列 (uint8 ndarray)。
        seed: LFSR 初始状态（默认 0x7F）。
        poly: 生成多项式（与加扰器相同）。

    Returns:
        解扰后的比特序列 (uint8 ndarray)。
    """
    if len(bits) == 0:
        return np.array([], dtype=np.uint8)

    state = seed & 0x7F
    result = np.zeros(len(bits), dtype=np.uint8)

    for i in range(len(bits)):
        bit = int(bits[i])
        # 解扰器与加扰器结构相同
        # 反馈从接收比特计算（自同步特性）
        feedback = bin(((state << 1) & poly)).count('1') % 2
        output = bit ^ feedback
        new_state = ((state << 1) | bit) & 0x7F  # 使用接收比特更新状态
        result[i] = output
        state = new_state

    return result
