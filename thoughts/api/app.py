import logging
from pathlib import Path
import subprocess
from urllib.parse import quote_plus


from diskcache import Cache
from fastapi import Depends, FastAPI, File, Form, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
import httpx
from sqlalchemy.orm import Session
from sqlmodel import select
from starlette.requests import Request
from thoughts.api.analytics import analytics_router
from thoughts.api.image_modal import image_modal
from thoughts.api.post import Post, Posts, get_session, post_router
from thoughts.api.user import try_get_current_active_user, user_router
from thoughts.config import config

logger = logging.getLogger(__name__)

cache = Cache("cache", size_limit=0.5 * (2**30))
app = FastAPI(
    title="thoughts",
    description="thoughts",
    version=config.app_version,
)
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


@app.get("/app.css", include_in_schema=False)
@app.get("/app.css/{version}", include_in_schema=False)
def get_css(request: Request):
    """Serve CSS with cache busting query param support"""
    css_path = Path(__file__).parent.parent.parent / "static" / "app.css"
    if not css_path.exists():
        # Fallback for Docker environment
        css_path = Path("/app/static/app.css")
    return FileResponse(css_path, media_type="text/css")


app.include_router(post_router)
app.include_router(user_router)
app.include_router(analytics_router)
app.add_api_route("/image-modal/", image_modal, response_class=HTMLResponse)
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
async def get(
    request: Request,
    current_user=Depends(try_get_current_active_user),
    session: Session = Depends(get_session),
    response_class=HTMLResponse,
):
    statement = select(Post).where(Post.published).order_by(Post.id.desc()).limit(10)
    posts = session.exec(statement).all()
    posts = Posts(__root__=posts)

    if isinstance(current_user, RedirectResponse):
        is_logged_in = False
    else:
        is_logged_in = True

    return config.templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "config": config,
            "current_user": current_user,
            "posts": posts,
            "md": config.md,
            "is_logged_in": is_logged_in,
            "page": 1,
            "page_size": 10,
        },
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


@app.get("/favicon.ico", response_class=FileResponse)
async def get_favicon(request: Request):
    output = "static/8bitcc.ico"
    return FileResponse(output)


@app.get("/robots.txt", response_class=FileResponse)
async def get_robots(request: Request):
    output = "static/robots.txt"
    return FileResponse(output)


@app.get("/service-worker.js", response_class=FileResponse)
async def get_robots(request: Request):
    output = "static/service-worker.js"
    return FileResponse(output)


@app.get("/manifest.json", response_class=FileResponse)
async def get_robots(request: Request):
    output = "static/manifest.json"
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


@app.get("/image-modal/", response_class=HTMLResponse)
async def image_modal(request: Request, image_url: str):
    return config.templates.TemplateResponse(
        "image_modal.html",
        {"request": request, "image_url": image_url},
    )
