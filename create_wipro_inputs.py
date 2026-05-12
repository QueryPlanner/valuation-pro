import json

data = {
  "financial_data": {
    "Revenues": {
      "Most_Recent_12_months": 890884000000.0,
      "Last_10K_before_LTM": 897603000000.0
    },
    "Operating_income_or_EBIT": {
      "Most_Recent_12_months": 150686000000.0,
      "Last_10K_before_LTM": 133730000000.0
    },
    "Interest_expense": {
      "Most_Recent_12_months": 9247000000.0,
      "Last_10K_before_LTM": 8260000000.0
    },
    "Book_value_of_equity": {
      "Most_Recent_12_months": 830447000000.0,
      "Last_10K_before_LTM": 751223000000.0
    },
    "Book_value_of_debt": {
      "Most_Recent_12_months": 192035000000.0,
      "Last_10K_before_LTM": 164649000000.0
    },
    "Cash_and_Marketable_Securities": {
      "Most_Recent_12_months": 532373000000.0,
      "Last_10K_before_LTM": 410012000000.0
    },
    "Cross_holdings_and_other_non_operating_assets": {
      "Most_Recent_12_months": 1327000000.0,
      "Last_10K_before_LTM": 1044000000.0
    },
    "Minority_interests": {
      "Most_Recent_12_months": 2138000000.0,
      "Last_10K_before_LTM": 1340000000.0
    }
  },
  "revenue_splits": {
    "by_region": {
      "Rest of the World": 890884000000.0
    },
    "by_business": {
      "Computer Software & Svcs": 890884000000.0
    }
  },
  "cost_of_capital_inputs": {
    "debt_rating": "N/A",
    "average_maturity_of_debt_years": 5.0
  },
  "employee_options": {
    "total_options_outstanding": 0.0,
    "weighted_average_exercise_price": 0.0,
    "average_maturity_years": 0.0
  },
  "r_and_d_details": {
    "industry_name": "Computer Software & Svcs",
    "amortization_period_years": 3,
    "current_year_expense": 0.0,
    "historical_expenses": {
      "Year_Minus_1": 0.0,
      "Year_Minus_2": 0.0,
      "Year_Minus_3": 0.0
    }
  },
  "single_value_metrics": {
    "Years_since_last_10K": 1.0,
    "Number_of_shares_outstanding": 10482438781,
    "Effective_tax_rate": 0.2445
  },
  "missing_documents_required": []
}

with open("wipro_inputs.json", "w") as f:
    json.dump(data, f, indent=2)
