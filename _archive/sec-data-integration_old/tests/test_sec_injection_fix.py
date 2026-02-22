import os
import sys
import unittest
from unittest.mock import patch

# Add parent dir to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from sec_data_extractor import get_filings


class TestSecInjection(unittest.TestCase):
    def test_malicious_date_format(self):
        # Passing a SQL injection attempt as date
        malicious_date = "20240101; DROP TABLE students;"

        with self.assertRaises(ValueError):
            get_filings("12345", as_of_date=malicious_date)

    @patch('sec_data_extractor.run_query_csv')
    def test_valid_date_format_hyphen(self, mock_run):
        # Passing YYYY-MM-DD
        mock_run.return_value = "adsh,form,period,fy,fp,countryba,filed\n"
        try:
            get_filings("12345", as_of_date="2024-01-01")
        except ValueError:
            self.fail("get_filings raised ValueError unexpectedly for YYYY-MM-DD!")

    @patch('sec_data_extractor.run_query_csv')
    def test_valid_date_format_compact(self, mock_run):
        # Passing YYYYMMDD (Backward Compatibility)
        mock_run.return_value = "adsh,form,period,fy,fp,countryba,filed\n"
        try:
            get_filings("12345", as_of_date="20240101")
        except ValueError:
            self.fail("get_filings raised ValueError unexpectedly for YYYYMMDD!")

if __name__ == '__main__':
    unittest.main()
