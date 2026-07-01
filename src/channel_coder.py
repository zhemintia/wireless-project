"""信道编解码模块 — 卷积编码 + Viterbi 译码。

实现 (2,1,K) 卷积码编码器和 Viterbi 最大似然序列估计 (MLSE) 译码器。
支持硬判决和软判决两种译码模式。

默认参数:
- 约束长度 K = 7
- 生成多项式: G1 = 171 (八进制), G2 = 133 (八进制)
- 码率: 1/2
"""

import numpy as np
from typing import Optional


class ConvolutionalEncoder:
    """卷积编码器。

    使用零尾比特终止 (zero-tail termination)，在输入序列末尾追加 K-1 个零
    以驱动编码器回到全零状态。

    Attributes:
        constraint_length: 约束长度 K。
        generators: 生成多项式元组（八进制表示）。
        num_outputs: 输出分支数 (= len(generators))。
    """

    def __init__(
        self,
        constraint_length: int = 7,
        generators: tuple = (0o171, 0o133),
    ):
        self.constraint_length = constraint_length
        self.generators = generators
        self.num_outputs = len(generators)

        # 预计算每个可能状态 (0..2^(K-1)-1) 和每个输入比特 (0/1) 的输出
        self._num_states = 1 << (constraint_length - 1)

    def _conv_encode_bit(self, state: int, bit: int) -> tuple[np.ndarray, int]:
        """对单个比特编码。

        Args:
            state: 当前移位寄存器状态 (K-1 bits)。
            bit: 输入比特 (0 或 1)。

        Returns:
            (output_bits, next_state): 输出比特和下一状态。
        """
        # 将输入比特移入状态寄存器
        new_state = ((bit << (self.constraint_length - 1)) | state) >> 1

        output = np.zeros(self.num_outputs, dtype=np.uint8)
        for i, gen in enumerate(self.generators):
            # 生成多项式与扩展状态做点积（XOR parity）
            extended = (bit << (self.constraint_length - 1)) | state
            parity = bin(extended & gen).count('1') % 2
            output[i] = parity

        return output, new_state

    def encode(self, bits: np.ndarray) -> np.ndarray:
        """卷积编码。

        Args:
            bits: 输入比特序列 (uint8 ndarray)。

        Returns:
            编码后的比特序列，长度为 (len(bits) + K - 1) * num_outputs。
        """
        if len(bits) == 0:
            # 无输入时仍需输出 tail bits
            state = 0
            coded = []
            for _ in range(self.constraint_length - 1):
                outs, state = self._conv_encode_bit(state, 0)
                coded.extend(outs)
            return np.array(coded, dtype=np.uint8)

        state = 0
        coded = []

        # 信息比特编码
        for bit in bits:
            outs, state = self._conv_encode_bit(state, int(bit))
            coded.extend(outs)

        # Tail bits: K-1 个零比特将编码器归零
        for _ in range(self.constraint_length - 1):
            outs, state = self._conv_encode_bit(state, 0)
            coded.extend(outs)

        return np.array(coded, dtype=np.uint8)


