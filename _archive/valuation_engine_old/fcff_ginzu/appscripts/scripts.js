function exportAllSheetsFormulasAsCSV() {
    var spreadsheet = SpreadsheetApp.getActiveSpreadsheet();
    var sheets = spreadsheet.getSheets(); // Get all sheets
    var folder = DriveApp.getRootFolder(); // Or specify a folder ID
    
    // Optional: Create a timestamped folder for organization
    var timestamp = Utilities.formatDate(new Date(), Session.getScriptTimeZone(), "yyyy-MM-dd_HHmmss");
    var exportFolder = folder.createFolder(spreadsheet.getName() + "_formulas_" + timestamp);
    
    var filesCreated = [];
    
    // Loop through each sheet
    for (var i = 0; i < sheets.length; i++) {
      var sheet = sheets[i];
      var sheetName = sheet.getName();
      
      var range = sheet.getDataRange();
      var formulas = range.getFormulas();
      var values = range.getValues();
      
      // Build CSV data
      var csvData = [];
      for (var row = 0; row < formulas.length; row++) {
        var rowData = [];
        for (var col = 0; col < formulas[row].length; col++) {
          // Use formula if exists, otherwise use value
          var cellContent = formulas[row][col] ? formulas[row][col] : values[row][col];
          cellContent = String(cellContent).replace(/"/g, '""');
          if (cellContent.indexOf(',') !== -1 || cellContent.indexOf('\n') !== -1 || cellContent.indexOf('"') !== -1) {
            cellContent = '"' + cellContent + '"';
          }
          rowData.push(cellContent);
        }
        csvData.push(rowData.join(','));
      }
      
      var csv = csvData.join('\n');
      
      // Create CSV file for this sheet
      var fileName = sheetName + '.csv';
      var file = exportFolder.createFile(fileName, csv, MimeType.CSV);
      filesCreated.push(fileName);
    }
    
    // Show success message
    var ui = SpreadsheetApp.getUi();
    ui.alert('Export Complete!', 
             filesCreated.length + ' CSV files created:\n\n' + 
             filesCreated.join('\n') + 
             '\n\nFolder: ' + exportFolder.getName() + 
             '\n\nCheck your Google Drive.', 
             ui.ButtonSet.OK);
  }
  