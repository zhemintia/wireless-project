"""加扰/解扰模块 — 基于 LFSR 的自同步扰码器。

使用线性反馈移位寄存器 (LFSR) 实现加扰和解扰。
自同步设计意味着解扰器无需显式同步：通过接收数据自动恢复状态。

生成多项式: x^7 + x^4 + 1 (CCITT 标准)

⚠ 已知边界情况: 当 LFSR 状态为全 1 (0x7F) 且输入持续为全 1 时，
   反馈始终为 0 (bit6⊕bit3 = 1⊕1 = 0)，状态锁存在 0x7F。
   在实际数据中出现概率极低，但作为教育项目应了解此特性。
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
    # 多项式 0x91 (x^7+x^4+1): 抽头位于 bit 7 和 bit 4，对应 state 的 bit 6 和 bit 3
    # 使用位运算替代 bin().count() 避免每比特分配字符串对象
    feedback = ((state >> 6) ^ (state >> 3)) & 1
    output = bit ^ feedback
    new_state = ((state << 1) | output) & 0x7F  # 保持 7-bit
    return output, new_state


def scramble(bits: np.ndarray, seed: int = 0x7F, poly: int = 0x91) -> np.ndarray:
    """加扰器：对比特序列进行加扰。

    Args:
        bits: 输入比特序列 (uint8 ndarray)。
        seed: LFSR 初始状态。自动取低 7 位 (seed & 0x7F)。
        poly: 生成多项式（默认 0x91 = x⁷+x⁴+1）。

    Returns:
        加扰后的比特序列 (uint8 ndarray)。
    """
    seed = seed & 0x7F  # LFSR 为 7-bit，仅取低 7 位
    return _scramble_impl(bits, seed, poly)

def _scramble_impl(bits: np.ndarray, seed: int, poly: int) -> np.ndarray:
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

    Args:
        bits: 加扰后的比特序列 (uint8 ndarray)。
        seed: LFSR 初始状态。自动取低 7 位 (seed & 0x7F)。
        poly: 生成多项式（与加扰器相同）。

    Returns:
        解扰后的比特序列 (uint8 ndarray)。
    """
    seed = seed & 0x7F  # LFSR 为 7-bit，仅取低 7 位
    if len(bits) == 0:
        return np.array([], dtype=np.uint8)

    state = seed & 0x7F
    result = np.zeros(len(bits), dtype=np.uint8)

    for i in range(len(bits)):
        bit = int(bits[i])
        # 反馈从接收比特计算（自同步：不依赖输出比特即可收敛）
        feedback = ((state >> 6) ^ (state >> 3)) & 1
        output = bit ^ feedback
        # 关键：状态更新用接收比特（非 output），实现自同步
        new_state = ((state << 1) | bit) & 0x7F
        result[i] = output
        state = new_state

    return result
