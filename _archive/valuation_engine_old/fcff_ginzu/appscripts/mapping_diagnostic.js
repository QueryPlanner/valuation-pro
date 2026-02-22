/**
 * MAPPING DIAGNOSTIC
 * 
 * INSTRUCTIONS:
 * 1. Open your Google Sheet.
 * 2. Go to Extensions > Apps Script.
 * 3. Create a new script file and paste this code.
 * 4. Run the 'diagnoseMappings' function.
 * 5. Copy the Markdown table from the Execution Log (Ctrl+Enter) and paste it into the chat. 
 * 
 * This allows us to align the Python Engine mappings with your specific Google Sheet version.
 */
function diagnoseMappings() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const sheet = ss.getSheetByName("Input sheet");
  
  if (!sheet) {
    console.log("Error: Sheet named 'Input sheet' not found. Please check your tab names.");
    return;
  }
  
  // Read first 75 rows to capture all potential inputs
  const range = sheet.getRange("A1:B75"); 
  const values = range.getValues();
  
  let report = "### CELL MAPPING DIAGNOSTIC\n\n| Cell | Label | Current Value |\n| :--- | :--- | :--- |\n";
  for (let i = 0; i < values.length; i++) {
    const label = values[i][0];
    const val = values[i][1];
    
    // Only include rows that have either a label or a value
    if (label || val) {
      // Format value for readability (round numbers, keep strings)
      let displayVal = val;
      if (typeof val === 'number') {
        displayVal = val.toLocaleString(undefined, {maximumFractionDigits: 4});
      }
      
      report += `| B${i+1} | ${label || "(No Label)"} | ${displayVal} |\n`;
    }
  }
  
  console.log(report);
}
