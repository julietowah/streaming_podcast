from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    MONGODB_URI: str
    MONGODB_DB: str

    JWT_SECRET: str
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days


    BUNNY_STORAGE_ZONE: str
    BUNNY_STORAGE_PASSWORD: str
    BUNNY_STORAGE_HOST: str = "storage.bunnycdn.com"
    BUNNY_CDN_BASE: str

    class Config:
        env_file = ".env"

settings = Settings()
