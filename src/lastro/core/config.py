"""Application settings, read from the environment (plan NUC-01, D3 and D7).

Reading the settings never opens a connection. Every module that needs a setting calls
`get_settings()`; nothing here keeps mutable global state.
"""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Settings of the API and of the migrations.

    Attributes:
        database_url: SQLAlchemy URL used by the API, as the application role
            (`DATABASE_URL`).
        migrations_database_url: SQLAlchemy URL used only by Alembic, as the owner role
            (`MIGRATIONS_DATABASE_URL`). Optional for the API process.
        invitation_hours: how long an accountant invitation is valid, in hours
            (`LASTRO_CONVITE_HORAS`, default 48, at least 1; ACE-02, plan D3).
    """

    model_config = SettingsConfigDict(extra="ignore", frozen=True, populate_by_name=True)

    # repr=False: the URLs carry passwords and must not show up in logs or tracebacks.
    database_url: str = Field(repr=False)
    migrations_database_url: str | None = Field(default=None, repr=False)
    invitation_hours: int = Field(default=48, ge=1, validation_alias="LASTRO_CONVITE_HORAS")


def get_settings() -> Settings:
    """Read the settings from the current environment.

    Returns:
        A new `Settings` built from the environment variables.

    Raises:
        pydantic.ValidationError: if `DATABASE_URL` is missing.
    """
    return Settings()
