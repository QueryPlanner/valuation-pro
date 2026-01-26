
import unittest
from unittest.mock import patch, MagicMock
import sys
import os
import io
import csv

# Add the parent directory to sys.path to import sec_data_extractor
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from sec_data_extractor import get_filings, calculate_ltm

class TestSecExtractor(unittest.TestCase):
    
    def test_calculate_ltm_arithmetic(self):
        # Scenario:
        # FY 2023 (10-K): 100
        # Q2 2024 (10-Q): 60 (Current YTD)
        # Q2 2023 (10-Q): 55 (Prior YTD)
        # LTM = 100 + 60 - 55 = 105
        
        tags = ["Revenue"]
        
        # Mock Filing Rows
        latest_10k = {'adsh': 'A', 'period': '20231231', 'form': '10-K', 'fy': '2023', 'fp': 'FY'}
        latest_filing = {'adsh': 'B', 'period': '20240630', 'form': '10-Q', 'fy': '2024', 'fp': 'Q2'}
        
        # Mock Facts
        # facts_10k needs the FY value
        facts_10k = [
            {'tag': 'Revenue', 'value': '100', 'uom': 'USD', 'qtrs': '4', 'ddate': '20231231', 'dimh': '0x00000000'}
        ]
        
        # facts_latest needs Current YTD and Prior YTD
        # Prior YTD date for Q2 (ending 20240630) would be 20230630
        facts_latest = [
            {'tag': 'Revenue', 'value': '60', 'uom': 'USD', 'qtrs': '2', 'ddate': '20240630', 'dimh': '0x00000000'},
            {'tag': 'Revenue', 'value': '55', 'uom': 'USD', 'qtrs': '2', 'ddate': '20230630', 'dimh': '0x00000000'}
        ]
        
        ltm_value = calculate_ltm(tags, latest_10k, latest_filing, facts_10k, facts_latest)
        
        self.assertEqual(ltm_value, 105.0)

    @patch('sec_data_extractor.get_filings')
    @patch('sec_data_extractor.fetch_facts')
    def test_extract_shares_practicable_date(self, mock_fetch, mock_filings):
        # Scenario: Share count is reported as of July 20, 2024 in a June 30, 2024 filing.
        period_end = '20240630'
        practicable_date = '20240720'
        
        mock_filings.return_value = (
            {'adsh': 'A', 'period': '20231231', 'form': '10-K', 'fy': '2023', 'fp': 'FY'},
            {'adsh': 'B', 'period': period_end, 'form': '10-Q', 'fy': '2024', 'fp': 'Q2'},
            'US'
        )
        
        mock_fetch.return_value = [
            # Strict date match fails
            {'tag': 'EntityCommonStockSharesOutstanding', 'value': '1000', 'uom': 'shares', 'qtrs': '0', 'ddate': practicable_date, 'dimh': '0x00000000'}
        ]
        
        from sec_data_extractor import extract_data
        data = extract_data("12345")
        
        # This currently fails because extract_data looks for facts strictly on 20240630
        self.assertEqual(data['shares_outstanding'], 1000.0)

    @patch('sec_data_extractor.get_filings')
    @patch('sec_data_extractor.fetch_facts')
    def test_extract_interest_expense(self, mock_fetch, mock_filings):
        # Mock Filings
        mock_filings.return_value = (
            {'adsh': 'A', 'period': '20231231', 'form': '10-K', 'fy': '2023', 'fp': 'FY'}, # 10K
            {'adsh': 'A', 'period': '20231231', 'form': '10-K', 'fy': '2023', 'fp': 'FY'}, # Latest (same)
            'US'
        )
        
        # Mock Facts
        # InterestExpense = 50
        mock_fetch.return_value = [
            {'tag': 'InterestExpense', 'value': '50', 'uom': 'USD', 'qtrs': '4', 'ddate': '20231231', 'dimh': '0x00000000'}
        ]
        
        from sec_data_extractor import extract_data
        data = extract_data("12345")
        
        self.assertEqual(data['interest_expense'], 50.0)
    
    @patch('sec_data_extractor.run_query_csv')
    def test_get_filings_as_of_date_filtering(self, mock_run_query):
        # Mock data: Three filings, but we want to simulate what DuckDB would return 
        # AFTER filtering by filed <= 20240901.
        # So only the second and third rows should be in the result.
        csv_header = "adsh,form,period,fy,fp,countryba,filed"
        csv_row2 = "0000021344-24-000044,10-Q,20240628,2024,Q2,US,20240725"
        csv_row3 = "0000021344-24-000009,10-K,20231231,2023,FY,US,20240222"
        
        mock_run_query.return_value = "\n".join([csv_header, csv_row2, csv_row3])
        
        cik = "21344"
        as_of_date = "2024-09-01"
        
        latest_10k, latest_filing, country = get_filings(cik, as_of_date=as_of_date)
        
        # Verify SQL contains the date filter
        called_sql = mock_run_query.call_args[0][0]
        self.assertIn("filed <= 20240901", called_sql)
        self.assertIn("CAST(cik AS VARCHAR) = '21344'", called_sql)

    @patch('sec_data_extractor.run_query_csv')
    def test_get_filings_no_date_filter(self, mock_run_query):
        csv_header = "adsh,form,period,fy,fp,countryba,filed"
        csv_row1 = "0000021344-24-000060,10-Q,20240927,2024,Q3,US,20241024"
        mock_run_query.return_value = "\n".join([csv_header, csv_row1])
        
        get_filings("21344")
        
    @patch('sec_data_extractor.run_query_csv')
    def test_get_filings_selection_logic(self, mock_run_query):
        # Multiple 10-Ks and 10-Qs
        csv_header = "adsh,form,period,fy,fp,countryba,filed"
        rows = [
            "001,10-Q,20240630,2024,Q2,US,20240725",
            "002,10-K/A,20231231,2023,FY,US,20240301",
            "003,10-K,20231231,2023,FY,US,20240220",
            "004,10-Q,20230930,2023,Q3,US,20231025"
        ]
        mock_run_query.return_value = "\n".join([csv_header] + rows)
        
        latest_10k, latest_filing, _ = get_filings("21344")
        
        # latest_filing should be 001 (latest period)
        self.assertEqual(latest_filing['adsh'], "001")
    @patch('sec_data_extractor.run_query_csv')
    def test_ko_selection_scenario(self, mock_run_query):
        csv_header = "adsh,form,period,fy,fp,countryba,filed"
        rows = [
            "0000021344-24-000060,10-Q,20240927,2024,Q3,US,20241024",
            "0000021344-24-000044,10-Q,20240628,2024,Q2,US,20240725",
            "0000021344-24-000017,10-Q,20240329,2024,Q1,US,20240425",
            "0000021344-24-000009,10-K,20231231,2023,FY,US,20240222"
        ]
        
        # When filtered by filed <= 20240901, only the last three rows remain
        mock_run_query.return_value = "\n".join([csv_header] + rows[1:])
        
        latest_10k, latest_filing, _ = get_filings("21344", as_of_date="2024-09-01")
        
        self.assertEqual(latest_filing['adsh'], "0000021344-24-000044")
        self.assertEqual(latest_10k['adsh'], "0000021344-24-000009")

if __name__ == "__main__":
    unittest.main()
