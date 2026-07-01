"""统一命令行入口模块。

提供无线通信基带仿真系统的 CLI 接口，支持参数化运行。
"""

import argparse
import sys
import numpy as np
from pathlib import Path

from src.config import WirelessConfig
from src.pipeline import WirelessPipeline
from src.metrics import plot_constellation, plot_ber_curve, plot_sync_correlation


def parse_args(argv=None):
    """解析命令行参数。"""
    parser = argparse.ArgumentParser(
        prog='wireless-sim',
        description='无线通信文件传输基带仿真系统 — 基于 AI 辅助编程',
    )

    parser.add_argument(
        '--input', '-i',
        default='Test.txt',
        help='输入文本文件路径 (默认: Test.txt)',
    )
    parser.add_argument(
        '--output-dir', '-o',
        default='output',
        help='输出目录路径 (默认: output)',
    )
    parser.add_argument(
        '--snr', '-s',
        type=float,
        default=10.0,
        help='Es/N0 信噪比 (dB, 默认: 10.0)',
    )
    parser.add_argument(
        '--seed',
        type=int,
        default=42,
        help='随机数种子 (默认: 42)',
    )
    parser.add_argument(
        '--sync-offset',
        type=int,
        default=0,
        help='同步偏移符号数 (默认: 0)',
    )
    parser.add_argument(
        '--frame-length',
        type=int,
        default=256,
        help='每帧载荷比特数 (默认: 256)',
    )
    parser.add_argument(
        '--no-plot',
        action='store_false',
        dest='plot',
        help='不生成图表',
    )
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='详细输出',
    )

    return parser.parse_args(argv)


def main(argv=None):
    """主入口函数。"""
    args = parse_args(argv)

    # 配置
    config = WirelessConfig()
    config.frame_payload_bits = args.frame_length
    config.default_snr_db = args.snr
    config.default_seed = args.seed
    config.sync_offset = args.sync_offset

    input_path = args.input
    output_dir = args.output_dir

    if not Path(input_path).exists():
        print(f"错误: 输入文件 '{input_path}' 不存在")
        sys.exit(1)

    if args.verbose:
        print(f"=== 无线通信基带仿真系统 ===")
        print(f"输入文件: {input_path}")
        print(f"输出目录: {output_dir}")
        print(f"SNR: {args.snr} dB")
        print(f"Seed: {args.seed}")
        print(f"同步偏移: {args.sync_offset} 符号")
        print(f"帧载荷: {args.frame_length} bits")
        print()

    # 运行 Pipeline
    pipeline = WirelessPipeline(config)

    if args.verbose:
        print("正在运行仿真...")

    metrics = pipeline.run(
        input_path=input_path,
        output_dir=output_dir,
        snr_db=args.snr,
        seed=args.seed,
        sync_offset=args.sync_offset,
    )

    # 输出结果
    print()
    print("=== 仿真结果 ===")
    if metrics.get('sync_failed'):
        print("⚠ 帧同步失败！无法恢复数据。")
    else:
        print(f"BER (误比特率):     {metrics['ber']:.6f}")
        print(f"FER (误帧率):       {metrics['fer']:.6f}")
        print(f"文本恢复率:         {metrics['text_recovery_rate']:.4f}")
        print(f"总比特数:           {metrics['total_bits']}")
        print(f"比特错误数:         {metrics['bit_errors']}")
        print(f"总帧数:             {metrics['total_frames']}")
        print(f"帧错误数:           {metrics['frame_errors']}")
    print(f"SNR:                {metrics['snr_db']:.1f} dB")
    print()
    print(f"接收文件: {Path(output_dir) / 'received.txt'}")
    print(f"指标文件: {Path(output_dir) / 'metrics.json'}")

    # 生成图表
    if args.plot and not metrics.get('sync_failed'):
        if args.verbose:
            print("\n正在生成图表...")

        figs_dir = Path(output_dir) / 'figures'
        figs_dir.mkdir(parents=True, exist_ok=True)

        # 星座图（使用接收符号）
        try:
            from src.qpsk import qpsk_modulate
            from src.awgn import awgn_channel
            # 生成测试用的星座图
            test_bits = np.random.RandomState(args.seed).randint(
                0, 2, size=2000, dtype=np.uint8
            )
            test_sym = qpsk_modulate(test_bits)
            rx_sym = awgn_channel(test_sym, snr_db=args.snr, seed=args.seed)
            plot_constellation(
                rx_sym,
                output_path=str(figs_dir / 'constellation_rx.png'),
                title=f'Received Constellation (SNR = {args.snr} dB)',
            )
            if args.verbose:
                print(f"  星座图: {figs_dir / 'constellation_rx.png'}")
        except Exception as e:
            if args.verbose:
                print(f"  星座图生成失败: {e}")

        # 同步相关图
        try:
            sync_symbols = pipeline.synchronizer.sync_symbols
            # 重新生成含同步字的符号用于绘制相关图
            from src.qpsk import qpsk_modulate
            from src.awgn import awgn_channel
            test_payload = np.random.RandomState(args.seed).randint(
                0, 2, size=args.frame_length, dtype=np.uint8
            )
            test_frame = np.concatenate([config.sync_word, np.zeros(16, dtype=np.uint8), test_payload])
            test_sym2 = qpsk_modulate(test_frame)
            rx_sym2 = awgn_channel(test_sym2, snr_db=args.snr, seed=args.seed + 1)
            corr = pipeline.synchronizer.compute_correlation(rx_sym2)
            peaks = pipeline.synchronizer.find_frame_starts(rx_sym2)
            if len(corr) > 0:
                plot_sync_correlation(
                    corr, peaks,
                    output_path=str(figs_dir / 'sync_correlation.png'),
                )
                if args.verbose:
                    print(f"  同步相关图: {figs_dir / 'sync_correlation.png'}")
        except Exception as e:
            if args.verbose:
                print(f"  同步相关图生成失败: {e}")

    return 0


if __name__ == '__main__':
    sys.exit(main())
