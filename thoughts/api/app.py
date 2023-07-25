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


app = FastAPI()

app.include_router(post_router)
app.include_router(user_router)
app.mount("/static", StaticFiles(directory="static"), name="static")



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
