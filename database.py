"""Database configuration and initialization helpers."""

import os

from extensions import db


def normalize_database_url(raw_url: str) -> str:
    """Ensure the PostgreSQL URL uses the psycopg (v3) SQLAlchemy dialect."""
    url = raw_url.strip()
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql+psycopg://", 1)
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+psycopg://", 1)
    return url


def get_database_uri() -> str:
    """Read and validate DATABASE_URL from the environment."""
    raw_url = os.environ.get("DATABASE_URL")
    if not raw_url:
        raise RuntimeError(
            "DATABASE_URL environment variable is not set. "
            "Add it to your .env file or system environment."
        )
    return normalize_database_url(raw_url)


def init_db(app) -> None:
    """Configure SQLAlchemy for PostgreSQL and ensure tables exist."""
    app.config["SQLALCHEMY_DATABASE_URI"] = get_database_uri()
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
        "pool_pre_ping": True,
        "pool_recycle": 300,
    }

    db.init_app(app)

    # Import models before create_all so SQLAlchemy registers metadata.
    import models  # noqa: F401

    with app.app_context():
        db.create_all()
