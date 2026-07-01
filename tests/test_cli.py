"""CLI 接口测试。"""
import pytest
import sys
from pathlib import Path


class TestCLI:
    """CLI 入口测试。"""

    def test_help(self):
        """测试 --help 不报错。"""
        from src.cli import main
        try:
            main(['--help'])
        except SystemExit:
            pass  # argparse 会调用 sys.exit

    def test_default_args_with_test_file(self, test_text_file, tmp_output_dir):
        """测试默认参数运行。"""
        from src.cli import main
        exit_code = main([
            '--input', test_text_file,
            '--output-dir', tmp_output_dir,
            '--snr', '100',
            '--no-plot',
        ])
        assert exit_code == 0
        assert Path(tmp_output_dir, 'received.txt').exists()
        assert Path(tmp_output_dir, 'metrics.json').exists()

    def test_custom_args(self, test_text_file, tmp_output_dir):
        """测试自定义参数。"""
        from src.cli import main
        exit_code = main([
            '--input', test_text_file,
            '--output-dir', tmp_output_dir,
            '--snr', '15.0',
            '--seed', '123',
            '--sync-offset', '5',
            '--frame-length', '128',
            '--no-plot',
        ])
        assert exit_code == 0

    def test_missing_input_file(self, tmp_output_dir):
        """测试输入文件不存在时报错。"""
        from src.cli import main
        with pytest.raises(SystemExit) as exc_info:
            main([
                '--input', 'nonexistent_file_xyz.txt',
                '--output-dir', tmp_output_dir,
            ])
        assert exc_info.value.code == 1

    def test_verbose_mode(self, test_text_file, tmp_output_dir):
        """测试 verbose 模式不报错。"""
        from src.cli import main
        exit_code = main([
            '--input', test_text_file,
            '--output-dir', tmp_output_dir,
            '--snr', '100',
            '--no-plot',
            '--verbose',
        ])
        assert exit_code == 0

    def test_output_metrics_content(self, test_text_file, tmp_output_dir):
        """测试 metrics.json 包含所有必需字段。"""
        import json
        from src.cli import main

        main([
            '--input', test_text_file,
            '--output-dir', tmp_output_dir,
            '--snr', '100',
            '--no-plot',
        ])

        metrics_path = Path(tmp_output_dir) / 'metrics.json'
        with open(metrics_path, encoding='utf-8') as f:
            metrics = json.load(f)

        required_fields = ['ber', 'fer', 'text_recovery_rate', 'total_bits',
                           'bit_errors', 'snr_db', 'seed']
        for field in required_fields:
            assert field in metrics, f"Missing field: {field}"
