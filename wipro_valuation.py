import json
import statistics
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from valuation_engine.inputs_builder import build_ginzu_inputs
from valuation_engine.engine import compute_ginzu
from valuation_engine.wacc import calculate_bottom_up_wacc

# 1. Base data from inputs
data = {
    "revenues_base": 890884000000.0,
    "ebit_reported_base": 184204000000.0,
    "book_equity": 830447000000.0,
    "book_debt": 192035000000.0,
    "cash": 532373000000.0,
    "cross_holdings": 1327000000.0,
    "minority_interest": 2138000000.0,
    "shares_outstanding": 10482438781.0,
    "stock_price": 196.68,
    "effective_tax_rate": 0.2445,
    "marginal_tax_rate": 0.25,
    "risk_free_rate": 0.07,
}

market_value_equity = data["shares_outstanding"] * data["stock_price"]

# 2. Bottom-up WACC Calculation
wacc_outputs = calculate_bottom_up_wacc(
    revenues=data["revenues_base"],
    operating_income=data["ebit_reported_base"],
    interest_expense=9247000000.0,
    book_value_of_debt=data["book_debt"],
    market_value_of_equity=market_value_equity,
    effective_tax_rate=data["effective_tax_rate"],
    riskfree_rate=data["risk_free_rate"],
    revenue_by_business={"Computer Software & Svcs": data["revenues_base"]},
    revenue_by_region={"North America": data["revenues_base"] * 0.60, "Western Europe": data["revenues_base"] * 0.28, "Asia": data["revenues_base"] * 0.12},
    debt_rating="N/A",
    average_maturity_of_debt_years=5.0
)
base_wacc = wacc_outputs["wacc"]

invested_capital = data["book_equity"] + data["book_debt"] - data["cash"]
current_sales_to_cap = data["revenues_base"] / invested_capital if invested_capital > 0 else 1.5
current_margin = data["ebit_reported_base"] / data["revenues_base"]

# Base Growth = (Most_Recent - Last_10K) / Last_10K
last_10k_rev = 897603000000.0
base_growth = (data["revenues_base"] / last_10k_rev) - 1.0

print(f"Base Growth: {base_growth:.2%}")
print(f"Base Margin: {current_margin:.2%}")
print(f"Base WACC: {base_wacc:.2%}")

base_assumptions = {
    "rev_growth_y1": base_growth,
    "rev_cagr_y2_5": base_growth,
    "margin_y1": current_margin,
    "margin_target": current_margin,
    "margin_convergence_year": 5,
    "sales_to_capital_1_5": current_sales_to_cap,
    "sales_to_capital_6_10": current_sales_to_cap,
    "wacc_initial": base_wacc,
}
base_inputs = build_ginzu_inputs(data, base_assumptions)
base_outputs = compute_ginzu(base_inputs)
base_val_per_share = base_outputs.estimated_value_per_share
print(f"Base Case Value Per Share: {base_val_per_share:.2f}")

# 3. Monte Carlo Simulation
num_simulations = 1000
np.random.seed(42)

def get_valuation(growth, margin):
    assumptions = {
        "rev_growth_y1": growth,
        "rev_cagr_y2_5": growth,
        "margin_y1": current_margin,
        "margin_target": margin,
        "margin_convergence_year": 5,
        "sales_to_capital_1_5": current_sales_to_cap,
        "sales_to_capital_6_10": current_sales_to_cap,
        "wacc_initial": base_wacc,
    }
    try:
        inputs = build_ginzu_inputs(data, assumptions)
        return compute_ginzu(inputs).estimated_value_per_share
    except Exception:
        return np.nan

results = {
    "Growth": [],
    "Target Margin": []
}

# Add standard deviation for growth: let's say 2% variation
growth_std = 0.02
growth_samples = np.random.normal(base_growth, growth_std, num_simulations)
for g in growth_samples:
    results["Growth"].append(get_valuation(g, current_margin))

# Add standard deviation for margin: let's say 2% variation
margin_std = 0.02
margin_samples = np.random.normal(current_margin, margin_std, num_simulations)
for m in margin_samples:
    results["Target Margin"].append(get_valuation(base_growth, m))

