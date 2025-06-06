import logging
from datetime import datetime
from typing import Annotated, Union

from fastapi import FastAPI, Request, Depends, HTTPException, status, Body
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.responses import HTMLResponse, RedirectResponse
from starlette.middleware.sessions import SessionMiddleware
from authlib.integrations.starlette_client import OAuth, OAuthError
import httpx

from nmdc_orcid_creditor.config import cfg
from nmdc_orcid_creditor.helpers import (
    extract_put_code_from_location_header,
    extract_year_month_day_from_datetime_string,
)

# Enable debug output on the console.
logger = logging.getLogger("uvicorn")
logger.setLevel(logging.DEBUG)

# Register ORCID as a remote application that uses OAuth 2.0.
#
# References:
# - https://docs.authlib.org/en/latest/client/fastapi.html
# - https://docs.authlib.org/en/latest/client/starlette.html#starlette-client
# - https://docs.authlib.org/en/latest/client/frameworks.html#using-oauth-2-0-to-log-in
#
oauth = OAuth()
oauth.register(
    # Note: Once a `RemoteApp` is registered with `{name}` here, it
    #       can be accessed via `oauth.{name}` (e.g. `oauth.orcid`).
    name="orcid",
    client_id=cfg.ORCID_CLIENT_ID,
    client_secret=cfg.ORCID_CLIENT_SECRET,
    access_token_url=cfg.ORCID_ACCESS_TOKEN_URL,
    access_token_params=None,
    authorize_url=cfg.ORCID_AUTHORIZE_BASE_URL,
    authorize_params=None,
    api_base_url=cfg.SERVER_BASE_URL,
    client_kwargs=dict(scope=cfg.ORCID_OAUTH_SCOPES),
)

app = FastAPI()

# Add session middleware so the OAuth library can store data in a cookie(s)
# when performing the `oauth.orcid.authorize_redirect(...)` step.
#
# Note: I assume (not sure) the value it stores there is the `state`
#       query param value in the URL of the ORCID login page.
#
# Reference: https://www.starlette.io/middleware/#sessionmiddleware
#
app.add_middleware(SessionMiddleware, secret_key=cfg.SERVER_SESSION_SECRET_KEY)

# Designate a directory that will store static files, such as the favicon.
# Reference: https://fastapi.tiangolo.com/tutorial/static-files/
app.mount("/static", StaticFiles(directory="static"), name="static")

# Designate a directory that will store template files.
# Reference: https://fastapi.tiangolo.com/advanced/templates/#using-jinja2templates
templates = Jinja2Templates(directory="nmdc_orcid_creditor/templates")


@app.get("/", response_class=HTMLResponse, include_in_schema=False)
def get_root(request: Request):
    r"""Displays a web page containing a login link"""

    return templates.TemplateResponse(request=request, name="home.html.jinja")


@app.get("/redirect-to-orcid-login-page", include_in_schema=False)
async def get_redirect_to_orcid_login_page(request: Request):
    r"""Redirects the client to ORCID, initiating the ORCID login flow"""

    redirect_uri = request.url_for("get_exchange_code_for_token")
    return await oauth.orcid.authorize_redirect(request, redirect_uri=redirect_uri)


@app.get("/exchange-code-for-token", include_in_schema=False)
async def get_exchange_code_for_token(request: Request):
    r"""Exchanges an ORCID authorization code for an ORCID access token"""

    try:
        orcid_access_token: dict = await oauth.orcid.authorize_access_token(request)
    except (OAuthError, httpx.HTTPStatusError) as error:
        # Note: An `httpx.HTTPStatusError` is raised when the response status code is 4xx or 5xx.
        #       Reference: https://www.python-httpx.org/exceptions/#exception-classes
        logger.exception(error)
        return templates.TemplateResponse(
            request=request, name="error.html.jinja", context={"error_message": "Failed to log in to ORCID."}
        )

    # Store the token in the session, overwriting any previous token.
    #
    # Note: The session is persisted as a signed cookie on the client side. Because it is signed by the server,
    #       the client cannot modify it; although the client can decode and read its contents.
    #
    request.session["orcid_access_token"] = orcid_access_token

    # Now, redirect the client to the "Credits" page.
    return RedirectResponse(url=request.url_for("get_credits"))


