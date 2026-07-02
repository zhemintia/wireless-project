"""无线通信文件传输基带仿真系统 - Wireless Communication Baseband Simulation System."""

from src.config import WirelessConfig
from src.pipeline import WirelessPipeline
from src.source_coder import text_to_bits, bits_to_text
from src.scrambler import scramble, descramble
from src.channel_coder import ConvolutionalEncoder, ViterbiDecoder
from src.frame import FramePacker, FrameUnpacker
from src.qpsk import qpsk_modulate, qpsk_demodulate_hard, qpsk_demodulate_soft
from src.awgn import awgn_channel, snr_db_to_noise_var, eb_n0_to_es_n0
from src.synchronizer import FrameSynchronizer
from src.metrics import compute_ber, compute_fer, compute_text_recovery_rate

__all__ = [
    "WirelessConfig",
    "WirelessPipeline",
    "text_to_bits",
    "bits_to_text",
    "scramble",
    "descramble",
    "ConvolutionalEncoder",
    "ViterbiDecoder",
    "FramePacker",
    "FrameUnpacker",
    "qpsk_modulate",
    "qpsk_demodulate_hard",
    "qpsk_demodulate_soft",
    "awgn_channel",
    "snr_db_to_noise_var",
    "eb_n0_to_es_n0",
    "FrameSynchronizer",
    "compute_ber",
    "compute_fer",
    "compute_text_recovery_rate",
]
