import os


def _env_flag(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _database_url() -> str | None:
    """Normalize the database URL for SQLAlchemy + psycopg 3.

    Railway (and most hosts) give ``postgresql://`` or ``postgres://``.
    SQLAlchemy maps those to psycopg2, which is not installed; the project
    uses psycopg 3, so point the URL at the ``psycopg`` driver.
    """
    url = os.getenv("DATABASE_URL")
    if not url:
        return None
    if url.startswith("postgres://"):
        url = "postgresql://" + url[len("postgres://"):]
    if url.startswith("postgresql://"):
        url = "postgresql+psycopg://" + url[len("postgresql://"):]
    return url


# True on Railway or when APP_ENV=production is set explicitly.
IS_PRODUCTION = (
    os.getenv("APP_ENV", "").strip().lower() == "production"
    or bool(os.getenv("RAILWAY_ENVIRONMENT"))
)


class Config:
    IS_PRODUCTION = IS_PRODUCTION

    SECRET_KEY = os.getenv("SECRET_KEY")

    SQLALCHEMY_DATABASE_URI = _database_url()
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    # Managed Postgres closes idle connections; check before reuse.
    SQLALCHEMY_ENGINE_OPTIONS = {"pool_pre_ping": True, "pool_recycle": 280}

    GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
    GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")

    GITHUB_CLIENT_ID = os.getenv("GITHUB_CLIENT_ID")
    GITHUB_CLIENT_SECRET = os.getenv("GITHUB_CLIENT_SECRET")

    # --- Email -------------------------------------------------------------
    # With RESEND_API_KEY set, mail goes through the Resend HTTP API (works on
    # hosts that block SMTP ports, e.g. Railway). Otherwise Gmail SMTP below.
    RESEND_API_KEY = os.getenv("RESEND_API_KEY")
    MAIL_FROM = os.getenv("MAIL_FROM", "NosiFit <onboarding@resend.dev>")

    MAIL_SERVER = os.getenv("MAIL_SERVER", "smtp.gmail.com")
    MAIL_PORT = int(os.getenv("MAIL_PORT", "587"))
    MAIL_USE_TLS = True
    MAIL_USE_SSL = False
    MAIL_USERNAME = os.getenv("MAIL_USERNAME")
    MAIL_PASSWORD = os.getenv("MAIL_PASSWORD")
    MAIL_DEFAULT_SENDER = ("NosiFit", os.getenv("MAIL_USERNAME"))

    # --- Cookies -----------------------------------------------------------
    # Secure cookies only travel over HTTPS, so they are on in production and
    # off locally (http://localhost). Override with SESSION_COOKIE_SECURE.
    SESSION_COOKIE_SECURE = _env_flag("SESSION_COOKIE_SECURE", IS_PRODUCTION)
    REMEMBER_COOKIE_SECURE = SESSION_COOKIE_SECURE
    SESSION_COOKIE_HTTPONLY = True
    REMEMBER_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    REMEMBER_COOKIE_SAMESITE = "Lax"

    PREFERRED_URL_SCHEME = "https" if IS_PRODUCTION else "http"

    # /premium/activate grants premium for free. Fine while developing,
    # never on a public site until real payments exist.
    PREMIUM_SELF_ACTIVATION = _env_flag("PREMIUM_SELF_ACTIVATION", not IS_PRODUCTION)