def validate_orcid_access_token(orcid_access_token: dict) -> Union[dict, None]:
    r"""
    Validates the ORCID access token, returning it if valid or `None` if invalid

    Note: This function does _not_ validate that the ORCID access token has not
          been tampered with since we stored it in the session. That validation
          is handled by the `SessionMiddleware`.
    """

    # Check whether the token expires in the future (not the past or present).
    if "expires_at" in orcid_access_token:
        expires_at = orcid_access_token["expires_at"]
        if datetime.fromtimestamp(expires_at) > datetime.now():
            return orcid_access_token

    return None


def get_orcid_access_token(request: Request) -> Union[dict, None]:
    r"""Returns the ORCID access token, if valid, present in the session; otherwise return `None`"""

    return validate_orcid_access_token(request.session.get("orcid_access_token", {}))


@app.get("/logout", include_in_schema=False)
async def logout(request: Request):
    r"""Logs the client out by clearing the session, then redirects the client to the home page"""

    request.session.clear()
    return RedirectResponse(url=request.url_for("get_root"))


@app.get("/credits", include_in_schema=False)
async def get_credits(request: Request, orcid_access_token: dict = Depends(get_orcid_access_token)):
    r"""Responds with the credits page, which displays the credits associated with the signed-in user"""

    if orcid_access_token is None:
        return RedirectResponse(url=request.url_for("get_root"))
    orcid_id = orcid_access_token["orcid"]
    name = orcid_access_token["name"]

    # Respond with the credits page.
    context = {
        "orcid_id": orcid_id,
        "name": name,
    }
    return templates.TemplateResponse(request=request, name="credits.html.jinja", context=context)


@app.get("/api/credits", tags=["Credits"])
async def get_api_credits(
    orcid_access_token: dict = Depends(get_orcid_access_token),
):
    r"""Returns all credits associated with the specified ORCID ID"""

    if orcid_access_token is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid ORCID access token")
    orcid_id = orcid_access_token["orcid"]

    # Get a list of credits available to this ORCID ID.
    try:
        response = httpx.get(
            cfg.NMDC_ORCID_CREDITOR_PROXY_URL,
            params={
                "shared_secret": cfg.NMDC_ORCID_CREDITOR_PROXY_SHARED_SECRET,
                "orcid_id": orcid_id,
            },
            follow_redirects=True,
        )
        res_json = response.json()
        return {
            "orcid_id": res_json["orcid_id"],
            "credits": res_json["credits"],
        }
    except httpx.HTTPError as error:
        logger.exception(error)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to load credits")


