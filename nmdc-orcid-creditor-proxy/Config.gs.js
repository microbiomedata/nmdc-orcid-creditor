const CONFIG = {
  // Note: This is a random string known to both the FastAPI app
  //       and the Google Apps Script script, but nobody else.
  //       It's sensitive information, like a password or key.
  SHARED_SECRET: "__REPLACE_ME__",

  // Note: You can get this from the Google Sheet's document's URL.
  //       Here's where it appears in a Google Sheets URL:
  //       https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/edit
  SPREADSHEET_ID: "__REPLACE_ME__",

  // Note: You can get this from the Google Sheets tabs.
  SHEET_NAME: "__REPLACE_ME__",
};
