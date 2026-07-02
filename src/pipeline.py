"""端到端无线通信 Pipeline 编排模块。

将发射机、信道和接收机各模块串联，实现完整的文件传输仿真链路。
"""

import numpy as np
import json
from pathlib import Path
from typing import Optional

from src.config import WirelessConfig
from src.source_coder import text_to_bits, bits_to_text
from src.scrambler import scramble, descramble
from src.channel_coder import ConvolutionalEncoder, ViterbiDecoder
from src.frame import FramePacker, FrameUnpacker
from src.qpsk import qpsk_modulate, qpsk_demodulate_hard, qpsk_demodulate_soft
from src.awgn import awgn_channel, snr_db_to_noise_var
from src.synchronizer import FrameSynchronizer
from src.metrics import compute_ber, compute_fer, compute_text_recovery_rate


class WirelessPipeline:
    """无线通信基带仿真 Pipeline。

    串联完整的发射→信道→接收链路。
    """

    def __init__(self, config: Optional[WirelessConfig] = None):
        """
        Args:
            config: 系统配置。None 时使用默认配置。
        """
        self.config = config or WirelessConfig()
        cfg = self.config

        # 发射机模块
        self.encoder = ConvolutionalEncoder(
            constraint_length=cfg.constraint_length,
            generators=cfg.generator_polynomials,
        )
        self.packer = FramePacker(
            sync_word=cfg.sync_word,
            payload_bits=cfg.frame_payload_bits,
        )

        # 接收机模块
        self.decoder = ViterbiDecoder(
            constraint_length=cfg.constraint_length,
            generators=cfg.generator_polynomials,
        )
        self.unpacker = FrameUnpacker(
            sync_word=cfg.sync_word,
            payload_bits=cfg.frame_payload_bits,
        )

        # 帧同步参数
        sw_len = len(cfg.sync_word)
        frame_total_bits = sw_len + 16 + cfg.frame_payload_bits
        assert frame_total_bits % 2 == 0, \
            f"Frame total bits must be even, got {frame_total_bits}"
        self._frame_sym_len = frame_total_bits // 2
        self.synchronizer = FrameSynchronizer(
            sync_word=cfg.sync_word,
            frame_length_symbols=self._frame_sym_len,
            threshold_factor=cfg.sync_threshold_factor,
        )

    def run(
        self,
        input_path: str,
        output_dir: str,
        snr_db: float = None,
        seed: int = None,
        sync_offset: int = None,
        soft_decision: bool = False,
    ) -> dict:
        """运行完整的端到端仿真。

        Args:
            input_path: 输入文本文件路径。
            output_dir: 输出目录路径。
            snr_db: Es/N0 信噪比 (dB)。None 时使用默认配置。
            seed: 随机数种子。None 时使用默认配置。
            sync_offset: 同步偏移（符号数）。None 时使用默认配置。
            soft_decision: True 时使用软解调+LLR译码（~2dB 增益）。

        Returns:
            metrics 字典，包含 BER、FER、text_recovery_rate 等。
        """
        cfg = self.config
        snr_db = snr_db if snr_db is not None else cfg.default_snr_db
        seed = seed if seed is not None else cfg.default_seed
        sync_offset = sync_offset if sync_offset is not None else cfg.sync_offset

        out_path = Path(output_dir)
        out_path.mkdir(parents=True, exist_ok=True)

        # ==================== 发射机 ====================

        # 1. 信源编码
        tx_bits, metadata = text_to_bits(input_path)

        # 2. 加扰
        tx_scrambled = scramble(tx_bits, seed=seed)

        # 空输入：直接复制文件
        if len(tx_bits) == 0:
            import shutil
            shutil.copy(input_path, str(out_path / 'received.txt'))
            return {
                'ber': 0.0, 'fer': 0.0, 'text_recovery_rate': 1.0,
                'total_bits': 0, 'bit_errors': 0, 'frame_errors': 0,
                'snr_db': snr_db,
            }

        # 3. 信道编码
        tx_encoded = self.encoder.encode(tx_scrambled)

        # 4. 帧封装
        frames = self.packer.pack(tx_encoded)
        all_tx_bits = np.concatenate(frames)

        # 5. QPSK 调制
        tx_symbols = qpsk_modulate(all_tx_bits)

        # ==================== 信道 ====================

        # 6. AWGN 信道
        rx_symbols = awgn_channel(tx_symbols, snr_db=snr_db, seed=seed)

        # 7. 添加同步偏移（模拟传输开始前的未知符号）
        # 偏移噪声幅度设为 0.01（远低于 QPSK 信号功率 1.0），确保同步器
        # 不会将噪声误检为帧起始，同时不影响后续帧的检测
        _SYNC_OFFSET_NOISE_AMPLITUDE = 0.01
        if sync_offset > 0:
            rng_seed = (seed + 1) % (2**31)
            rng = np.random.default_rng(rng_seed)
            offset_noise = (
                rng.standard_normal(sync_offset) +
                1j * rng.standard_normal(sync_offset)
            ) * _SYNC_OFFSET_NOISE_AMPLITUDE
            rx_symbols = np.concatenate([offset_noise, rx_symbols])

        # ==================== 接收机 ====================

        # 8. 帧同步
        frame_starts = self.synchronizer.find_frame_starts(rx_symbols)
        rx_frames_sym = self.synchronizer.extract_frames(rx_symbols, frame_starts)

        if not rx_frames_sym:
            # 同步失败：无法恢复
            return {
                'ber': 0.5, 'fer': 1.0, 'text_recovery_rate': 0.0,
                'total_bits': 0, 'bit_errors': 0, 'frame_errors': 0,
                'snr_db': snr_db, 'sync_failed': True,
            }

        # 9. QPSK 解调 → 硬比特（用于帧解封装 + FER 计算）
        rx_bits_list = [qpsk_demodulate_hard(fsym) for fsym in rx_frames_sym]
        if rx_bits_list:
            all_rx_bits = np.concatenate(rx_bits_list)
        else:
            all_rx_bits = np.array([], dtype=np.uint8)

        if len(all_rx_bits) < len(all_tx_bits):
            all_rx_bits = np.pad(all_rx_bits,
                                 (0, len(all_tx_bits) - len(all_rx_bits)))
        elif len(all_rx_bits) > len(all_tx_bits):
            all_rx_bits = all_rx_bits[:len(all_tx_bits)]

        # 10. 解帧
        rx_frames_bits = self._reshape_to_frames(all_rx_bits)
        rx_encoded, sync_errs = self.unpacker.unpack_with_sync_check(
            rx_frames_bits
        )

        # 11. 信道译码
        if soft_decision:
            # 软判决路径：每帧提取载荷对应的 LLR → Viterbi LLR 译码（~2dB 增益）
            noise_var_real = snr_db_to_noise_var(snr_db) / 2.0
            header_bits_per_frame = self.unpacker.header_bits  # sync + length
            payload_llr_list = []

            for fi, fsym in enumerate(rx_frames_sym):
                # 软解调该帧所有符号 → LLR（长度 = frame_total_bits）
                frame_llr = qpsk_demodulate_soft(fsym, noise_var=noise_var_real)

                # 从对应硬判决帧中读取长度字段以确定有效载荷比特数
                if fi < len(rx_frames_bits):
                    frame_bits = rx_frames_bits[fi]
                    len_start = self.unpacker.sw_len
                    len_end = len_start + self.unpacker.len_field_bits
                    length_bits = frame_bits[len_start:len_end]
                    if len(length_bits) >= self.unpacker._len_field_bits:
                        length_val = 0
                        for b in length_bits:
                            length_val = (length_val << 1) | int(b)
                        length_val = min(length_val, self.unpacker.payload_bits)
                    else:
                        length_val = 0
                    # 提取该帧载荷对应的 LLR
                    payload_start = header_bits_per_frame
                    payload_end = payload_start + length_val
                    if payload_end <= len(frame_llr):
                        payload_llr_list.append(frame_llr[payload_start:payload_end])
                    elif payload_start < len(frame_llr):
                        payload_llr_list.append(frame_llr[payload_start:])

            if payload_llr_list:
                all_rx_llr = np.concatenate(payload_llr_list)
            else:
                all_rx_llr = np.array([], dtype=np.float64)

            # 对齐 LLR 长度到编码比特数
            if len(all_rx_llr) < len(tx_encoded):
                all_rx_llr = np.pad(all_rx_llr,
                                     (0, len(tx_encoded) - len(all_rx_llr)))
            elif len(all_rx_llr) > len(tx_encoded):
                all_rx_llr = all_rx_llr[:len(tx_encoded)]

            rx_decoded = self.decoder.decode_llr(all_rx_llr)
        else:
            # 硬判决路径（默认）
            # 对齐编码比特长度
            if len(rx_encoded) < len(tx_encoded):
                rx_encoded = np.pad(rx_encoded,
                                    (0, len(tx_encoded) - len(rx_encoded)))
            elif len(rx_encoded) > len(tx_encoded):
                rx_encoded = rx_encoded[:len(tx_encoded)]

            rx_decoded = self.decoder.decode_hard(rx_encoded)

        # 12. 解扰
        rx_descrambled = descramble(rx_decoded, seed=seed)

        # 13. 信源解码
        received_path = str(out_path / 'received.txt')
        bits_to_text(rx_descrambled, metadata, received_path)

        # ==================== 指标计算 ====================

        # BER
        ber, bit_errors = compute_ber(tx_scrambled, rx_decoded)

        # FER（含同步错误帧）
        num_tx_frames = len(frames)
        fer_content = compute_fer(frames, rx_frames_bits)
        # compute_fer 已计入同步字损坏的帧（帧比特不匹配），sync_errs 仅作日志
        frame_errors_total = int(round(fer_content * num_tx_frames))
        fer = fer_content

        # 文本恢复率
        text_recovery = compute_text_recovery_rate(input_path, received_path)

        min_len = min(len(tx_scrambled), len(rx_decoded))

        metrics = {
            'ber': float(ber),
            'fer': float(fer),
            'text_recovery_rate': float(text_recovery),
            'total_bits': int(min_len),
            'bit_errors': int(bit_errors),
            'total_frames': int(num_tx_frames),
            'frame_errors': int(frame_errors_total),
            'snr_db': float(snr_db),
            'seed': int(seed),
            'sync_offset': int(sync_offset),
            # 实际仿真数据（供 CLI 绘图使用）
            # 内部数据（供 CLI 绘图，不写入 JSON）
            '_rx_symbols': rx_symbols,
            '_frame_starts': frame_starts,
            '_synchronizer': self.synchronizer,
        }

        # 保存 metrics.json（仅公共字段）
        json_metrics = {k: v for k, v in metrics.items() if not k.startswith('_')}
        metrics_path = out_path / 'metrics.json'
        with open(metrics_path, 'w', encoding='utf-8') as f:
            json.dump(json_metrics, f, indent=2, ensure_ascii=False)

        return metrics

    def _reshape_to_frames(self, bits: np.ndarray) -> list:
        """将一维比特流重塑为帧列表。"""
        frame_bits = self._frame_sym_len * 2
        frames = []
        pos = 0
        while pos + frame_bits <= len(bits):
            frames.append(bits[pos:pos + frame_bits])
            pos += frame_bits
        return frames

