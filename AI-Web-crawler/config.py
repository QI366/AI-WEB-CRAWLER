import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


@dataclass
class Settings:
    anthropic_model: str = os.getenv("ANTHROPIC_MODEL", "claude-opus-5")
    request_timeout: float = float(os.getenv("REQUEST_TIMEOUT", "15"))
    user_agent: str = os.getenv(
        "USER_AGENT",
        "AI-Web-Crawler/0.1 (learning project; +https://github.com/)",
    )
    output_dir: str = os.getenv("OUTPUT_DIR", "data")


settings = Settings()
