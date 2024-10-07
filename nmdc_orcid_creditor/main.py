import logging

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.responses import HTMLResponse
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


@app.get("/", response_class=HTMLResponse)
def get_root(request: Request):
    r"""Displays a web page containing a login link"""

    return templates.TemplateResponse(request=request, name="home.jinja")


@app.get("/redirect-to-orcid-login-page")
async def get_redirect_to_orcid_login_page(request: Request):
    r"""Redirects the client to ORCID, initiating the ORCID login flow"""

    redirect_uri = request.url_for("get_exchange_code_for_token")
    return await oauth.orcid.authorize_redirect(request, redirect_uri=redirect_uri)


@app.get("/exchange-code-for-token")
async def get_exchange_code_for_token(request: Request, code: str):
    r"""Exchanges an ORCID authorization code for an ORCID access token"""

    try:
        token: dict = await oauth.orcid.authorize_access_token(request)
    except OAuthError as error:
        return templates.TemplateResponse(request=request, name="error.jinja", context={"error_message": error.error})

    # Get the user's ORCID ID from the ORCID access token.
    orcid_id = token["orcid"]

    # Get a list of credits available to this ORCID ID.
    response = httpx.get(
        cfg.NMDC_ORCID_CREDITOR_PROXY_URL,
        params={"shared_secret": cfg.NMDC_ORCID_CREDITOR_PROXY_SHARED_SECRET, "orcid_id": orcid_id},
        follow_redirects=True,
    )
    logger.debug(response.url)
    res_json = response.json()
    context = {
        "orcid_id": res_json["orcid_id"],
        "credits": res_json["credits"],
    }

    return templates.TemplateResponse(request=request, name="credits.jinja", context=context)
