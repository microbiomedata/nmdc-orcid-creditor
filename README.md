# nmdc-orcid-creditor

Web app NMDC team members use to credit ambassadors and champions via ORCID

## File tree

- `nmdc-orcid-creditor-proxy`: Google Apps Script
- `nmdc_orcid_creditor`: FastAPI app
- `nmdc_orcid_creditor/templates`: Jinja2 templates used by the FastAPI app
- `static`: Static files served by the FastAPI app

## Development

- Create and customize `.env` file (if not already done):
  ```sh
  cp .env.example .env
  ```
- Install dependencies:
  ```sh
  poetry install
  ```
- Run tests:
  ```sh
  poetry run pytest
  ```
- Format Python code:
  ```sh
  poetry run black .
  ```
- Lint and format Jinja2 templates:
  ```sh
  poetry run djlint --reformat --lint .
  ```
- Format JavaScript files (if you have [Node.js](https://nodejs.org/en/download/prebuilt-installer) installed):
  ```sh
  npx prettier --write nmdc-orcid-creditor-proxy/*.js
  ```
- Run app in development mode:
  ```sh
  poetry run fastapi dev nmdc_orcid_creditor/main.py
  ```

## Journal

- We copied `static/favicon.png` from
  the [nmdc-field-notes](https://github.com/microbiomedata/nmdc-field-notes/blob/main/public/favicon.png) repository
- We downloaded `static/undraw_online_resume_re_ru7s.svg` from [unDraw](https://undraw.co/license)
