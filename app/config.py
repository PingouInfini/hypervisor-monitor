import json
from pydantic import BaseModel, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List, Dict, Optional

# --- Modèles pour la config ---

class HostConfig(BaseModel):
    ip: str
    type: str  # ex: 'hyperv', 'proxmox', 'esxi'
    tags: List[str] = []
    username: Optional[str] = None
    password: Optional[str] = None

class TagColor(BaseModel):
    bg: str
    text: str

# --- Settings principal ---

class Settings(BaseSettings):
    # Configuration pour lire le fichier .env
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    poll_minutes: int = Field(default=5, alias="POLL_MINUTES")

    winrm_username: str = Field(default="", alias="WINRM_USERNAME")
    winrm_password: str = Field(default="", alias="WINRM_PASSWORD")
    winrm_use_ssl: bool = Field(default=False, alias="WINRM_USE_SSL")
    winrm_port: int = Field(default=5985, alias="WINRM_PORT")
    winrm_verify_ssl: bool = Field(default=False, alias="WINRM_VERIFY_SSL")

    db_path: str = Field(default="data/app.db", alias="DB_PATH")

    # Déclaration en JSON
    hosts_config: List[HostConfig] = Field(default_factory=list, alias="HOSTS_CONFIG")
    tag_colors: Dict[str, TagColor] = Field(default_factory=dict, alias="TAG_COLORS")

    @field_validator("hosts_config", "tag_colors", mode="before")
    @classmethod
    def parse_json(cls, v, info):
        # Si c'est déjà le bon type (ex: en instanciation directe), on retourne tel quel
        if isinstance(v, (list, dict)):
            return v

        # Si c'est une string (depuis le .env), on parse
        if isinstance(v, str):
            # Nettoyage préventif des guillemets simples autour de la string (au cas où python-dotenv les garderait)
            v = v.strip().strip("'")
            try:
                return json.loads(v)
            except json.JSONDecodeError as e:
                print(f"Erreur de parsing JSON pour {info.field_name} dans le .env : {e}")
                return [] if info.field_name == "hosts_config" else {}
        return v

settings = Settings()