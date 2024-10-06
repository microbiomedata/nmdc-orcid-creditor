/**
 * This Google Apps Script script accepts HTTP requests from the nmdc-orcid-creditor FastAPI app
 * (with which it shares a secret), retrieves data from a Google Sheets document, and returns
 * that data to the FastAPI app. In that sense, this script is a "proxy" between the FastAPI
 * app and Google Sheets.
 */

// Reference: https://support.orcid.org/hc/en-us/articles/360006897674-Structure-of-the-ORCID-Identifier
const orcidRegex = new RegExp(/^\d{4}-\d{4}-\d{4}-\d{4}$/);

/**
 * Returns the credits associated with the specified ORCID ID,
 * from the Google Sheets document.
 */
function getCreditsByOrcidId(orcidId) {
  const spreadsheet = SpreadsheetApp.openById(CONFIG.SPREADSHEET_ID);
  const sheet = spreadsheet.getSheetByName(CONFIG.SHEET_NAME);

  // Get all the values on the sheet.
  const dataRange = sheet.getDataRange();
  const values = dataRange.getValues();

  // Determine the index of the column containing the ORCID IDs.
  const columnNames = values[0];
  const orcidIdColumnIndex = columnNames.indexOf("column.ORCID_ID");

  // Find the rows that have the specified ORCID ID in that column.
  const credits = values.filter((row) => row[orcidIdColumnIndex] === orcidId);

  // Convert the array of values into an array of objects, so the values are labeled.
  // Example: [{ "col_A": "val_A1", "col_B": "val_B1" }, { "col_A": "val_A7", "col_B": "val_B7" }]
  const labeledCredits = credits.map((cellValues) => {
    let labeledRow = {};
    for (let i = 0; i < columnNames.length; i++) {
      labeledRow[columnNames[i]] = cellValues[i];
    }
    return labeledRow;
  });

  // Return the array of objects.
  return labeledCredits;
}

/**
 * Handle incoming GET requests.
 *
 * Reference: https://developers.google.com/apps-script/guides/web
 */
function doGet(event) {
  let responsePayload = {};

  // Get the request query parameters as an object.
  const queryParams = event.parameter;

  // Abort if either no shared secret was specified or it does not match ours.
  const sharedSecret = queryParams["shared_secret"];
  if (sharedSecret !== CONFIG.SHARED_SECRET) {
    responsePayload = { error: "Forbidden. Incorrect shared_secret." };
    return ContentService.createTextOutput(
      JSON.stringify(responsePayload),
    ).setMimeType(ContentService.MimeType.JSON);
  }

  // Abort if either no ORCID ID was specified or its format is invalid.
  const orcidId = queryParams["orcid_id"];
  if (typeof orcidId !== "string" || orcidRegex.test(orcidId) !== true) {
    responsePayload = { error: "Bad request. Invalid orcid_id." };
    return ContentService.createTextOutput(
      JSON.stringify(responsePayload),
    ).setMimeType(ContentService.MimeType.JSON);
  }

  // Get the credits associated with the specified ORCID ID.
  const credits = getCreditsByOrcidId(orcidId);

  return ContentService.createTextOutput(
    JSON.stringify({ orcidId, credits }),
  ).setMimeType(ContentService.MimeType.JSON);
}
