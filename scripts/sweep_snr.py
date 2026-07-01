"""SNR 扫描脚本 — 生成 BER vs SNR 曲线数据。

用法:
    python scripts/sweep_snr.py --input Test.txt --output-dir output/

输出:
    output/ber_vs_snr.json — 各 SNR 点的 BER 数据
    output/figures/ber_vs_snr.png — BER 曲线图
"""

import argparse
import json
import sys
from pathlib import Path

import numpy as np

# 添加父目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config import WirelessConfig
from src.pipeline import WirelessPipeline
from src.metrics import plot_ber_curve


def main():
    parser = argparse.ArgumentParser(description='SNR 扫描生成 BER 曲线')
    parser.add_argument('--input', '-i', default='Test.txt', help='输入文件')
    parser.add_argument('--output-dir', '-o', default='output', help='输出目录')
    parser.add_argument('--snr-start', type=float, default=-2.0, help='起始 SNR (dB)')
    parser.add_argument('--snr-end', type=float, default=12.0, help='结束 SNR (dB)')
    parser.add_argument('--snr-step', type=float, default=1.0, help='SNR 步长 (dB)')
    parser.add_argument('--seed', type=int, default=42, help='随机数种子')
    parser.add_argument('--trials', type=int, default=1, help='每个 SNR 点的试验次数')
    args = parser.parse_args()

    config = WirelessConfig()
    pipeline = WirelessPipeline(config)

    snr_values = np.arange(args.snr_start, args.snr_end + args.snr_step / 2,
                           args.snr_step)
    ber_values = []
    fer_values = []

    print(f"=== SNR 扫描 ===")
    print(f"SNR 范围: {args.snr_start} ~ {args.snr_end} dB, 步长: {args.snr_step} dB")
    print(f"输入文件: {args.input}")
    print()

    for snr in snr_values:
        snr = round(snr, 2)
        bers = []
        fers = []

        for trial in range(args.trials):
            trial_dir = Path(args.output_dir) / f'sweep_snr{snr}_trial{trial}'
            trial_dir.mkdir(parents=True, exist_ok=True)

            metrics = pipeline.run(
                input_path=args.input,
                output_dir=str(trial_dir),
                snr_db=snr,
                seed=args.seed + trial,
            )
            bers.append(metrics['ber'])
            fers.append(metrics['fer'])

        avg_ber = np.mean(bers)
        avg_fer = np.mean(fers)
        ber_values.append(avg_ber)
        fer_values.append(avg_fer)

        print(f"SNR = {snr:5.1f} dB  |  BER = {avg_ber:.6f}  |  FER = {avg_fer:.6f}")

    # 保存数据
    data = {
        'snr_db': [float(s) for s in snr_values],
        'ber': [float(b) for b in ber_values],
        'fer': [float(f) for f in fer_values],
    }
    data_path = Path(args.output_dir) / 'ber_vs_snr.json'
    data_path.parent.mkdir(parents=True, exist_ok=True)
    with open(data_path, 'w') as f:
        json.dump(data, f, indent=2)

    # 绘制 BER 曲线
    figs_dir = Path(args.output_dir) / 'figures'
    figs_dir.mkdir(parents=True, exist_ok=True)
    plot_ber_curve(
        snr_values.tolist(), ber_values,
        output_path=str(figs_dir / 'ber_vs_snr.png'),
    )

    print(f"\n数据已保存: {data_path}")
    print(f"图表已保存: {figs_dir / 'ber_vs_snr.png'}")


if __name__ == '__main__':
    main()
