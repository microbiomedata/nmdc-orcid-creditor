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
    except OAuthError as error:
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
    credit_type: Annotated[str, Body(..., embed=True)],
    orcid_access_token: dict = Depends(get_orcid_access_token),
):
    r"""
    Claims all unclaimed credits that both have the specified type and are associated with the specified ORCID ID
    """

    if orcid_access_token is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid ORCID access token")
    orcid_id = orcid_access_token["orcid"]

    # FIXME: Here, claim the credit via ORCID's API. If unsuccessful, return an error response and abort
    #        (instead of proceeding to record the claim event into the Google Sheets document).
    #
    pass

    # Record the claim event into the Google Sheets document via the proxy.
    try:
        response = httpx.post(
            cfg.NMDC_ORCID_CREDITOR_PROXY_URL,
            params={
                "shared_secret": cfg.NMDC_ORCID_CREDITOR_PROXY_SHARED_SECRET,
                "orcid_id": orcid_id,
                "credit_type": credit_type,
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
