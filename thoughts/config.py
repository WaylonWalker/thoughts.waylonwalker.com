import os
from pydantic import BaseSettings, BaseModel, validator
from pathlib import Path
from sqlalchemy import create_engine
from sqlmodel import Session


class ApiServer(BaseModel):
    app: str = "thoughts.api.app:app"
    port: int = 5000
    reload: bool = True
    log_level: str = "debug"
    host: str = "0.0.0.0"
    workers: int = 1
    forwarded_allow_ips: str = '*'

class Config(BaseSettings):
    api_server: ApiServer = ApiServer()
    database_url: str = None
    root: str = None

    @validator("database_url")
    def validate_database_url(cls, v):
        if Path('/data/database.db').exists():
            return "sqlite:////data/database.db"
        else:
            return "sqlite:///database.db"

    @validator("root")
    def validate_root(cls, v):
        if v is not None:
            return v
        if 'FLY_MACHINE_ID' in os.environ:
            return "https://thoughts.waylonwalker.com"
        else:
            return 'http://localhost:5000'

class Database:
    def __init__(self, config: "Config" = None) -> None:
        self.config = config
            
        self.db_conf = {}
        if 'sqlite' in self.config.database_url:
            self.db_conf = {
                'connect_args': {"check_same_thread": False},
                'pool_recycle': 3600,
                'pool_pre_ping': True,
            }
        self._engine = create_engine(
                self.config.database_url,
                **self.db_conf
            )

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
