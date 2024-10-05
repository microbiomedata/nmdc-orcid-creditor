from pydantic_settings import BaseSettings, SettingsConfigDict


class Config(BaseSettings):
    r"""
    A Pydantic Settings class used to make the values of environment variables
    accessible to the rest of the application.

    Reference: https://fastapi.tiangolo.com/advanced/settings/
    """

    # Base URL end users can use to access this web application.
    SERVER_BASE_URL: str = ""

    # Random string the `SessionMiddleware` will use to encrypt session cookie values.
    # Reference: https://www.starlette.io/middleware/#sessionmiddleware
    SERVER_SESSION_SECRET_KEY: str = ""

    # ORCID URLs, Oauth scopes, and Client (integration) information.
    # Reference: https://info.orcid.org/documentation/api-tutorials/api-tutorial-add-and-update-data-on-an-orcid-record/
    ORCID_ACCESS_TOKEN_URL: str = ""  # ends with "/token"
    ORCID_AUTHORIZE_BASE_URL: str = ""  # ends with "/authorize"
    ORCID_OAUTH_SCOPES: str = ""  # space-delimited list
    ORCID_CLIENT_ID: str = ""
    ORCID_CLIENT_SECRET: str = ""

    # Configure the class to read environment variable definitions from a `.env` file,
    # if such a file is present.
    # Reference: https://fastapi.tiangolo.com/advanced/settings/#reading-a-env-file
    model_config = SettingsConfigDict(env_file=".env")


cfg = Config()
