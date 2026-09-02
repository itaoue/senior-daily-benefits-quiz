/**
 * Senior Daily Benefits - lead webhook for Google Sheets.
 *
 * Setup (one time):
 *   1. Open the Google Sheet that should receive leads.
 *   2. Extensions -> Apps Script. Delete the sample code, paste this file.
 *   3. Change SECRET below to a long random string.
 *   4. Deploy -> New deployment -> Type "Web app"
 *        Execute as: Me
 *        Who has access: Anyone
 *      Authorize when asked, then copy the Web app URL (ends in /exec).
 *   5. In Railway -> Web service -> Variables add
 *        SHEETS_WEBHOOK_URL = that URL
 *        SHEETS_SECRET      = the same SECRET string
 *      and deploy.
 *
 * Each submission on seniordailybenefits.com then appends one row to the
 * sheet named SHEET_NAME (created automatically with a header row).
 */
var SECRET = "CHANGE-ME-TO-A-LONG-RANDOM-STRING";
var SHEET_NAME = "Leads";

function doPost(e) {
  try {
    var body = JSON.parse(e.postData.contents || "{}");
    if (!body.secret || body.secret !== SECRET) {
      return ContentService.createTextOutput(JSON.stringify({ok: false, error: "unauthorized"}))
        .setMimeType(ContentService.MimeType.JSON);
    }
    var columns = body.columns || Object.keys(body.row || {});
    var ss = SpreadsheetApp.getActiveSpreadsheet();
    var sheet = ss.getSheetByName(SHEET_NAME) || ss.insertSheet(SHEET_NAME);
    if (sheet.getLastRow() === 0) {
      sheet.appendRow(columns);
      sheet.getRange(1, 1, 1, columns.length).setFontWeight("bold");
      sheet.setFrozenRows(1);
    }
    var row = columns.map(function (c) {
      var v = body.row[c];
      return (v === null || v === undefined) ? "" : v;
    });
    sheet.appendRow(row);
    return ContentService.createTextOutput(JSON.stringify({ok: true}))
      .setMimeType(ContentService.MimeType.JSON);
  } catch (err) {
    return ContentService.createTextOutput(JSON.stringify({ok: false, error: String(err)}))
      .setMimeType(ContentService.MimeType.JSON);
  }
}

// Optional: open the web app URL in a browser to confirm it is deployed.
function doGet() {
  return ContentService.createTextOutput("Senior Daily Benefits lead webhook is running.");
}
