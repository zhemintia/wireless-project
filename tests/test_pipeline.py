"""端到端 Pipeline 集成测试。"""
import pytest
import numpy as np
from pathlib import Path


class TestWirelessPipeline:
    """端到端 Pipeline 测试。"""

    def test_e2e_noiseless(self, test_text_file, tmp_output_dir):
        """无噪声端到端：文件 100% 恢复。"""
        from src.pipeline import WirelessPipeline
        pipeline = WirelessPipeline()
        metrics = pipeline.run(
            input_path=test_text_file,
            output_dir=tmp_output_dir,
            snr_db=100.0,  # 极高 SNR = 几乎无噪声
            seed=42,
        )
        assert metrics['ber'] == 0.0, f"Expected BER=0 at SNR=100, got {metrics['ber']}"
        assert metrics['text_recovery_rate'] == 1.0

    def test_e2e_high_snr(self, test_text_file, tmp_output_dir):
        """高 SNR (20dB)：BER 接近 0。"""
        from src.pipeline import WirelessPipeline
        pipeline = WirelessPipeline()
        metrics = pipeline.run(
            input_path=test_text_file,
            output_dir=tmp_output_dir,
            snr_db=20.0,
            seed=42,
        )
        assert metrics['ber'] == 0.0, f"Expected BER=0 at SNR=20, got {metrics['ber']}"
        assert metrics['text_recovery_rate'] == 1.0

    def test_e2e_low_snr(self, test_text_file, tmp_output_dir):
        """低 SNR (0dB)：系统不崩溃，BER > 0。"""
        from src.pipeline import WirelessPipeline
        pipeline = WirelessPipeline()
        metrics = pipeline.run(
            input_path=test_text_file,
            output_dir=tmp_output_dir,
            snr_db=0.0,
            seed=42,
        )
        # 系统应正常完成
        assert 'ber' in metrics
        assert 'fer' in metrics
        assert 0 <= metrics['ber'] <= 1.0

    def test_output_files_exist(self, test_text_file, tmp_output_dir):
        """测试输出文件 received.txt 和 metrics.json 存在。"""
        from src.pipeline import WirelessPipeline
        pipeline = WirelessPipeline()
        pipeline.run(
            input_path=test_text_file,
            output_dir=tmp_output_dir,
            snr_db=100.0,
            seed=42,
        )
        assert Path(tmp_output_dir, 'received.txt').exists()
        assert Path(tmp_output_dir, 'metrics.json').exists()

    def test_seed_reproducibility(self, test_text_file, tmp_output_dir):
        """相同 seed 产生相同结果。"""
        from src.pipeline import WirelessPipeline

        pipeline1 = WirelessPipeline()
        metrics1 = pipeline1.run(
            input_path=test_text_file,
            output_dir=f'{tmp_output_dir}/run1',
            snr_db=10.0,
            seed=42,
        )

        pipeline2 = WirelessPipeline()
        metrics2 = pipeline2.run(
            input_path=test_text_file,
            output_dir=f'{tmp_output_dir}/run2',
            snr_db=10.0,
            seed=42,
        )

        assert metrics1['ber'] == metrics2['ber']
        assert metrics1['bit_errors'] == metrics2['bit_errors']

    def test_different_snr_different_results(self, test_text_file, tmp_output_dir):
        """高 SNR 比低 SNR 的 BER 更低。"""
        from src.pipeline import WirelessPipeline

        pipeline = WirelessPipeline()
        metrics_high = pipeline.run(
            input_path=test_text_file,
            output_dir=f'{tmp_output_dir}/high',
            snr_db=15.0,
            seed=42,
        )
        metrics_low = pipeline.run(
            input_path=test_text_file,
            output_dir=f'{tmp_output_dir}/low',
            snr_db=2.0,
            seed=42,
        )
        assert metrics_high['ber'] <= metrics_low['ber']

    def test_empty_file(self, tmp_output_dir):
        """空文件测试。"""
        import tempfile
        from src.pipeline import WirelessPipeline

        with tempfile.NamedTemporaryFile(
            mode='w', suffix='.txt', delete=False, encoding='utf-8'
        ) as f:
            f.write("")
            tmp = f.name

        try:
            pipeline = WirelessPipeline()
            metrics = pipeline.run(
                input_path=tmp,
                output_dir=tmp_output_dir,
                snr_db=10.0,
                seed=42,
            )
            assert metrics['ber'] == 0.0
            assert metrics['text_recovery_rate'] == 1.0
        finally:
            Path(tmp).unlink(missing_ok=True)

    def test_sync_offset(self, test_text_file, tmp_output_dir):
        """测试 sync_offset > 0 的代码路径不崩溃。"""
        from src.pipeline import WirelessPipeline
        pipeline = WirelessPipeline()
        metrics = pipeline.run(
            input_path=test_text_file,
            output_dir=tmp_output_dir,
            snr_db=100.0,
            seed=42,
            sync_offset=10,
        )
        assert 'ber' in metrics
        assert metrics['snr_db'] == 100.0

    def test_soft_decision_path(self, test_text_file, tmp_output_dir):
        """测试 soft_decision=True 路径正常完成。"""
        from src.pipeline import WirelessPipeline
        pipeline = WirelessPipeline()
        metrics = pipeline.run(
            input_path=test_text_file,
            output_dir=tmp_output_dir,
            snr_db=100.0,
            seed=42,
            soft_decision=True,
        )
        assert metrics['ber'] == 0.0
        assert metrics['text_recovery_rate'] == 1.0

    def test_sync_failed_low_snr(self, test_text_file, tmp_output_dir):
        """测试极低 SNR 下系统不崩溃且有合理输出。"""
        from src.pipeline import WirelessPipeline
        pipeline = WirelessPipeline()
        metrics = pipeline.run(
            input_path=test_text_file,
            output_dir=tmp_output_dir,
            snr_db=-20.0,  # 极低 SNR
            seed=42,
        )
        # 极低 SNR：同步失败或 BER 极高
        assert 'snr_db' in metrics
        if metrics.get('sync_failed'):
            assert metrics['fer'] == 1.0
        else:
            # 即使同步"成功"（噪声误触发），BER 也应接近 0.5
            assert metrics['ber'] >= 0.3, \
                f"At SNR=-20dB, BER should be high, got {metrics['ber']}"
