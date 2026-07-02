"""信道编解码模块 — 卷积编码 + Viterbi 译码。

实现 (2,1,K) 卷积码编码器和 Viterbi 最大似然序列估计 (MLSE) 译码器。
支持硬判决和软判决两种译码模式。

默认参数:
- 约束长度 K = 7
- 生成多项式: G1 = 171 (八进制), G2 = 133 (八进制)
- 码率: 1/2
"""

import numpy as np


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

    def _conv_encode_bit(self, state: int, bit: int) -> tuple[np.ndarray, int]:
        """对单个比特编码（委托给共享静态方法确保与 Decoder 逻辑一致）。"""
        return ViterbiDecoder._encode_bit_static(
            state, bit, self.constraint_length,
            self.generators, self.num_outputs,
        )

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
    支持硬判决（汉明距离）和软判决（欧氏距离/LLR 相关度量）。

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

    @staticmethod
    def _encode_bit_static(state: int, bit: int, k: int, generators: tuple,
                           num_outputs: int) -> tuple[np.ndarray, int]:
        """静态编码逻辑 — Encoder 和 Decoder 共享的单一真相来源。

        Args:
            state: 当前移位寄存器状态 (K-1 bits)。
            bit: 输入比特 (0 或 1)。
            k: 约束长度。
            generators: 生成多项式元组。
            num_outputs: 输出分支数。

        Returns:
            (output_bits, next_state): 输出比特数组和下一状态。
        """
        new_state = ((bit << (k - 1)) | state) >> 1
        output = np.zeros(num_outputs, dtype=np.uint8)
        extended = (bit << (k - 1)) | state
        for i, gen in enumerate(generators):
            # 使用 int.bit_count() 替代 bin().count('1')，避免每比特分配字符串
            parity = (extended & gen).bit_count() % 2
            output[i] = parity
        return output, new_state

    def _build_output_table(self) -> dict:
        """构建状态转移输出表。

        使用共享的 _encode_bit_static 静态方法，确保与 Encoder 逻辑一致。

        Returns:
            字典 {(state, bit): (output_bits, next_state)}。
        """
        table = {}
        for state in range(self._num_states):
            for bit in (0, 1):
                table[(state, bit)] = self._encode_bit_static(
                    state, bit, self.constraint_length,
                    self.generators, self.num_outputs,
                )
        return table

    def _validate_input(self, data: np.ndarray, name: str) -> int:
        """验证输入长度并返回分支数。"""
        if len(data) == 0:
            return 0
        if len(data) % self.num_outputs != 0:
            raise ValueError(
                f"{name} length ({len(data)}) "
                f"not a multiple of num_outputs ({self.num_outputs})"
            )
        return len(data) // self.num_outputs

    def _acs_viterbi(self, num_branches: int, metric_fn) -> tuple:
        """ACS (Add-Compare-Select) Viterbi 核心循环。

        所有译码变体 (hard/soft/LLR) 共享相同的 ACS 结构，
        仅分支度量计算方式不同。

        Args:
            num_branches: 分支数（编码比特数 / num_outputs）。
            metric_fn: callable(t, state, bit, expected, next_state) -> float
                       返回从 state 经过 bit 到达 next_state 的分支度量。

        Returns:
            (survivor_prev, path_metric): 幸存前一状态数组和最终路径度量。
        """
        path_metric = np.full((num_branches + 1, self._num_states), np.inf)
        path_metric[0, 0] = 0.0

        survivor_prev = np.full((num_branches, self._num_states), -1, dtype=np.int32)

        for t in range(num_branches):
            for state in range(self._num_states):
                if np.isinf(path_metric[t, state]):
                    continue

                for bit in (0, 1):
                    expected, next_state = self._output_table[(state, bit)]
                    branch_metric = metric_fn(t, state, bit, expected, next_state)
                    new_metric = path_metric[t, state] + branch_metric

                    if new_metric < path_metric[t + 1, next_state]:
                        path_metric[t + 1, next_state] = new_metric
                        survivor_prev[t, next_state] = state

        return survivor_prev, path_metric

    def _traceback(self, survivor_prev: np.ndarray, path_metric: np.ndarray,
                   num_branches: int) -> np.ndarray:
        """Viterbi 回溯 — 从终态反推最优路径。

        注意: 当前帧大小 (~300 分支) 下路径度量无需归一化。
        若帧大小增加到 >10^4 级别，应考虑定期减去最小度量以防浮点溢出。

        Args:
            survivor_prev: 幸存前一状态数组。
            path_metric: 路径度量矩阵。
            num_branches: 总分支数（含 tail bits）。

        Returns:
            译码后的信息比特序列 (uint8 ndarray)。
        """
        info_length = num_branches - self._tail_bits
        if info_length <= 0:
            return np.array([], dtype=np.uint8)

        decoded = np.zeros(info_length, dtype=np.uint8)
        best_state = int(np.argmin(path_metric[-1]))

        for t in range(num_branches - 1, -1, -1):
            prev_state = survivor_prev[t, best_state]
            # 从 prev_state 转移到 best_state 的输入比特 = best_state 的 MSB
            bit = (best_state >> (self.constraint_length - 2)) & 1
            if t < info_length:
                decoded[t] = bit
            best_state = prev_state
            if prev_state < 0:  # 不应发生，防御性编程
                break

        return decoded

    def decode_hard(self, coded_bits: np.ndarray) -> np.ndarray:
        """硬判决 Viterbi 译码（汉明距离度量）。

        Args:
            coded_bits: 编码后的比特序列 (uint8 ndarray)。

        Returns:
            译码后的信息比特序列 (uint8 ndarray)。
        """
        num_branches = self._validate_input(coded_bits, "coded_bits")
        if num_branches == 0:
            return np.array([], dtype=np.uint8)

        # 预切片所有分支比特，避免在 metric_fn 中重复切片
        all_branches = coded_bits.reshape(num_branches, self.num_outputs)

        def metric_fn(t, state, bit, expected, next_state):
            return float(np.sum(all_branches[t] != expected))

        survivor_prev, path_metric = self._acs_viterbi(num_branches, metric_fn)
        return self._traceback(survivor_prev, path_metric, num_branches)

    def decode_soft(self, soft_bits: np.ndarray) -> np.ndarray:
        """软判决 Viterbi 译码（欧氏距离度量）。

        Args:
            soft_bits: 软值序列（浮点 ndarray, 建议 BPSK 映射: 0→+1, 1→-1）。

        Returns:
            译码后的信息比特序列 (uint8 ndarray)。
        """
        num_branches = self._validate_input(soft_bits, "soft_bits")
        if num_branches == 0:
            return np.array([], dtype=np.uint8)

        all_branches = soft_bits.reshape(num_branches, self.num_outputs)

        def metric_fn(t, state, bit, expected, next_state):
            expected_soft = 1.0 - 2.0 * expected.astype(np.float64)
            return float(np.sum((all_branches[t] - expected_soft) ** 2))

        survivor_prev, path_metric = self._acs_viterbi(num_branches, metric_fn)
        return self._traceback(survivor_prev, path_metric, num_branches)

    def decode_llr(self, llr_values: np.ndarray) -> np.ndarray:
        """LLR 输入 Viterbi 译码（相关度量 / ML 度量）。

        直接接受 qpsk_demodulate_soft() 输出的对数似然比 (LLR)。
        分支度量: -sum(LLR[i] * (1 - 2*expected[i])) 是 AWGN 下的 ML 度量。

        Args:
            llr_values: LLR 序列 (float64 ndarray), 长度 = num_branches * 2。

        Returns:
            译码后的信息比特序列 (uint8 ndarray)。
        """
        num_branches = self._validate_input(llr_values, "llr_values")
        if num_branches == 0:
            return np.array([], dtype=np.uint8)

        all_branches = llr_values.reshape(num_branches, self.num_outputs)

        def metric_fn(t, state, bit, expected, next_state):
            correlation = float(np.sum(
                all_branches[t] * (1.0 - 2.0 * expected.astype(np.float64))
            ))
            return -correlation

        survivor_prev, path_metric = self._acs_viterbi(num_branches, metric_fn)
        return self._traceback(survivor_prev, path_metric, num_branches)
