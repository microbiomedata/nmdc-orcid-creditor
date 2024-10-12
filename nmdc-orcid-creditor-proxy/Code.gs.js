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

function test_claimCreditsByTypeAndOrcidId() {
  Logger.log(
    claimCreditsByTypeAndOrcidId("Ambassador 2023", "0009-0002-5962-1947"),
  );
}

/**
 * Claims the credits having the specified combination of credit type and ORCID ID,
 * in the Google Sheets document. Then, returns the credits associated with the
 * specified ORCID ID, which will reflect any updates made.
 */
function claimCreditsByTypeAndOrcidId(creditType, orcidId) {
  const spreadsheet = SpreadsheetApp.openById(CONFIG.SPREADSHEET_ID);
  const sheet = spreadsheet.getSheetByName(CONFIG.SHEET_NAME);

  // Get all the values on the sheet.
  const dataRange = sheet.getDataRange();
  const values = dataRange.getValues();

  // Determine the indexes of the relevant columns.
  const columnNames = values[0];
  const creditTypeColumnIndex = columnNames.indexOf("column.CREDIT_TYPE");
  const orcidIdColumnIndex = columnNames.indexOf("column.ORCID_ID");

  // Determine the column number of the column indicating when the credit was claimed.
  // Note: Google Sheets column numbers are 1-based.
  const claimedAtColumnNumber = columnNames.indexOf("column.CLAIMED_AT") + 1;

  // Find the row numbers of the rows having the specified credit type and ORCID ID pair.
  let rowNumbers = [];
  values.forEach((row, index) => {
    if (
      row[orcidIdColumnIndex] === orcidId &&
      row[creditTypeColumnIndex] === creditType
    ) {
      rowNumbers.push(index + 1); // Note: Google Sheets row numbers are 1-based.
    }
  });

  // Generate a timestamp representing the current date and time (now).
  const claimedAt = new Date();

  // Write that timestamp to each of those rows, in the column that indicates when the credit was claimed.
  rowNumbers.forEach((rowNumber) => {
    const cell = dataRange.getCell(rowNumber, claimedAtColumnNumber);
    cell.setValue(claimedAt);
  });

  // Return the updated credits associated with this ORCID ID.
  // Note: This will include the recently-written timestamps.
  return getCreditsByOrcidId(orcidId);
}

/**
 * Sends an error HTTP response if the specified shared secret is incorrect.
 */
function validateSharedSecret(sharedSecret) {
  if (
    typeof sharedSecret === "string" &&
    sharedSecret === CONFIG.SHARED_SECRET
  ) {
    return sharedSecret;
  } else {
    return ContentService.createTextOutput(
      JSON.stringify({ error: "Forbidden. Incorrect shared_secret." }),
    ).setMimeType(ContentService.MimeType.JSON);
  }
}

/**
 * Sends an error HTTP response if the specified ORCID ID is invalid.
 *
 * Note: Checks basic syntax only—does not calculate checksum.
 */
function validateOrcidId(orcidId) {
  if (typeof orcidId === "string" && orcidRegex.test(orcidId) === true) {
    return orcidId;
  } else {
    return ContentService.createTextOutput(
      JSON.stringify({ error: "Bad request. Invalid orcid_id." }),
    ).setMimeType(ContentService.MimeType.JSON);
  }
}

/**
 * Sends an error HTTP response if the specified credit type is invalid.
 *
 * Note: Checks syntax only—does not check for presence in spreadshet.
 */
function validateCreditType(creditType) {
  if (typeof creditType === "string" && creditType !== "") {
    return creditType;
  } else {
    return ContentService.createTextOutput(
      JSON.stringify({ error: "Bad request. Invalid credit_type." }),
    ).setMimeType(ContentService.MimeType.JSON);
  }
}

/**
 * Handle incoming POST requests.
 *
 * Reference: https://developers.google.com/apps-script/guides/web
 */
function doPost(event) {
  // Extract and validate the query parameters.
  const queryParams = event.parameter;
  const _ = validateSharedSecret(queryParams["shared_secret"]);
  const orcidId = validateOrcidId(queryParams["orcid_id"]);
  const creditType = validateCreditType(queryParams["credit_type"]);

  // Update the specified credits and then get all credits associated with that ORCID ID.
  const credits = claimCreditsByTypeAndOrcidId(creditType, orcidId);

  return ContentService.createTextOutput(
    JSON.stringify({ orcid_id: orcidId, credits }),
  ).setMimeType(ContentService.MimeType.JSON);
}

/**
 * Handle incoming GET requests.
 *
 * Reference: https://developers.google.com/apps-script/guides/web
 */
function doGet(event) {
  // Extract and validate the query parameters.
  const queryParams = event.parameter;
  const _ = validateSharedSecret(queryParams["shared_secret"]);
  const orcidId = validateOrcidId(queryParams["orcid_id"]);

  // Get the credits associated with the specified ORCID ID.
  const credits = getCreditsByOrcidId(orcidId);

  return ContentService.createTextOutput(
    JSON.stringify({ orcid_id: orcidId, credits }),
  ).setMimeType(ContentService.MimeType.JSON);
}
