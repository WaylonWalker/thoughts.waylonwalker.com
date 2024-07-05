import asyncio
import base64
import hashlib
import logging
import os
import subprocess
import tempfile
from pathlib import Path
from urllib.parse import quote_plus

import httpx
from diskcache import Cache
from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import (
    HTMLResponse,
    RedirectResponse,
    Response,
    StreamingResponse,
)
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.background import BackgroundTask
from starlette.requests import Request
from starlette.responses import StreamingResponse

from thoughts.api.post import post_router
from thoughts.api.user import User, try_get_current_active_user, user_router
from thoughts.config import config

cache = Cache("cache", size_limit=0.5 * (2**30))
app = FastAPI()
httpx_client = httpx.AsyncClient(timeout=30.0)

# ACCESS_KEY = os.environ.get("ACCESS_KEY")
# SECRET_KEY = os.environ.get("SECRET_KEY")

if config.env == "dev":
    import arel

    hot_reload = arel.HotReload(
        paths=[arel.Path("static"), arel.Path("templates"), arel.Path("thoughts")]
    )
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
    litestream_lock = Path("/tmp/litestream.lock")
    if litestream_lock.exists():
        return
    litestream_lock.touch()
    PROCS["litestream"] = subprocess.Popen(
        [
            config.litestream_cmd,
            "replicate",
            "-config",
            config.litestream_config,
        ]
    )


# on startup run tailwind if in dev mode
# @app.on_event("startup")
# async def start_tailwind():
#     if config.env == "dev":
#         PROCS["tailwind"] = subprocess.Popen(
#             [
#                 "npx",
#                 "tailwindcss",
#                 "--input",
#                 "tailwind/app.css",
#                 "--output",
#                 "static/app.css",
#                 "--watch",
#             ]
#         )


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


@app.post("/share")
async def handle_share(
    title: str = Form(...),
    text: str = Form(...),
    url: str = Form(...),
    file: UploadFile = File(...),
):
    content = f"""
    <html>
    <body>
    <h1>Shared Content</h1>
    <p>Title: {title}</p>
    <p>Text: {text}</p>
    <p>URL: {url}</p>
    <img src="{await file.read()}">
    </body>
    </html>
    """
    return HTMLResponse(content=content)


from fastapi.responses import FileResponse


@app.get("/favicon.ico", response_class=FileResponse)
async def get_favicon(request: Request):
    output = "static/8bitcc.ico"
    return FileResponse(output)


@app.get("/robots.txt", response_class=FileResponse)
async def get_robots(request: Request):
    output = "static/robots.txt"
    return FileResponse(output)


# @app.get("/shot/", response_class=FileResponse)
# async def get_shot(request: Request, path: str):
#     output = "/tmp/" + (hashlib.md5(path.encode()).hexdigest() + ".png").lower()
#     if Path(output).exists():
#         return FileResponse(output)
#     cmd = [
#         "shot-scraper",
#         path,
#         "-h",
#         "450",
#         "-w",
#         "800",
#         "-o",
#         output,
#     ]
#     proc = subprocess.Popen(cmd)
#     res = proc.wait()
#     return FileResponse(output)


# @app.get("/shot/", responses={200: {"content": {"image/png": {}}}})
# async def get_shot(request: Request, path: str):
#     from minio import Minio
#     from minio.error import S3Error

#     if not path.startswith("http"):
#         raise HTTPException(status_code=404, detail="path is not a url")

#     imgname = (hashlib.md5(path.encode()).hexdigest() + ".png").lower()
#     client = Minio(
#         "sandcrawler.wayl.one",
#         access_key=ACCESS_KEY,
#         secret_key=SECRET_KEY,
#     )
#     try:
#         imgdata = cache.get(imgname)
#         if not imgdata:
#             imgdata = client.get_object("images.thoughts", imgname)
#             cache.set(imgname, imgdata)
#         return Response(
#             content=imgdata,
#             media_type="image/webp",
#             headers={"Cache-Control": "public, max-age=604800"},
#         )

#     except S3Error:
#         print("failed to get from minio, proxying from shot.wayl.one")
#         path = f"https://shot.wayl.one/shot/?path={path}"
#         req = httpx_client.build_request("GET", path)
#         r = await httpx_client.send(req, stream=False)
#         cache.set(imgname, r.content)
#         # req = httpx_client.build_request("GET", path)
#         # r = await httpx_client.send(req, stream=True)
#         return Response(
#             r.content, background=BackgroundTask(r.aclose), headers=r.headers
#         )
