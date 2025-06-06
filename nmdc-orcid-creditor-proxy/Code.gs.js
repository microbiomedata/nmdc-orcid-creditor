/**
 * This Google Apps Script script accepts HTTP requests from the nmdc-orcid-creditor FastAPI app
 * (with which it shares a secret), retrieves data from a Google Sheets document, and returns
 * that data to the FastAPI app. In that sense, this script is a "proxy" between the FastAPI
 * app and Google Sheets.
 */

// Reference: https://support.orcid.org/hc/en-us/articles/360006897674-Structure-of-the-ORCID-Identifier
const orcidRegex = new RegExp(/^\d{4}-\d{4}-\d{4}-\d{3}[0-9X]$/);

/**
 * Returns all credits associated with the specified ORCID ID,
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

function test_markCreditAsClaimed() {
  Logger.log(
    markCreditAsClaimed(
      "Ambassador 2023",
      "0009-0002-5962-1947",
      "2023-02-14T08:00:00.000Z",
      "2023-07-04T08:00:00.000Z",
      "12345",
    ),
  );
}

/**
 * Marks a single, unclaimed credit in the Google Sheets document as having been claimed.
 *
 * Finds the first row describing an unclaimed credit having the specified combination
 * of {credit type, ORCID ID, start date, end date} in the Google Sheets document, and
 * updates its "claimed at" timestamp (to indicate it's been claimed) and stores the
 * specified affiliation "put-code" on that row.
 *
 * Returns all credits associated with the specified ORCID ID, which will reflect
 * any updates made by this function.
 */
function markCreditAsClaimed(
  creditType,
  orcidId,
  startDate,
  endDate,
  affiliationPutCode,
) {
  const spreadsheet = SpreadsheetApp.openById(CONFIG.SPREADSHEET_ID);
  const sheet = spreadsheet.getSheetByName(CONFIG.SHEET_NAME);

  // Get all the values on the sheet.
  const dataRange = sheet.getDataRange();
  const values = dataRange.getValues();

  // Determine the 0-based indexes of columns relevant to this operation.
  const columnNames = values[0];
  const creditTypeColumnIndex = columnNames.indexOf("column.CREDIT_TYPE");
  const orcidIdColumnIndex = columnNames.indexOf("column.ORCID_ID");
  const startDateColumnIndex = columnNames.indexOf("column.START_DATE");
  const endDateColumnIndex = columnNames.indexOf("column.END_DATE");
  const claimedAtColumnIndex = columnNames.indexOf("column.CLAIMED_AT");

  // Determine the 1-based column _numbers_ of (a) the column indicating when the
  // credit was claimed, and (b) the column indicating the affiliation's "put-code".
  // Note: Google Sheets column numbers are 1-based.
  const claimedAtColumnNumber = claimedAtColumnIndex + 1;
  const affiliationPutCodeColumnNumber =
    columnNames.indexOf("column.AFFILIATION_PUT_CODE") + 1;

  // Find the 1-based row _number_ of the first row having the specified combination
  // of {credit type, ORCID ID, start date, end date} that is not been claimed yet.
  let creditRowNumber = null;
  for (let rowIndex = 0; rowIndex < values.length; rowIndex++) {
    const row = values[rowIndex];
    if (
      row[orcidIdColumnIndex] === orcidId &&
      row[creditTypeColumnIndex] === creditType &&
      row[startDateColumnIndex] === startDate &&
      row[endDateColumnIndex] === endDate &&
      row[claimedAtColumnIndex] === "" // unclaimed
    ) {
      creditRowNumber = rowIndex + 1; // Note: Google Sheets row numbers are 1-based.
      break;
    }
  }

  // Generate a timestamp representing the current date and time (now).
  const claimedAt = new Date();

  // If a credit row number was found, write the following pieces of information to that row:
  // (a) that timestamp (so we know when the credit was claimed); and
  // (b) the specified "put-code" (so we can update the created affiliation later).
  if (typeof creditRowNumber === "number") {
    const claimedAtCell = dataRange.getCell(
      creditRowNumber,
      claimedAtColumnNumber,
    );
    const affiliationPutCodeCell = dataRange.getCell(
      creditRowNumber,
      affiliationPutCodeColumnNumber,
    );

    claimedAtCell.setValue(claimedAt);
    affiliationPutCodeCell.setValue(affiliationPutCode);
  }

  // Return all credits associated with this ORCID ID.
  // Note: This will reflect any updates made by this function.
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
      JSON.stringify({ error: "Unauthorized. Invalid shared_secret." }),
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
 * Note: Checks syntax only—does not check for presence in spreadsheet.
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
 * Sends an error HTTP response if the specified optional timestamp is invalid.
 *
 * Note: Checks syntax only—does not check for presence in spreadsheet. Also,
 *       an empty string are allowed (we use for credits that lack a start date
 *       and/or end date).
 */
function validateOptionalTimestamp(optionalTimestamp) {
  if (typeof optionalTimestamp === "string") {
    return optionalTimestamp;
  } else {
    return ContentService.createTextOutput(
      JSON.stringify({
        error: "Bad request. Invalid start_date and/or end_date.",
      }),
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
  const startDate = validateOptionalTimestamp(queryParams["start_date"]);
  const endDate = validateOptionalTimestamp(queryParams["end_date"]);
  const affiliationPutCode = validateCreditType(
    queryParams["affiliation_put_code"],
  );

  // Update the specified credit, if it exists, and then get all credits
  // associated with that ORCID ID (done in that order, so that the credits
  // reflect the update to the specified one).
  const credits = markCreditAsClaimed(
    creditType,
    orcidId,
    startDate,
    endDate,
    affiliationPutCode,
  );

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

  // Get all credits associated with the specified ORCID ID.
  const credits = getCreditsByOrcidId(orcidId);

  return ContentService.createTextOutput(
    JSON.stringify({ orcid_id: orcidId, credits }),
  ).setMimeType(ContentService.MimeType.JSON);
}
