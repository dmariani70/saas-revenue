from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql://saas:saas@localhost:5432/saas"
    secret_key: str = "change-me"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 480
    data_folder: str = "./data/imports"
    fx_strategy: str = "first_day"  # first_day | avg
    open_exchange_rates_key: str = ""

    model_config = {"env_file": ".env"}


settings = Settings()
