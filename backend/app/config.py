from pydantic_settings import BaseSettings
from cryptography.fernet import Fernet
import os

class Settings(BaseSettings):
    SECRET_KEY: str = "healthcare-dss-secret-2024-xai-shap-ortools"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    DATABASE_URL: str = "sqlite:///./healthcare_dss.db"
    FERNET_KEY_FILE: str = "fernet_key.bin"

    class Config:
        env_file = ".env"
        extra = "ignore"

    def get_fernet_key(self) -> bytes:
        if os.path.exists(self.FERNET_KEY_FILE):
            with open(self.FERNET_KEY_FILE, "rb") as f:
                return f.read()
        key = Fernet.generate_key()
        with open(self.FERNET_KEY_FILE, "wb") as f:
            f.write(key)
        return key

settings = Settings()
fernet = Fernet(settings.get_fernet_key())
