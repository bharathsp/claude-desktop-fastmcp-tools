from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    tools_api_base_url: str = "http://127.0.0.1:8100"
    tools_api_prefix: str = "/api/v1"
    server_name: str = "Custom Tools MCP Server"
    ssl_verify: bool = True

    class Config:
        env_prefix = "MCP_"


settings = Settings()
