from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    DATABASE_URL: str = "postgresql+asyncpg://tunnel:password@postgres/tunneldb"
    REDIS_URL: str = "redis://:password@redis:6379/0"
    SECRET_KEY: str = "dev_secret_key_change_in_production_64_chars_long_xxxxxxxxxxxxx"
    INTERNAL_SECRET: str = "dev_internal_secret_key_change_in_production"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_HOURS: int = 24

    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""
    GOOGLE_REDIRECT_URI: str = "https://api.tunnel.dev/auth/google/callback"

    BASE_DOMAIN: str = "localhost"
    SERVER_HOST: str = "0.0.0.0"
    SERVER_PORT: int = 8000
    USE_HTTPS: bool = False

    PORT_POOL_MIN: int = 20000
    PORT_POOL_MAX: int = 29999
    DEFAULT_TTL_SECONDS: int = 7200
    MAX_TTL_SECONDS: int = 86400
    MAX_TUNNELS_PER_USER: int = 3
    MAX_REQUESTS_PER_TUNNEL: int = 10000
    RATE_LIMIT_PER_MINUTE: int = 100
    IDLE_WARN_MINUTES: int = 15
    IDLE_EXPIRE_MINUTES: int = 30

    GEOIP_DB_PATH: str = "/app/data/GeoLite2-Country.mmdb"
    MAXMIND_LICENSE_KEY: str = ""

    DEBUG: bool = False


settings = Settings()
