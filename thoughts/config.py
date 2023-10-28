import os
from pydantic import BaseSettings, BaseModel, validator
from pathlib import Path
from sqlalchemy import create_engine
from sqlmodel import Session
from markdown_it import MarkdownIt
from fastapi.templating import Jinja2Templates
from thoughts.highlight import highlight_code
from urllib.parse import quote_plus


class ApiServer(BaseModel):
    app: str = "thoughts.api.app:app"
    port: int = 5000
    reload: bool = True
    log_level: str = "debug"
    host: str = "0.0.0.0"
    workers: int = 1
    forwarded_allow_ips: str = "*"

    @validator("workers")
    def validate_workers(cls, v):
        if v is not None:
            return v
        if "FLY_MACHINE_ID" in os.environ:
            return 8
        else:
            return 1

    @validator("reload")
    def validate_reload(cls, v):
        if v is not None:
            return v
        if "FLY_MACHINE_ID" in os.environ:
            return False
        else:
            return True


def get_templates():
    templates = Jinja2Templates(directory="templates")
    templates.env.filters["quote_plus"] = lambda u: quote_plus(str(u))
    return templates


class Config(BaseSettings):
    api_server: ApiServer = ApiServer()
    database_url: str = None
    litestream_cmd: str = None
    litestream_config: str = None
    root: str = None
    templates = get_templates()
    env: str = None

    @property
    def md(self):
        return MarkdownIt(
            "gfm-like",
            {
                "linkify": True,
                "html": True,
                "typographer": True,
                "highlight": highlight_code,
            },
        )

    @validator("env")
    def validate_env(cls, v):
        if v is not None:
            return v
        if "FLY_MACHINE_ID" in os.environ:
            return "prod"
        else:
            return "dev"

    @validator("database_url")
    def validate_database_url(cls, v):
        if Path("/data/database.db").exists():
            return "sqlite:////data/database.db"
        else:
            return "sqlite:///database.db"

    @validator("litestream_config")
    def validate_litestream_config(cls, v):
        if Path("/data/litestream.yml").exists():
            return "/data/litestream.yml"
        else:
            return "litestream.yml"

    @validator("litestream_cmd")
    def validate_litestream_cmd(cls, v):
        if Path("/data/litestream").exists():
            return "/data/litestream"
        else:
            return "litestream"

    @validator("root")
    def validate_root(cls, v):
        if v is not None:
            return v
        if "FLY_MACHINE_ID" in os.environ:
            return "https://thoughts.waylonwalker.com"
        else:
            return "http://localhost:5000"


class Database:
    def __init__(self, config: "Config" = None) -> None:
        self.config = config

        self.db_conf = {}
        if "sqlite" in self.config.database_url:
            self.db_conf = {
                "connect_args": {"check_same_thread": False},
                "pool_recycle": 3600,
                "pool_pre_ping": True,
            }
        self._engine = create_engine(self.config.database_url, **self.db_conf)

    @property
    def engine(self) -> "Engine":
        return self._engine

    @property
    def session(self) -> "Session":
        return Session(self.engine)


config = Config()
database = Database(config)


def get_session() -> "Session":
    with Session(database.engine) as session:
        yield session
