from pydantic_settings import BaseSettings, SettingsConfigDict


class Config(BaseSettings):
    r"""
    A Pydantic Settings class used to make the values of environment variables
    accessible to the rest of the application.

    Reference: https://fastapi.tiangolo.com/advanced/settings/
    """

    some_key: str = "Value from Config class"

    # Configure the class to read environment variable definitions from a `.env` file,
    # if such a file is present.
    # Reference: https://fastapi.tiangolo.com/advanced/settings/#reading-a-env-file
    model_config = SettingsConfigDict(env_file=".env")


cfg = Config()
