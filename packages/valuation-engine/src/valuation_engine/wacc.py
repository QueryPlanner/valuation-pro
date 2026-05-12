import os

import numpy as np
import pandas as pd

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")


def get_synthetic_spread(interest_coverage_ratio, is_large_firm=True):
    """
    Returns the default spread given an interest coverage ratio.
    """
    if is_large_firm:
        if interest_coverage_ratio > 8.5:
            return 0.0040
        if interest_coverage_ratio > 6.5:
            return 0.0055
        if interest_coverage_ratio > 5.5:
            return 0.0070
        if interest_coverage_ratio > 4.25:
            return 0.0078
        if interest_coverage_ratio > 3.0:
            return 0.0089
        if interest_coverage_ratio > 2.5:
            return 0.0111
        if interest_coverage_ratio > 2.25:
            return 0.0138
        if interest_coverage_ratio > 2.0:
            return 0.0184
        if interest_coverage_ratio > 1.75:
            return 0.0275
        if interest_coverage_ratio > 1.5:
            return 0.0321
        if interest_coverage_ratio > 1.25:
            return 0.0509
        if interest_coverage_ratio > 0.8:
            return 0.0885
        if interest_coverage_ratio > 0.65:
            return 0.1261
        if interest_coverage_ratio > 0.2:
            return 0.1600
        return 0.1900
    else:
        if interest_coverage_ratio > 12.5:
            return 0.0040
        if interest_coverage_ratio > 9.5:
            return 0.0055
        if interest_coverage_ratio > 7.5:
            return 0.0070
        if interest_coverage_ratio > 6.0:
            return 0.0078
        if interest_coverage_ratio > 4.5:
            return 0.0089
        if interest_coverage_ratio > 4.0:
            return 0.0111
        if interest_coverage_ratio > 3.5:
            return 0.0138
        if interest_coverage_ratio > 3.0:
            return 0.0184
        if interest_coverage_ratio > 2.5:
            return 0.0275
        if interest_coverage_ratio > 2.0:
            return 0.0321
        if interest_coverage_ratio > 1.5:
            return 0.0509
        if interest_coverage_ratio > 1.25:
            return 0.0885
        if interest_coverage_ratio > 0.8:
            return 0.1261
        if interest_coverage_ratio > 0.5:
            return 0.1600
        return 0.1900


def load_industry_betas():
    # Attempt to load US Industry averages, fallback to Global if needed
    path = os.path.join(DATA_DIR, "Industry_Averages(US).csv")
    if not os.path.exists(path):
        path = os.path.join(DATA_DIR, "Industry_Averages_(Global).csv")
    if not os.path.exists(path):
        return None
    df = pd.read_csv(path)
    # Convert to numeric, coerce errors to NaN
    df["Unlevered Beta"] = pd.to_numeric(df["Unlevered Beta"], errors="coerce").fillna(1.0)
    # create dictionary mapping industry name to unlevered beta
    return pd.Series(df["Unlevered Beta"].values, index=df["Industry Name"]).to_dict()


def load_country_erps():
    path = os.path.join(DATA_DIR, "Country_equity_risk_premiums.csv")
    if not os.path.exists(path):
        return None, 0.0411

    # Read the first row to get Mature Market ERP
    df_head = pd.read_csv(path, nrows=1, header=None)
    try:
        mature_market_erp = float(df_head.iloc[0, 1])
    except (ValueError, TypeError):
        mature_market_erp = 0.0411

    df = pd.read_csv(path, skiprows=3)
    df["Equity Risk Premium"] = pd.to_numeric(df["Equity Risk Premium"], errors="coerce")
    return pd.Series(df["Equity Risk Premium"].values, index=df["Country"]).to_dict(), mature_market_erp


