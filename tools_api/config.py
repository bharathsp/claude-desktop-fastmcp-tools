from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    host: str = "127.0.0.1"
    port: int = 8100
    api_prefix: str = "/api/v1"
    ssl_verify: bool = True

    class Config:
        env_prefix = "TOOLS_API_"


settings = Settings()
