from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    devin_api_key: str = ""
    devin_org_id: str = ""
    github_webhook_secret: str = ""
    github_token: str = ""
    target_repo: str = "danagajewski/superset"
    poll_interval_seconds: int = 30
    data_file_path: str = "data.json"
    devin_api_base_url: str = "https://api.devin.ai/v3"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