# Plotting using Plotly Subplots
fig = make_subplots(rows=1, cols=2, subplot_titles=(
    f"Sensitivity to Revenue Growth (Base: {base_growth:.2%})", 
    f"Sensitivity to Target Margin (Base: {current_margin:.2%})"
))

colors = ["#1f77b4", "#ff7f0e"]
variables = list(results.keys())

for i, var in enumerate(variables):
    valid_data = [val for val in results[var] if not np.isnan(val)]
    fig.add_trace(
        go.Histogram(
            x=valid_data,
            name=var,
            marker_color=colors[i],
            opacity=0.75,
            nbinsx=50
        ),
        row=1, col=i+1
    )
    fig.add_vline(x=base_val_per_share, line_dash="dash", line_color="black", 
                  annotation_text="Base Val: {:.2f}".format(base_val_per_share), 
                  annotation_position="top right", row=1, col=i+1)

fig.update_layout(
    title_text="Monte Carlo Sensitivity Analysis (Wipro)",
    showlegend=False,
    height=500,
    width=1000
)

graph_html = fig.to_html(full_html=False, include_plotlyjs='cdn')

# 4. Generate HTML Report
html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <title>Wipro Intrinsic Valuation Report</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 40px; line-height: 1.6; }}
        h1, h2, h3 {{ color: #333; }}
        table {{ border-collapse: collapse; width: 100%; margin-bottom: 20px; font-size: 0.9em; }}
        th, td {{ border: 1px solid #ddd; padding: 6px; text-align: right; }}
        th {{ background-color: #f2f2f2; text-align: center; }}
        .text-left {{ text-align: left; }}
        .story-header {{ background-color: #e6f2ff; font-weight: bold; }}
    </style>
</head>
<body>
    <h1>Wipro Intrinsic Valuation Report</h1>
    
    <h2>1. Valuation as a Picture (Stories to Numbers)</h2>
    
    <table>
        <tr class="story-header">
            <th colspan="2">Base Year and Comparison</th>
            <th colspan="2">Growth Story</th>
            <th colspan="3">Profitability Story</th>
            <th colspan="3">Growth Efficiency Story</th>
            <th colspan="2">Terminal Value</th>
        </tr>
        <tr>
            <td class="text-left">Revenue Growth</td><td>{base_growth:.2%}</td>
            <td class="text-left" colspan="2" rowspan="4" style="vertical-align: top;">
                Assume historical revenue growth trajectory stabilizes and moves towards the risk-free rate over the next 10 years.
            </td>
            <td class="text-left" colspan="3" rowspan="4" style="vertical-align: top;">
                Target margin is maintained at the current operating margin ({current_margin:.2%}) as the firm is mature and faces steady competition.
            </td>
            <td class="text-left" colspan="3" rowspan="4" style="vertical-align: top;">
                Sales to capital ratio maintained at the current {current_sales_to_cap:.2f}x to reflect steady capital efficiency.
            </td>
            <td class="text-left">Growth Rate</td><td>{data['risk_free_rate']:.2%}</td>
        </tr>
        <tr>
            <td class="text-left">Revenue</td><td>INR {data['revenues_base'] / 1e9:,.0f} B</td>
            <td class="text-left">Cost of capital</td><td>{base_outputs.wacc[-1]:.2%}</td>
        </tr>
        <tr>
            <td class="text-left">Operating Margin</td><td>{current_margin:.2%}</td>
            <td class="text-left">Return on capital</td><td>{base_outputs.wacc[-1]:.2%}</td>
        </tr>
        <tr>
            <td class="text-left">Operating Income</td><td>INR {data['ebit_reported_base'] / 1e9:,.0f} B</td>
            <td class="text-left">Reinvestment Rate</td><td>{(data['risk_free_rate'] / base_outputs.wacc[-1]):.2%}</td>
        </tr>
    </table>

    <table>
        <tr>
            <th></th>
            <th>1</th><th>2</th><th>3</th><th>4</th><th>5</th>
            <th>6</th><th>7</th><th>8</th><th>9</th><th>10</th>
            <th>Terminal year</th>
        </tr>
        <tr>
            <td class="text-left"><strong>Revenue Growth</strong></td>
            {"".join([f"<td>{g:.2%}</td>" for g in base_outputs.growth_rates])}
            <td>{data['risk_free_rate']:.2%}</td>
        </tr>
        <tr>
            <td class="text-left"><strong>Revenue (B)</strong></td>
            {"".join([f"<td>{r / 1e9:,.0f}</td>" for r in base_outputs.revenues[1:]])}
            <td>{(base_outputs.revenues[-1] * (1 + data['risk_free_rate'])) / 1e9:,.0f}</td>
        </tr>
        <tr>
            <td class="text-left"><strong>Operating Margin</strong></td>
            {"".join([f"<td>{m:.2%}</td>" for m in base_outputs.margins[1:]])}
            <td>{base_outputs.margins[-1]:.2%}</td>
        </tr>
        <tr>
            <td class="text-left"><strong>Operating Income (B)</strong></td>
            {"".join([f"<td>{e / 1e9:,.0f}</td>" for e in base_outputs.ebit[1:]])}
            <td>{(base_outputs.revenues[-1] * (1 + data['risk_free_rate']) * base_outputs.margins[-1]) / 1e9:,.0f}</td>
        </tr>
        <tr>
            <td class="text-left"><strong>EBIT (1-t) (B)</strong></td>
            {"".join([f"<td>{eat / 1e9:,.0f}</td>" for eat in base_outputs.ebit_after_tax[1:]])}
            <td>{(base_outputs.revenues[-1] * (1 + data['risk_free_rate']) * base_outputs.margins[-1] * (1 - base_outputs.tax_rates[-1])) / 1e9:,.0f}</td>
        </tr>
        <tr>
            <td class="text-left"><strong>Reinvestment (B)</strong></td>
            {"".join([f"<td>{r / 1e9:,.0f}</td>" for r in base_outputs.reinvestment[:-1]])}
            <td>{base_outputs.reinvestment[-1] / 1e9:,.0f}</td>
        </tr>
        <tr>
            <td class="text-left"><strong>FCFF (B)</strong></td>
            {"".join([f"<td>{f / 1e9:,.0f}</td>" for f in base_outputs.fcff[:-1]])}
            <td>{base_outputs.fcff[-1] / 1e9:,.0f}</td>
        </tr>
        <tr><td colspan="12" style="border:none; height: 10px;"></td></tr>
        <tr>
            <td class="text-left"><strong>Cost of Capital</strong></td>
            {"".join([f"<td>{w:.2%}</td>" for w in base_outputs.wacc[:-1]])}
            <td></td>
        </tr>
        <tr>
            <td class="text-left"><strong>Cumulated WACC</strong></td>
            {"".join([f"<td>{df:.4f}</td>" for df in base_outputs.discount_factors])}
            <td></td>
        </tr>
    </table>
    
    <table style="width: 40%; float: left; margin-right: 20px;">
        <tr><td class="text-left">PV (Terminal value)</td><td>INR {base_outputs.pv_terminal_value / 1e9:,.0f} B</td></tr>
        <tr><td class="text-left">PV (CF over next 10 years)</td><td>INR {base_outputs.pv_10y / 1e9:,.0f} B</td></tr>
        <tr><td class="text-left">Probability of failure</td><td>{base_outputs.probability_of_failure:.2%}</td></tr>
        <tr><td class="text-left"><strong>Value of operating assets</strong></td><td><strong>INR {base_outputs.value_of_operating_assets / 1e9:,.0f} B</strong></td></tr>
        <tr><td class="text-left">- Debt</td><td>INR {base_outputs.debt / 1e9:,.0f} B</td></tr>
        <tr><td class="text-left">- Minority interests</td><td>INR {data['minority_interest'] / 1e9:,.0f} B</td></tr>
        <tr><td class="text-left">+ Cash</td><td>INR {base_outputs.cash_adjusted / 1e9:,.0f} B</td></tr>
        <tr><td class="text-left">+ Non-operating assets</td><td>INR {data['cross_holdings'] / 1e9:,.0f} B</td></tr>
        <tr><td class="text-left"><strong>Value of equity</strong></td><td><strong>INR {base_outputs.value_of_equity / 1e9:,.0f} B</strong></td></tr>
        <tr><td class="text-left">- Value of options</td><td>INR {base_outputs.options_value / 1e9:,.0f} B</td></tr>
        <tr><td class="text-left"><strong>Value of equity in common stock</strong></td><td><strong>INR {base_outputs.value_of_equity_common / 1e9:,.0f} B</strong></td></tr>
        <tr><td class="text-left">Number of shares</td><td>{data['shares_outstanding'] / 1e6:,.2f} M</td></tr>
        <tr><td class="text-left"><strong>Estimated value / share</strong></td><td><strong>INR {base_outputs.estimated_value_per_share:.2f}</strong></td></tr>
        <tr><td class="text-left">Price per share</td><td>INR {data['stock_price']:.2f}</td></tr>
        <tr><td class="text-left">% Under or Over Valued</td><td>{((data['stock_price'] / base_outputs.estimated_value_per_share) - 1):.2%}</td></tr>
    </table>

    <table style="width: 55%; float: left;">
        <tr class="story-header"><th class="text-left">Risk Story</th><th class="text-left">Competitive Advantages</th></tr>
        <tr>
            <td class="text-left" style="vertical-align: top; height: 100px;">Cost of capital based on industry average beta and regional risk premiums.</td>
            <td class="text-left" style="vertical-align: top;">Strong IT services presence globally, steady margins but facing growth headwinds.</td>
        </tr>
    </table>
    <div style="clear: both; margin-bottom: 40px;"></div>

    <h2>3. Valuation Diagnostic Report</h2>
    <div style="background-color: #f9f9f9; padding: 20px; border-left: 5px solid #0056b3;">
        <h3>Step 1: Growth Diagnostic</h3>
        <p><strong>Input:</strong> -0.75% for Years 1-10.</p>
        <p><strong>Assessment: Overly Pessimistic.</strong> Extrapolating a single recent year of negative growth (-0.75%) across a 10-year forecast is highly conservative for a mature, established IT services firm. The industry average growth is in the low-to-mid single digits. While Wipro may be facing short-term headwinds, modeling a decade of perpetual shrinkage implies the business is in terminal decline, which contradicts the broader structural tailwinds in global IT spending.</p>

        <h3>Step 2: Revenues Diagnostic</h3>
        <p><strong>Input:</strong> Compounding a -0.75% growth rate over 10 years.</p>
        <p><strong>Assessment: Unrealistic Base.</strong> Because growth is negative, Wipro's forecasted revenues in Year 10 will be lower than they are today. If inflation remains positive, real revenue shrinkage is even more severe. The market typically expects large IT players to at least match inflation over the long run.</p>

        <h3>Step 3: Margins Diagnostic</h3>
        <p><strong>Input:</strong> 20.68% target operating margin (maintaining the base year).</p>
        <p><strong>Assessment: Optimistic/Contradictory.</strong> Wipro's margin is modeled at the very top end of the industry average (15-20%). While historically achievable for Wipro, maintaining a ~21% operating margin <em>while revenues are shrinking for 10 straight years</em> is economically counterintuitive. Usually, declining revenues lead to margin compression due to the loss of operating leverage and fixed overhead costs. The model assumes flawless cost-cutting perfectly aligned with revenue loss.</p>

        <h3>Step 4: Reinvestment Diagnostic (ROC & Capital Efficiency)</h3>
        <p><strong>Input:</strong> ROC at ~19-20%; Sales to Capital at ~1.07 (or 1.50).</p>
        <p><strong>Assessment: Mixed.</strong> A 19-20% Return on Capital indicates strong historical capital efficiency, well above the cost of capital. However, because the modeled growth is negative, the model essentially implies Wipro is shrinking its capital base. Generating a high ROC on a shrinking capital base is mathematically possible (returning cash to shareholders instead of reinvesting), but it is a liquidation scenario rather than a going-concern growth scenario.</p>

        <h3>Step 5: Risk Diagnostic (Cost of Capital)</h3>
        <p><strong>Input:</strong> 11.18% WACC (Initial and Stable).</p>
        <p><strong>Assessment: Reasonable but Conservative.</strong> The 11.18% discount rate sits at the higher end of the standard 9-12% industry range. Given Wipro is a large-cap, established multinational with strong cash flows, an 11.18% WACC slightly penalizes the valuation. Keeping it at 11.18% into perpetuity (stable WACC) also leaves no room for the firm maturing into a lower-risk profile.</p>

        <h3>Step 6: Price vs. Value Diagnostic</h3>
        <p><strong>Input:</strong> Estimated Value (154.03) vs. Price (196.68); Value is ~78.3% of Price.</p>
        <p><strong>Assessment: Model is Pricing a Terminal Decline, the Market is Not.</strong> The model concludes Wipro is roughly 22% overvalued. However, this output is heavily skewed by the draconian growth assumption (-0.75% for a decade). The current market price of ~196 INR is clearly factoring in a return to historical industry growth norms (low-to-mid single digits) and a stabilization of the business. If the growth rate is adjusted to match inflation (e.g., 2-4%) and the margin normalized to a sustainable industry median (~17-18%), the estimated value per share will likely align much more closely with the current stock price.</p>
    </div>

    <h2>4. Computed Cost of Capital (Bottom-Up)</h2>
    <table>
        <tr><th>Metric</th><th>Value</th></tr>
        <tr><td>Cost of Equity (CAPM)</td><td>{wacc_outputs['cost_of_equity']:.2%}</td></tr>
        <tr><td>Pre-tax Cost of Debt</td><td>{wacc_outputs['pre_tax_cost_of_debt']:.2%}</td></tr>
        <tr><td>After-tax Cost of Debt</td><td>{wacc_outputs['cost_of_debt_after_tax']:.2%}</td></tr>
        <tr><td>Unlevered Beta</td><td>{wacc_outputs['unlevered_beta']:.4f}</td></tr>
        <tr><td>Levered Beta</td><td>{wacc_outputs['levered_beta']:.4f}</td></tr>
        <tr><td>Weighted ERP</td><td>{wacc_outputs['weighted_erp']:.2%}</td></tr>
        <tr><td>Default Spread</td><td>{wacc_outputs['default_spread']:.2%}</td></tr>
        <tr><td><strong>Cost of Capital (WACC)</strong></td><td><strong>{base_wacc:.2%}</strong></td></tr>
    </table>

    <h2>5. Primary Inputs</h2>
    <table>
        <tr><th>Input</th><th>Value</th></tr>
        <tr><td>Revenues Base</td><td>INR {data['revenues_base']:,.2f}</td></tr>
        <tr><td>EBIT Reported Base</td><td>INR {data['ebit_reported_base']:,.2f}</td></tr>
        <tr><td>Book Equity</td><td>INR {data['book_equity']:,.2f}</td></tr>
        <tr><td>Book Debt</td><td>INR {data['book_debt']:,.2f}</td></tr>
        <tr><td>Cash</td><td>INR {data['cash']:,.2f}</td></tr>
        <tr><td>Shares Outstanding</td><td>{data['shares_outstanding']:,.0f}</td></tr>
        <tr><td>Effective Tax Rate</td><td>{data['effective_tax_rate']:.2%}</td></tr>
        <tr><td>Risk Free Rate</td><td>{data['risk_free_rate']:.2%}</td></tr>
        <tr><td>Historical Growth Rate</td><td>{base_growth:.2%}</td></tr>
    </table>

    <h2>6. Monte Carlo Simulation Distributions</h2>
    <p>Varying Growth Rates (std: 2%) and Target Operating Margins (std: 2%).</p>
    {graph_html}
    
</body>
</html>
"""

with open("wipro_valuation_report.html", "w", encoding="utf-8") as f:
    f.write(html_content)

print("Report generated: wipro_valuation_report.html")
