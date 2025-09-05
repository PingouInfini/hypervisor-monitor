from pydantic_settings import BaseSettings
from pydantic import Field, validator
from typing import List

class Settings(BaseSettings):
    hosts: List[str] = Field(default_factory=list, alias="HOSTS")
    poll_minutes: int = Field(default=5, alias="POLL_MINUTES")
    winrm_username: str = Field(default="", alias="WINRM_USERNAME")
    winrm_password: str = Field(default="", alias="WINRM_PASSWORD")
    winrm_use_ssl: bool = Field(default=False, alias="WINRM_USE_SSL")
    winrm_port: int = Field(default=5985, alias="WINRM_PORT")
    winrm_verify_ssl: bool = Field(default=False, alias="WINRM_VERIFY_SSL")
    db_path: str = Field(default="data/app.db", alias="DB_PATH")

    @validator("hosts", pre=True)
    def split_hosts(cls, v):
        if isinstance(v, str):
            return [h.strip() for h in v.split(",") if h.strip()]
        return v

settings = Settings()
