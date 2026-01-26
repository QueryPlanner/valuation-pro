/**
 * VALUATION ENGINE VERIFIER
 * 
 * INSTRUCTIONS:
 * 1. Open your Google Sheet (Amazon or Coca-Cola version).
 * 2. Go to Extensions > Apps Script.
 * 3. Create a new script file and paste this code.
 * 4. Ensure your tab names are "Input sheet" and "Valuation output".
 * 5. Run the 'runScenarios' function.
 * 6. View the results in the Execution Log (Ctrl+Enter).
 */

const INPUT_SHEET = "Input sheet";
const OUTPUT_SHEET = "Valuation output";

// Mappings based on the 'fcffsimpleginzu.xlsx' layout (Input sheet)
const MAPPINGS = {
  // Base Numbers
  revenues_base: "B11",
  ebit_reported_base: "B12",
  capitalize_rnd: "B16",             // "Yes"/"No"
  capitalize_operating_leases: "B17", // "Yes"/"No"
  
  // Drivers
  rev_growth_y1: "B26",
  rev_cagr_y2_5: "B28",
  margin_target: "B29",
  margin_convergence_year: "B30",
  sales_to_capital_1_5: "B31",
  sales_to_capital_6_10: "B32",
  riskfree_rate_now: "B34",
  wacc_initial: "B35",
  tax_rate_effective: "B23",
  tax_rate_marginal: "B24",
  
  // Advanced Switches & Overrides
  has_employee_options: "B37",        // "Yes"/"No"
  override_stable_roc: "B48",        // "Yes"/"No"
  stable_roc: "B49",
  override_failure_probability: "B51", // "Yes"/"No"
  probability_of_failure: "B52",
  distress_proceeds_percent: "B54",
  override_perpetual_growth: "B67",   // "Yes"/"No"
  perpetual_growth_rate: "B68",
  override_trapped_cash: "B70",       // "Yes"/"No"
  trapped_cash_amount: "B71",
  trapped_cash_foreign_tax_rate: "B72"
};

const OUTPUTS = {
  value_op_assets: "B24", // 'Valuation output' B24
  value_equity: "B31",   // 'Valuation output' B31
  value_per_share: "B33"  // 'Valuation output' B33
};

/**
 * Runs multiple valuation scenarios and logs the results.
 * This allows us to verify the Python engine against Google Sheets "Truth".
 */
function runScenarios() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const inputSheet = ss.getSheetByName(INPUT_SHEET);
  const outputSheet = ss.getSheetByName(OUTPUT_SHEET);
  
  if (!inputSheet || !outputSheet) {
    throw new Error("Sheets not found. Ensure tab names are 'Input sheet' and 'Valuation output'.");
  }

  // Define scenarios matching test_extensive_valuations.py
  const scenarios = [
    { name: "Baseline", updates: {} },
    { name: "High Growth (20% Y1, 15% Y2-5)", updates: { rev_growth_y1: 0.20, rev_cagr_y2_5: 0.15 } },
    { name: "Low Target Margin (10%)", updates: { margin_target: 0.10 } },
    { name: "High WACC (10%)", updates: { wacc_initial: 0.10 } },
    { name: "No R&D Cap", updates: { capitalize_rnd: "No" } },
    { name: "High Sales-to-Cap (2.0)", updates: { sales_to_capital_1_5: 2.0, sales_to_capital_6_10: 2.0 } },
    { name: "Fast Convergence (2y)", updates: { margin_convergence_year: 2 } },
    { name: "10% Failure Prob", updates: { override_failure_probability: "Yes", probability_of_failure: 0.10, distress_proceeds_percent: 0.50 } },
    { name: "High Marginal Tax (35%)", updates: { tax_rate_marginal: 0.35 } },
    { name: "Aggressive Growth/Margin", updates: { rev_growth_y1: 0.25, margin_target: 0.18, wacc_initial: 0.075 } },
    // KO Specific / Overrides
    { name: "Stable ROC 15%", updates: { override_stable_roc: "Yes", stable_roc: 0.15 } },
    { name: "3% Perp Growth", updates: { override_perpetual_growth: "Yes", perpetual_growth_rate: 0.03 } },
    { name: "Trapped Cash", updates: { override_trapped_cash: "Yes", trapped_cash_amount: 5000, trapped_cash_foreign_tax_rate: 0.10 } }
  ];

  const results = [];

  scenarios.forEach(scenario => {
    console.log("Processing Scenario: " + scenario.name);
    
    // 1. Capture original values to restore them later
    const originals = {};
    Object.keys(scenario.updates).forEach(key => {
      const cellRef = MAPPINGS[key];
      originals[key] = inputSheet.getRange(cellRef).getValue();
      // 2. Apply the scenario update
      inputSheet.getRange(cellRef).setValue(scenario.updates[key]);
    });

    // 3. Force calculation and wait
    SpreadsheetApp.flush();
    Utilities.sleep(1000); 

    // 4. Capture result outputs
    const result = { scenario: scenario.name };
    Object.keys(OUTPUTS).forEach(key => {
      result[key] = outputSheet.getRange(OUTPUTS[key]).getValue();
    });
    results.push(result);

    // 5. Restore original values to leave sheet as we found it
    Object.keys(originals).forEach(key => {
      inputSheet.getRange(MAPPINGS[key]).setValue(originals[key]);
    });
  });

  // Format and Print Results
  let markdown = "\n### SCENARIO VERIFICATION RESULTS\n\n";
  markdown += "| Scenario | Value Op Assets | Value Equity | Value/Share |\n";
  markdown += "| :--- | :--- | :--- | :--- |\n";
  
  results.forEach(r => {
    markdown += `| ${r.scenario} | ${Math.round(r.value_op_assets).toLocaleString()} | ${Math.round(r.value_equity).toLocaleString()} | ${r.value_per_share.toFixed(2)} |\n`;
  });

  console.log(markdown);
  SpreadsheetApp.getUi().alert("Verification Complete! Open the Execution Log to copy the results table.");
}
