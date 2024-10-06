# nmdc-orcid-creditor

Web app NMDC team members use to credit ambassadors and champions via ORCID

## File tree

- `nmdc-orcid-creditor-proxy`: Google Apps Script
- `nmdc_orcid_creditor`: FastAPI app
- `static`: Static files served by the FastAPI app

## Development

- Create and customize `.env` file (if not already done): `$ cp .env.example .env`
- Install dependencies: `$ poetry install`
- Run tests: `$ poetry run pytest`
- Format Python code: `$ poetry run black .`
- Format HTML and JavaScript files (if you have [Node.js](https://nodejs.org/en/download/prebuilt-installer) installed):
  `$ npx prettier --write static/*.html nmdc-orcid-creditor-proxy/*`
- Run app in development mode: `$ poetry run fastapi dev nmdc_orcid_creditor/main.py`

## Journal

- We copied `static/favicon.png` from
  the [nmdc-field-notes](https://github.com/microbiomedata/nmdc-field-notes/blob/main/public/favicon.png) repository
