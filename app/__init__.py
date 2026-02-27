from pathlib import Path

import pendulum
from dotenv import load_dotenv

from app.settings import Settings

env_files = [".env", ".env.dev", ".env.local", ".env.prod"]


def load_env_files():
    root_dir = Path(__file__).parent.parent
    for env in env_files:
        f = root_dir / env
        if f.exists():
            load_dotenv(dotenv_path=f, override=False)


load_env_files()

settings = Settings()

pendulum.set_local_timezone(pendulum.timezone(settings.default_timezone))
