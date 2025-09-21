from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    BASE_URL: str
    REDIS_HOST: str
    REDIS_PORT: int
    CACHE_TTL_SECONDS: int
    DEBUG: bool = False

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

settings = Settings()