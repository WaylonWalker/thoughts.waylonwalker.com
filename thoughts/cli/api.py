import typer

from thoughts.config import config
from thoughts.optional import _optional_import_

uvicorn = _optional_import_("uvicorn", group="api")
api_app = typer.Typer()


@api_app.callback()
def api(
    verbose: bool = typer.Option(
        False,
        help="show the log messages",
    ),
):
    "model cli"


@api_app.command()
def run(
    verbose: bool = typer.Option(
        False,
        help="show the log messages",
    ),
):
    uvicorn.run(**config.api_server.dict())
