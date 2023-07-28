from typing import Annotated
from fastapi.responses import RedirectResponse
from fastapi import FastAPI, Request
from fastapi import Depends
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from thoughts.api.post import post_router
from thoughts.api.user import user_router, User, get_current_active_user
from fastapi.staticfiles import StaticFiles
from thoughts.config import config
from fastapi.templating import Jinja2Templates

templates = Jinja2Templates(directory="templates")

class ASGIMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        await self.app(scope, receive, send)

class LoggedRequestBodySizeMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        # if scope["type"] != "http":
        #     await self.app(scope, receive, send)
        #     return
        from rich import print
        print('hey im in here')
        print(scope)
        print('the receive')

        # message = await receive()
        # print(message)


        body_size = 0

        async def receive_logging_request_body_size():
            print('recieving')
            print('recieving')
            print('recieving')
            print('recieving')
            print('recieving')
            print('recieving')
            nonlocal body_size

            message = await receive()
            print(message)
            assert message["type"] == "http.request"

            body_size += len(message.get("body", b""))
            print('body_size', body_size)

            if not message.get("more_body", False):
                print(f"Size of request body was: {body_size} bytes")

            return message

        await self.app(scope, receive_logging_request_body_size, send)


app = FastAPI()

app.include_router(post_router)
app.include_router(user_router)
app.mount("/static", StaticFiles(directory="static"), name="static")

import logging
logger = logging.getLogger(__name__)

@app.middleware("http")
async def log_request(request, call_next):
    logger.info('hey im in here')
    logger.info('hey im in here')
    logger.info('hey im in here')
    logger.info('hey im in here')
    logger.info(f'{request.method} {request.url}')
    response = await call_next(request)
    return response



app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def get(request: Request, response_class=HTMLResponse):
    return templates.TemplateResponse("index.html", {"request": request, "config": config})
