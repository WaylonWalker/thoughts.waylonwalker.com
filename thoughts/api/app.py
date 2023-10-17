import logging
import hashlib
import tempfile
from pathlib import Path
import subprocess

from thoughts.api.user import User, try_get_current_active_user
from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from urllib.parse import quote_plus

from thoughts.api.post import post_router
from thoughts.api.user import user_router
from thoughts.config import config
import arel


app = FastAPI()

if config.env == "dev":
    hot_reload = arel.HotReload(paths=[arel.Path(".")])
    app.add_websocket_route("/hot-reload", route=hot_reload, name="hot-reload")
    app.add_event_handler("startup", hot_reload.startup)
    app.add_event_handler("shutdown", hot_reload.shutdown)
    config.templates.env.globals["DEBUG"] = True
    config.templates.env.globals["hot_reload"] = hot_reload
config.templates.env.filters["quote_plus"] = lambda u: quote_plus(str(u))

PROCS = {}


@app.on_event("startup")
async def start_litestream():
    if config.env == "dev":
        return
    database = config.database_url.split(":///")[-1]
    PROCS["litestream"] = subprocess.Popen(
        [
            config.litestream_cmd,
            "replicate",
            "-config",
            config.litestream_config,
        ]
    )


# on startup run tailwind if in dev mode
@app.on_event("startup")
async def start_tailwind():
    if config.env == "dev":
        PROCS["tailwind"] = subprocess.Popen(
            [
                "npx",
                "tailwindcss",
                "--input",
                "tailwind/app.css",
                "--output",
                "static/app.css",
                "--watch",
            ]
        )


@app.on_event("shutdown")
async def shutdown_event():
    for proc in PROCS.values():
        proc.kill()


app.include_router(post_router)
app.include_router(user_router)
app.mount("/static", StaticFiles(directory="static"), name="static")


class AuthStaticFiles(StaticFiles):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

    async def __call__(self, scope, receive, send) -> None:
        assert scope["type"] == "http"

        request = Request(scope, receive)
        current_user = await try_get_current_active_user(request)
        if isinstance(current_user, RedirectResponse):
            await current_user(scope, receive, send)
        else:
            await super().__call__(scope, receive, send)


app.mount(
    "/restricted",
    AuthStaticFiles(directory="restricted"),
    name="restricted",
)

logger = logging.getLogger(__name__)


@app.middleware("http")
async def log_request(request, call_next):
    logger.info("hey im in here")
    logger.info("hey im in here")
    logger.info("hey im in here")
    logger.info("hey im in here")
    logger.info(f"{request.method} {request.url}")
    response = await call_next(request)
    return response


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def get(request: Request, response_class=HTMLResponse):
    return config.templates.TemplateResponse(
        "index.html", {"request": request, "config": config}
    )


from fastapi.responses import FileResponse


@app.get("/favicon.ico", response_class=FileResponse)
async def get_favicon(request: Request):
    output = "static/8bitcc.ico"
    return FileResponse(output)


@app.get("/robots.txt", response_class=FileResponse)
async def get_robots(request: Request):
    output = "static/robots.txt"
    return FileResponse(output)


@app.get("/shot/", response_class=FileResponse)
async def get_shot(request: Request, path: str):
    output = "/tmp/" + (hashlib.md5(path.encode()).hexdigest() + ".png").lower()
    if Path(output).exists():
        return FileResponse(output)
    cmd = [
        "shot-scraper",
        path,
        "-h",
        "450",
        "-w",
        "800",
        "-o",
        output,
    ]
    proc = subprocess.Popen(cmd)
    res = proc.wait()
    return FileResponse(output)
