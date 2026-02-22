import io
import sys
import unittest
from unittest.mock import MagicMock, patch

from valuation import parity_verification


class TestParityVerification(unittest.TestCase):

    def test_argument_parsing_success(self):
        """Test that valid arguments are parsed correctly."""
        test_args = ['parity_verification.py', 'AAPL', '320193', '2024-01-01']
        with patch.object(sys, 'argv', test_args):
            args = parity_verification.parse_arguments()
            self.assertEqual(args.ticker, 'AAPL')
            self.assertEqual(args.cik, '320193')
            self.assertEqual(args.date, '2024-01-01')

    @patch('subprocess.run')
    def test_run_sec_extractor_success(self, mock_run):
        """Test successful execution of SEC extractor."""
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = '{"test": "data"}'

        result = parity_verification.get_sec_data("320193", "2024-01-01")
        self.assertEqual(result, {"test": "data"})
        mock_run.assert_called_once()

    @patch('subprocess.run')
    def test_run_yf_extractor_success(self, mock_run):
        """Test successful execution of YF extractor."""
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = '{"test": "data"}'

        result = parity_verification.get_yf_data("AAPL")
        self.assertEqual(result, {"test": "data"})
        mock_run.assert_called_once()

    @patch('subprocess.run')
    def test_extractor_failure_nonzero_exit(self, mock_run):
        """Test handling of non-zero exit code."""
        mock_run.return_value.returncode = 1
        mock_run.return_value.stderr = "Error message"

        with self.assertRaises(RuntimeError) as cm:
            parity_verification.get_sec_data("320193", "2024-01-01")
        self.assertIn("SEC extractor failed", str(cm.exception))

    @patch('subprocess.run')
    def test_get_yf_data_failure(self, mock_run):
        """Test failure in YF extractor wrapper."""
        mock_run.side_effect = RuntimeError("Process failed")
        with self.assertRaises(RuntimeError) as cm:
             parity_verification.get_yf_data("AAPL")
        self.assertIn("YF extractor failed", str(cm.exception))

    @patch('subprocess.run')
    def test_get_sec_data_failure(self, mock_run):
        """Test failure in SEC extractor wrapper."""
        mock_run.side_effect = RuntimeError("Process failed")
        with self.assertRaises(RuntimeError) as cm:
             parity_verification.get_sec_data("123", "2020-01-01")
        self.assertIn("SEC extractor failed", str(cm.exception))

    @patch('subprocess.run')
    def test_extractor_failure_invalid_json(self, mock_run):
        """Test handling of invalid JSON output."""
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = "Not JSON"

        with self.assertRaises(ValueError) as cm:
            parity_verification.get_yf_data("AAPL")
        self.assertIn("Invalid JSON", str(cm.exception))

    def test_compare_datasets_exact_match(self):
        """Test comparison when datasets match exactly."""
        data = {
            "revenues_base": 100.0,
            "ebit_reported_base": 50.0,
            "rnd_expense": 10.0,
            "book_equity": 200.0,
            "book_debt": 100.0,
            "cash": 20.0,
            "minority_interest": 5.0,
            "operating_leases_liability": 10.0,
            "cross_holdings": 0.0,
            "shares_outstanding": 1000.0,
            "effective_tax_rate": 0.21,
            "marginal_tax_rate": 0.25
        }
        # Patch keys to match the test data keys
        with patch('valuation.parity_verification.COMPARISON_KEYS', list(data.keys())):
            passed, mismatches = parity_verification.compare_datasets(data, data)
        self.assertTrue(passed)
        self.assertEqual(len(mismatches), 0)

    def test_compare_datasets_mismatch(self):
        """Test comparison with value mismatches."""
        sec_data = {"revenues_base": 100.0}
        yf_data = {"revenues_base": 101.0}

        with patch('valuation.parity_verification.COMPARISON_KEYS', ["revenues_base"]):
            passed, mismatches = parity_verification.compare_datasets(sec_data, yf_data)
        self.assertFalse(passed)
        self.assertEqual(len(mismatches), 1)
        self.assertEqual(mismatches[0]['key'], 'revenues_base')

    def test_compare_datasets_missing_key(self):
        """Test comparison when a key is missing in one dataset."""
        sec_data = {"revenues_base": 100.0}
        yf_data = {}

        with patch('valuation.parity_verification.COMPARISON_KEYS', ["revenues_base"]):
            passed, mismatches = parity_verification.compare_datasets(sec_data, yf_data)
        self.assertFalse(passed)
        self.assertEqual(len(mismatches), 1)
        self.assertIn('missing in YF', mismatches[0]['status'])

    def test_compare_datasets_missing_key_in_sec(self):
        """Test comparison when a key is missing in SEC dataset."""
        sec_data = {}
        yf_data = {"revenues_base": 100.0}

        with patch('valuation.parity_verification.COMPARISON_KEYS', ["revenues_base"]):
            passed, mismatches = parity_verification.compare_datasets(sec_data, yf_data)
        self.assertFalse(passed)
        self.assertEqual(len(mismatches), 1)
        self.assertIn('missing in SEC', mismatches[0]['status'])

    def test_compare_datasets_tolerance(self):
        """Test comparison respects floating point tolerance."""
        sec_data = {"revenues_base": 100.0000001}
        yf_data = {"revenues_base": 100.0000002}

        with patch('valuation.parity_verification.COMPARISON_KEYS', ["revenues_base"]):
            # Should match if close enough (default tolerance usually small)
            passed, mismatches = parity_verification.compare_datasets(sec_data, yf_data)
            self.assertTrue(passed)

            # Large difference fails
            yf_data_diff = {"revenues_base": 100.1}
            passed, mismatches = parity_verification.compare_datasets(sec_data, yf_data_diff)
            self.assertFalse(passed)

    def test_compare_datasets_both_missing(self):
        """Test comparison when key is missing in both datasets."""
        sec_data = {"revenues_base": None}
        yf_data = {"revenues_base": None}
        # Comparison logic should skip if both are missing
        with patch('valuation.parity_verification.COMPARISON_KEYS', ["revenues_base"]):
            passed, mismatches = parity_verification.compare_datasets(sec_data, yf_data)
        self.assertTrue(passed)
        self.assertEqual(len(mismatches), 0)

    def test_compare_datasets_type_mismatch(self):
        """Test comparison with non-numeric values."""
        sec_data = {"key": "value1"}
        yf_data = {"key": "value2"}

        with patch('valuation.parity_verification.COMPARISON_KEYS', ["key"]):
             passed, mismatches = parity_verification.compare_datasets(sec_data, yf_data)
        self.assertFalse(passed)
        self.assertEqual(mismatches[0]['status'], "mismatch (type)")

    def test_compare_datasets_type_match_non_numeric(self):
        """Test comparison with matching non-numeric values."""
        sec_data = {"key": "same"}
        yf_data = {"key": "same"}

        with patch('valuation.parity_verification.COMPARISON_KEYS', ["key"]):
             passed, mismatches = parity_verification.compare_datasets(sec_data, yf_data)
        self.assertTrue(passed)

    def test_setup_logging(self):
        """Test logging setup."""
        with patch('logging.basicConfig') as mock_logging:
            parity_verification.setup_logging()
            mock_logging.assert_called_once()

    @patch('subprocess.run')
    def test_run_extractor_generic_exception(self, mock_run):
        """Test handling of generic exceptions in extractor runner."""
        mock_run.side_effect = Exception("Unexpected error")
        with self.assertRaises(RuntimeError) as cm:
            parity_verification.run_extractor(["cmd"])
        self.assertIn("Failed to run extractor", str(cm.exception))

    @patch('valuation.parity_verification.setup_logging')
    @patch('valuation.parity_verification.get_sec_data')
    @patch('valuation.parity_verification.get_yf_data')
    @patch('sys.exit')
    @patch('valuation.parity_verification.parse_arguments')
    def test_main_reporting_pass(self, mock_args, mock_exit, mock_yf, mock_sec, mock_setup_logging):
        """Test main function reporting for a passing case."""
        mock_args.return_value = MagicMock(ticker="AAPL", cik="123", date="2020-01-01")

        # Mock matching data
        data = {"revenues_base": 100.0}
        mock_sec.return_value = data
        mock_yf.return_value = data

        with patch('valuation.parity_verification.COMPARISON_KEYS', ["revenues_base"]):
            # Capture stdout
            with patch('sys.stdout', new_callable=io.StringIO) as mock_stdout:
                # Use assertLogs to verify logging as well
                with self.assertLogs(level='INFO') as log:
                    parity_verification.main()

        output = mock_stdout.getvalue()
        self.assertIn("PASS", output)
        self.assertNotIn("FAIL", output)
        mock_exit.assert_called_with(0)
        self.assertTrue(any("Starting parity verification" in m for m in log.output))

    @patch('valuation.parity_verification.get_sec_data')
    @patch('valuation.parity_verification.get_yf_data')
    @patch('sys.exit')
    @patch('valuation.parity_verification.parse_arguments')
    def test_main_reporting_fail(self, mock_args, mock_exit, mock_yf, mock_sec):
        """Test main function reporting for a failing case."""
        mock_args.return_value = MagicMock(ticker="AAPL", cik="123", date="2020-01-01")

        # Mock mismatching data
        mock_sec.return_value = {"revenues_base": 100.0}
        mock_yf.return_value = {"revenues_base": 200.0}

        with patch('valuation.parity_verification.COMPARISON_KEYS', ["revenues_base"]):
             with patch('sys.stdout', new_callable=io.StringIO) as mock_stdout:
                parity_verification.main()

        output = mock_stdout.getvalue()
        self.assertIn("FAIL", output)
        self.assertIn("revenues_base", output)
        self.assertIn("100.0", output)
        self.assertIn("200.0", output)
        mock_exit.assert_called_with(1)

    @patch('valuation.parity_verification.get_sec_data')
    @patch('sys.exit')
    @patch('valuation.parity_verification.parse_arguments')
    @patch('valuation.parity_verification.setup_logging')
    def test_main_exception(self, mock_setup, mock_args, mock_exit, mock_sec):
        """Test main function exception handling."""
        mock_args.return_value = MagicMock(ticker="AAPL", cik="123", date="2020-01-01")
        mock_sec.side_effect = RuntimeError("Critical Error")

        # We need to capture the logs to verify the error logging
        with self.assertLogs(level='ERROR') as log:
            parity_verification.main()

        self.assertTrue(any("Verification process failed: Critical Error" in m for m in log.output))
        mock_exit.assert_called_with(2)