@app.post("/api/credits/claim", tags=["Credits"])
async def post_api_credits_claim(
    # Note: This parameter tells FastAPI the request payload will have a property named `credit_type`.
    #
    # References:
    # - https://fastapi.tiangolo.com/tutorial/body-multiple-params/#multiple-body-parameters (docs)
    # - https://stackoverflow.com/a/70636163 (example)
    #
    credit_type: Annotated[str, Body(title="Credit Type", description="The type of the credit")],
    start_date: Annotated[str, Body(title="Start Date", description="The start date, if any, of the credit")],
    end_date: Annotated[str, Body(title="End Date", description="The end date, if any, of the credit")],
    orcid_access_token: dict = Depends(get_orcid_access_token),
):
    r"""
    Claim a credit associated with the signed-in user's ORCID ID, having the specified combination
    of credit type, start date, and end date
    """

    if orcid_access_token is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid ORCID access token")
    orcid_id = orcid_access_token["orcid"]

    # Get all of this user's credits from the Google Sheets document via the proxy.
    all_credits = []
    try:
        response = httpx.get(
            cfg.NMDC_ORCID_CREDITOR_PROXY_URL,
            params={
                "shared_secret": cfg.NMDC_ORCID_CREDITOR_PROXY_SHARED_SECRET,
                "orcid_id": orcid_id,
            },
            follow_redirects=True,
        )
        res_json = response.json()
        all_credits = res_json["credits"]
    except httpx.HTTPError as error:
        logger.exception(error)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to load credits")

    # Check whether the user has any unclaimed credits having the specified combination
    # of {ORCID ID, credit type, start date, end date} values.
    #
    # Note: The credit's `column.CLAIMED_AT` value will be an empty string when
    #       that cell in the Google Sheets spreadsheet is empty (which we use
    #       to indicate that the credit has not been claimed).
    #
    # Note: We assume that the Google Sheets document does not contain multiple rows having the same combination
    #       of `column.ORCID_ID` and `column.CREDIT_TYPE` values. In case it does, we process only the first row.
    #
    # TODO: Add a validation rule to the Google Sheets document to prevent multiple rows from having the same
    #       combination of `column.ORCID_ID` and `column.CREDIT_TYPE` values. Accounting for duplicates there
    #       would complicate this code.
    #
    # TODO: Also, update existing code and documentation to reflect the same assumption. Some existing code was
    #       written under the contrary assumption that multiple rows of the spreadsheet _could_ have the same
    #       combination of `column.ORCID_ID` and `column.CREDIT_TYPE` values.
    #
    credit_to_claim = None
    for credit in all_credits:
        if (
            credit.get("column.ORCID_ID") == orcid_id
            and credit.get("column.CREDIT_TYPE") == credit_type
            and credit.get("column.START_DATE") == start_date
            and credit.get("column.END_DATE") == end_date
            and credit.get("column.CLAIMED_AT") == ""
        ):
            credit_to_claim = credit
            break

    # If the user has no such unclaimed credits, return an error response and abort.
    if credit_to_claim is None:
        logger.warning(f"Found no unclaimed credits of type '{credit_type}' for ORCID ID '{orcid_id}'")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"There are no matching credits available to claim.",
        )

    logger.debug(f"Claiming credit: {credit_to_claim}")

    # Get the affiliation type associated with the credit.
    affiliation_type = credit_to_claim.get("column.AFFILIATION_TYPE", "").strip()
    if affiliation_type not in ["membership", "service"]:
        logger.error(f"The credit has an invalid affiliation type. Credit: {credit_to_claim}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"The credit has an invalid affiliation type. Please report this to an administrator.",
        )

    # Get the start date and end date strings associated with the credit; and—for any
    # that isn't empty—parse it into its corresponding year, month, and day strings.
    has_start_date = False
    has_end_date = False
    start_date = credit_to_claim.get("column.START_DATE", "").strip()
    end_date = credit_to_claim.get("column.END_DATE", "").strip()
    try:
        if len(start_date) > 0:
            start_year, start_month, start_day = extract_year_month_day_from_datetime_string(start_date)
            logger.debug(f"Parsed {start_date=} into {start_year=}, {start_month=}, {start_day=}")
            has_start_date = True
        if len(end_date) > 0:
            end_year, end_month, end_day = extract_year_month_day_from_datetime_string(end_date)
            logger.debug(f"Parsed {end_date=} into {end_year=}, {end_month=}, {end_day=}")
            has_end_date = True
    except ValueError as error:
        logger.error(f"Failed to parse start date or end date. Details: {error}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="The credit has an invalid date associated with it. Please report this to an administrator.",
        )

    # Get the URL associated with the credit.
    credit_url = credit_to_claim.get("column.DETAILS_URL", "").strip()

    # Create the ("membership" or "service") affiliation on the specified ORCID profile and extract the newly-created
    # affiliation's "put-code" from the API response. If we fail to do either thing, return an error response and abort
    # (instead of proceeding to record the claim event and "put-code" into the Google Sheets document).
    #
    # References:
    # - https://github.com/ORCID/orcid-model/blob/master/src/main/resources/record_3.0/README.md#add-record-items
    # - https://github.com/ORCID/ORCID-Source/tree/main/orcid-api-web#orcid-apis
    # - https://github.com/ORCID/ORCID-Source/blob/main/orcid-api-web/tutorial/affiliations.md
    #
    try:
        orcid_api_url = f"{cfg.ORCID_API_BASE_URL}/{orcid_id}/{affiliation_type}"

        # Build the start date and end date items (or lack thereof) for the API request payload (dictionary).
        #
        # Note: The ORCID API does allow the top-level "start-date" and "end-date" fields to be omitted.
        #       When "start-date" is omitted, the person's ORCID profile will show only the end date (e.g. "2023-12-31 | Team member").
        #       When "end-date" is omitted, the person's ORCID profile will append "to present"      (e.g. "2022-01-01 to present | Team member").
        #       When both are omitted, the person's ORCID profile will not show any dates            (e.g. "Team member").
        #        
        start_date_item = {"start-date": {"year": {"value": start_year}, "month": {"value": start_month}, "day": {"value": start_day}}} if has_start_date else {}
        end_date_item = {"end-date": {"year": {"value": end_year}, "month": {"value": end_month}, "day": {"value": end_day}}} if has_end_date else {}

        response = httpx.post(
            orcid_api_url,
            headers={"Authorization": f"Bearer {orcid_access_token['access_token']}"},
            json={
                # TODO: Consider including a department and other information (see payload examples in ORCID docs).
                "role-title": f"{credit_type}",
                **start_date_item,
                **end_date_item,
                "organization": {
                    "name": "National Microbiome Data Collaborative",
                    "address": {"city": "Berkeley", "region": "California", "country": "US"},
                    "disambiguated-organization": {
                        "disambiguated-organization-identifier": "https://ror.org/05cwx3318",
                        "disambiguation-source": "ROR",
                    },
                },
                # Note: Submitting a "url.value" value of "" is OK. In that situation,
                #       ORCID will not display the "URL" field for this affiliation.
                "url": {"value": credit_url},
            },
        )

        # Try to extract the affiliation's "put-code" from the response's "location" header.
        response_location_header = response.headers.get("location", default="")
        affiliation_put_code = extract_put_code_from_location_header(response_location_header)

        # If the response status code wasn't `201` or we failed to extract a "put-code",
        # abort; i.e., don't record that the credit has been claimed.
        if response.status_code != 201 or affiliation_put_code is None:
            logger.debug(f"{response.status_code=}\n{response.headers=}\n{response.content=}")
            raise RuntimeError("Failed to claim credit.")
        else:
            logger.debug(f"Created affiliation having put-code: {affiliation_put_code}")
    except (httpx.HTTPError, RuntimeError) as error:
        logger.exception(error)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to claim credit.")

    # Record the claim event, including the "put-code", into the Google Sheets document via the proxy.
    try:
        response = httpx.post(
            cfg.NMDC_ORCID_CREDITOR_PROXY_URL,
            params={
                "shared_secret": cfg.NMDC_ORCID_CREDITOR_PROXY_SHARED_SECRET,
                "orcid_id": orcid_id,
                "credit_type": credit_type,
                "start_date": credit_to_claim.get("column.START_DATE"),  # uses the value verbatim
                "end_date": credit_to_claim.get("column.END_DATE"),  # uses the value verbatim
                "affiliation_put_code": affiliation_put_code,
            },
            follow_redirects=True,
        )
        res_json = response.json()
        return {
            "orcid_id": res_json["orcid_id"],
            "credits": res_json["credits"],
        }
    except httpx.HTTPError as error:
        logger.exception(error)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to record claim.")