def calculate_bottom_up_wacc(
    revenues: float,
    operating_income: float,
    interest_expense: float,
    book_value_of_debt: float,
    market_value_of_equity: float,
    effective_tax_rate: float,
    riskfree_rate: float,
    revenue_by_business: dict = None,
    revenue_by_region: dict = None,
    debt_rating: str = "N/A",
    average_maturity_of_debt_years: float = 3.0,
):
    """
    Calculates the bottom-up WACC given financial inputs and lookup tables.
    """
    if not revenue_by_business:
        revenue_by_business = {}
    if not revenue_by_region:
        revenue_by_region = {}

    # 1. Cost of Debt
    is_large_firm = revenues > 500e6  # Assume $500M threshold in absolute units

    default_spread = 0.0
    if debt_rating != "N/A":
        # we could look up rating, but since rating spread isn't explicitly requested as a mapping
        # outside synthetic, let's use synthetic rating directly. In real scenario, use actual rating spread.
        pass

    if interest_expense > 0:
        interest_coverage_ratio = operating_income / interest_expense
    else:
        interest_coverage_ratio = 100000

    default_spread = get_synthetic_spread(interest_coverage_ratio, is_large_firm=is_large_firm)

    kd_pre = riskfree_rate + default_spread
    kd_after_tax = kd_pre * (1 - effective_tax_rate)

    # 2. Market Value of Debt
    # D = PV of interest + PV of book value of debt
    if average_maturity_of_debt_years == 0 or np.isnan(average_maturity_of_debt_years):
        average_maturity_of_debt_years = 3.0

    if kd_pre > 0:
        pv_interest = interest_expense * ((1 - (1 + kd_pre) ** -average_maturity_of_debt_years) / kd_pre)
        pv_principal = book_value_of_debt / ((1 + kd_pre) ** average_maturity_of_debt_years)
        market_value_of_debt = pv_interest + pv_principal
    else:
        market_value_of_debt = book_value_of_debt

    # Cap D to non-negative
    market_value_of_debt = max(market_value_of_debt, 0)

    # 3. Cost of Equity (CAPM)
    industry_betas = load_industry_betas()
    if industry_betas and sum(revenue_by_business.values()) > 0:
        total_business_rev = sum(revenue_by_business.values())
        weighted_unlevered_beta = sum(
            industry_betas.get(biz, 1.0) * (rev / total_business_rev) for biz, rev in revenue_by_business.items()
        )
    else:
        weighted_unlevered_beta = 1.0  # fallback

    # Levered beta
    market_value_of_equity = max(market_value_of_equity, 1)  # prevent div/0
    levered_beta = weighted_unlevered_beta * (
        1 + (1 - effective_tax_rate) * (market_value_of_debt / market_value_of_equity)
    )

    # ERP
    country_erps, mature_market_erp = load_country_erps()
    if country_erps and sum(revenue_by_region.values()) > 0:
        total_region_rev = sum(revenue_by_region.values())
        # Provide fallback mapping from region to some proxy countries if exact mapping fails
        # e.g., "North America" -> "United States", etc.
        region_proxy = {
            "North America": "United States",
            "Western Europe": "Germany",
            "Asia": "China",
            "Eastern Europe": "Poland",
            "Central and South America": "Brazil",
            "Africa": "South Africa",
            "Middle East": "United Arab Emirates",
            "Australia & New Zealand": "Australia",
        }

        weighted_erp = 0.0
        for region, rev in revenue_by_region.items():
            country = region_proxy.get(region, region)
            # if we can't find country, fallback to mature market erp + some premium, or just mature market erp
            erp = country_erps.get(country, mature_market_erp)
            if pd.isna(erp) or erp > 0.15:  # Cap unreasonable ERPs like the 'Global' sum row
                erp = mature_market_erp
            weighted_erp += erp * (rev / total_region_rev)
    else:
        weighted_erp = mature_market_erp

    ke = riskfree_rate + levered_beta * weighted_erp

    # 4. Final WACC
    total_capital = market_value_of_equity + market_value_of_debt
    if total_capital == 0:
        wacc = ke
    else:
        wacc = (market_value_of_equity / total_capital) * ke + (market_value_of_debt / total_capital) * kd_after_tax

    return {
        "wacc": wacc,
        "cost_of_equity": ke,
        "cost_of_debt_after_tax": kd_after_tax,
        "pre_tax_cost_of_debt": kd_pre,
        "market_value_of_debt": market_value_of_debt,
        "market_value_of_equity": market_value_of_equity,
        "unlevered_beta": weighted_unlevered_beta,
        "levered_beta": levered_beta,
        "weighted_erp": weighted_erp,
        "default_spread": default_spread,
    }