class ViterbiDecoder:
    """Viterbi 译码器。

    使用最大似然序列估计 (MLSE) 方法译码卷积码。
    支持硬判决（汉明距离）和软判决（欧氏距离）。

    Attributes:
        constraint_length: 约束长度 K。
        generators: 生成多项式元组（八进制表示）。
        num_outputs: 输出分支数。
    """

    def __init__(
        self,
        constraint_length: int = 7,
        generators: tuple = (0o171, 0o133),
    ):
        self.constraint_length = constraint_length
        self.generators = generators
        self.num_outputs = len(generators)
        self._num_states = 1 << (constraint_length - 1)
        self._tail_bits = constraint_length - 1

        # 预计算所有状态转移的输出
        self._output_table = self._build_output_table()

    def _build_output_table(self) -> dict:
        """构建状态转移输出表。

        Returns:
            字典 {(state, bit): (output_bits, next_state)}。
        """
        table = {}
        for state in range(self._num_states):
            for bit in (0, 1):
                new_state = ((bit << (self.constraint_length - 1)) | state) >> 1
                output = np.zeros(self.num_outputs, dtype=np.uint8)
                for i, gen in enumerate(self.generators):
                    extended = (bit << (self.constraint_length - 1)) | state
                    parity = bin(extended & gen).count('1') % 2
                    output[i] = parity
                table[(state, bit)] = (output, new_state)
        return table

    def decode_hard(self, coded_bits: np.ndarray) -> np.ndarray:
        """硬判决 Viterbi 译码（汉明距离度量）。

        Args:
            coded_bits: 编码后的比特序列 (uint8 ndarray)。

        Returns:
            译码后的信息比特序列 (uint8 ndarray)。
        """
        if len(coded_bits) == 0:
            return np.array([], dtype=np.uint8)

        assert len(coded_bits) % self.num_outputs == 0, \
            f"coded_bits length ({len(coded_bits)}) not multiple of {self.num_outputs}"
        num_branches = len(coded_bits) // self.num_outputs

        # 路径度量: (num_branches + 1, num_states), 初始化为无穷大
        path_metric = np.full((num_branches + 1, self._num_states), np.inf)
        path_metric[0, 0] = 0.0

        # 幸存前一状态: (num_branches, num_states) — 记录到达 next_state 的来源 state
        survivor_prev = np.full((num_branches, self._num_states), -1, dtype=np.int32)

        for t in range(num_branches):
            branch_bits = coded_bits[t * self.num_outputs: (t + 1) * self.num_outputs]

            for state in range(self._num_states):
                if np.isinf(path_metric[t, state]):
                    continue

                for bit in (0, 1):
                    expected, next_state = self._output_table[(state, bit)]
                    dist = np.sum(branch_bits != expected)
                    new_metric = path_metric[t, state] + dist

                    if new_metric < path_metric[t + 1, next_state]:
                        path_metric[t + 1, next_state] = new_metric
                        survivor_prev[t, next_state] = state

        # 回溯
        info_length = num_branches - self._tail_bits
        if info_length <= 0:
            return np.array([], dtype=np.uint8)

        decoded = np.zeros(info_length, dtype=np.uint8)

        # 从最小度量终态回溯（零尾终止时理论上应为状态 0）
        best_state = int(np.argmin(path_metric[-1]))
        for t in range(num_branches - 1, -1, -1):
            prev_state = survivor_prev[t, best_state]
            # 从 prev_state 转移到 best_state 的输入比特
            bit = (best_state >> (self.constraint_length - 2)) & 1
            if t < info_length:
                decoded[t] = bit
            best_state = prev_state
            if prev_state < 0:  # 不应发生
                break

        return decoded

    def decode_soft(self, soft_bits: np.ndarray) -> np.ndarray:
        """软判决 Viterbi 译码（欧氏距离度量）。

        Args:
            soft_bits: 软值序列（浮点 ndarray, 建议 BPSK 映射: 0→+1, 1→-1）。

        Returns:
            译码后的信息比特序列 (uint8 ndarray)。
        """
        if len(soft_bits) == 0:
            return np.array([], dtype=np.uint8)

        assert len(soft_bits) % self.num_outputs == 0, \
            f"soft_bits length ({len(soft_bits)}) not multiple of {self.num_outputs}"
        num_branches = len(soft_bits) // self.num_outputs

        path_metric = np.full((num_branches + 1, self._num_states), np.inf)
        path_metric[0, 0] = 0.0

        survivor_prev = np.full((num_branches, self._num_states), -1, dtype=np.int32)

        for t in range(num_branches):
            branch_soft = soft_bits[t * self.num_outputs: (t + 1) * self.num_outputs]

            for state in range(self._num_states):
                if np.isinf(path_metric[t, state]):
                    continue

                for bit in (0, 1):
                    expected, next_state = self._output_table[(state, bit)]
                    expected_soft_val = 1.0 - 2.0 * expected.astype(np.float64)
                    dist = np.sum((branch_soft - expected_soft_val) ** 2)
                    new_metric = path_metric[t, state] + dist

                    if new_metric < path_metric[t + 1, next_state]:
                        path_metric[t + 1, next_state] = new_metric
                        survivor_prev[t, next_state] = state

        info_length = num_branches - self._tail_bits
        if info_length <= 0:
            return np.array([], dtype=np.uint8)

        decoded = np.zeros(info_length, dtype=np.uint8)
        # 从最小度量终态回溯（零尾终止时理论上应为状态 0，但有噪声时取 ML 估计）
        best_state = int(np.argmin(path_metric[-1]))

        for t in range(num_branches - 1, -1, -1):
            prev_state = survivor_prev[t, best_state]
            bit = (best_state >> (self.constraint_length - 2)) & 1
            if t < info_length:
                decoded[t] = bit
            best_state = prev_state
            if prev_state < 0:
                break

        return decoded
