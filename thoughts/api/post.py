import asyncio
import random
from rich.console import Console
from typing import Annotated, Optional
import urllib.parse

from fastapi import APIRouter, Depends, Form, HTTPException, Header, Request
from fastapi.responses import HTMLResponse, PlainTextResponse, RedirectResponse
import httpx
from pydantic import BaseModel
from sqlite_utils import Database
from sqlmodel import Session, select
from sse_starlette.sse import EventSourceResponse

from thoughts.api.user import User, try_get_current_active_user
from thoughts.config import config, get_session
from thoughts.htmx import htmx
from thoughts.models.post import Post, PostCreate, PostRead, PostUpdate, Posts

console = Console()

COPY_ICON = '<img src="static/copy.svg" alt="Copy to clipboard">'
HELP_ICON = '<svg height="92px" id="Capa_1" style="enable-background:new 0 0 91.999 92;" version="1.1" viewBox="0 0 91.999 92" width="91.999px" xml:space="preserve" xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink"><path d="M45.385,0.004C19.982,0.344-0.334,21.215,0.004,46.619c0.34,25.393,21.209,45.715,46.611,45.377  c25.398-0.342,45.718-21.213,45.38-46.615C91.655,19.986,70.785-0.335,45.385,0.004z M45.249,74l-0.254-0.004  c-3.912-0.116-6.67-2.998-6.559-6.852c0.109-3.788,2.934-6.538,6.717-6.538l0.227,0.004c4.021,0.119,6.748,2.972,6.635,6.937  C51.903,71.346,49.122,74,45.249,74z M61.704,41.341c-0.92,1.307-2.943,2.93-5.492,4.916l-2.807,1.938  c-1.541,1.198-2.471,2.325-2.82,3.434c-0.275,0.873-0.41,1.104-0.434,2.88l-0.004,0.451H39.429l0.031-0.907  c0.131-3.728,0.223-5.921,1.768-7.733c2.424-2.846,7.771-6.289,7.998-6.435c0.766-0.577,1.412-1.234,1.893-1.936  c1.125-1.551,1.623-2.772,1.623-3.972c0-1.665-0.494-3.205-1.471-4.576c-0.939-1.323-2.723-1.993-5.303-1.993  c-2.559,0-4.311,0.812-5.359,2.478c-1.078,1.713-1.623,3.512-1.623,5.35v0.457H27.935l0.02-0.477  c0.285-6.769,2.701-11.643,7.178-14.487C37.946,18.918,41.446,18,45.53,18c5.346,0,9.859,1.299,13.412,3.861  c3.6,2.596,5.426,6.484,5.426,11.556C64.368,36.254,63.472,38.919,61.704,41.341z"/><g/><g/><g/><g/><g/><g/><g/><g/><g/><g/><g/><g/><g/><g/><g/></svg>'

post_router = APIRouter()


@post_router.on_event("startup")
async def on_startup() -> None:
    # SQLModel.metadata.create_all(get_config().database.engine)
    ...


@post_router.get("/stream")
async def stream(request: Request):
    def new_message():
        if random.randint(0, 1):
            return "another message"

    async def event_generator():
        while True:
            if await request.is_disconnected():
                break
            if message := new_message():
                yield "message"
            await asyncio.sleep(0.2)

    return EventSourceResponse(event_generator())


@post_router.get("/postmd/{post_id}", response_class=PlainTextResponse)
async def get_post(
    *,
    request: Request,
    session: Session = Depends(get_session),
    post_id: int,
    current_user: Annotated[User, Depends(try_get_current_active_user)],
) -> str:
    "get one post"
    post = session.get(Post, post_id)
    if isinstance(current_user, RedirectResponse):
        is_logged_in = False
    else:
        is_logged_in = True
    if not post:
        # Get the highest and lowest post IDs
        highest = session.exec(select(Post).order_by(Post.id.desc()).limit(1)).first()
        lowest = session.exec(select(Post).order_by(Post.id.asc()).limit(1)).first()

        if highest and post_id > highest.id:
            # If requested ID is too high, redirect to first post
            return RedirectResponse(url=f"/post/{lowest.id}", status_code=302)
        raise HTTPException(status_code=404, detail="Post not found")
    return str(post.message)


@post_router.get("/post/{post_id}", response_class=HTMLResponse)
async def get_post(
    *,
    request: Request,
    session: Session = Depends(get_session),
    post_id: int,
    current_user: Annotated[User, Depends(try_get_current_active_user)],
    hx_request: Annotated[str | None, Header()] = None,
) -> PostRead:
    "get one post"
    post = session.get(Post, post_id)
    if isinstance(current_user, RedirectResponse):
        is_logged_in = False
    else:
        is_logged_in = True
    if not post:
        # Get the highest and lowest post IDs
        highest = session.exec(select(Post).order_by(Post.id.desc()).limit(1)).first()
        lowest = session.exec(select(Post).order_by(Post.id.asc()).limit(1)).first()

        if highest and post_id > highest.id:
            # If requested ID is too high, redirect to first post
            return RedirectResponse(url=f"/post/{lowest.id}", status_code=302)
        raise HTTPException(status_code=404, detail="Post not found")

    # Get lowest and highest post IDs for navigation
    lowest = session.exec(select(Post).order_by(Post.id.asc()).limit(1)).first()
    highest = session.exec(select(Post).order_by(Post.id.desc()).limit(1)).first()
    lowest_id = lowest.id if lowest else post_id
    highest_id = highest.id if highest else post_id

    if hx_request:
        return config.templates.TemplateResponse(
            "post_item.html",
            {
                "request": request,
                "config": config,
                "post": post,
                "md": config.md,
                "is_logged_in": is_logged_in,
                "current_user": current_user,
                "plain": False,
                "shot_url": str(request.url).replace("/post/", "/plain_post/", 1),
            },
        )
    return config.templates.TemplateResponse(
        "post.html",
        {
            "request": request,
            "config": config,
            "post": post,
            "md": config.md,
            "is_logged_in": is_logged_in,
            "lowest_post_id": lowest_id,
            "highest_post_id": highest_id,
            "current_user": current_user,
            "plain": False,
            "shot_url": str(request.url).replace("/post/", "/post-og/", 1),
        },
    )


@post_router.get("/post-og/{post_id}", response_class=HTMLResponse)
async def get_post(
    *,
    request: Request,
    session: Session = Depends(get_session),
    post_id: int,
    current_user: Annotated[User, Depends(try_get_current_active_user)],
    hx_request: Annotated[str | None, Header()] = None,
) -> PostRead:
    "get one post"
    post = session.get(Post, post_id)
    if isinstance(current_user, RedirectResponse):
        is_logged_in = False
    else:
        is_logged_in = True
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")

    return config.templates.TemplateResponse(
        "post-og.html",
        {
            "request": request,
            "config": config,
            "post": post,
            "md": config.md,
            "is_logged_in": is_logged_in,
            "current_user": current_user,
            "plain": False,
            "shot_url": str(request.url).replace("/post/", "/post-og/", 1),
        },
    )


@post_router.get("/link/")
async def get_post_by_link(
    *,
    session: Session = Depends(get_session),
    link: str,
) -> PostRead:
    "get one post by link"
    link = urllib.parse.unquote(link)
    post = session.exec(select(Post).where(Post.link == link)).first()
    if not post:
        raise HTTPException(status_code=404, detail=f"Post not found for link: {link}")

    return post


@post_router.post("/post/")
async def post_post(
    request: Request,
    post: PostCreate,
    current_user: Annotated[User, Depends(try_get_current_active_user)],
    session: Session = Depends(get_session),
    hx_request: Annotated[str | None, Header()] = None,
) -> PostRead:
    "create a post"
    if isinstance(current_user, RedirectResponse):
        is_logged_in = False
    else:
        is_logged_in = True
    post.author_id = current_user.id
    db_post = Post.from_orm(post)
    session.add(db_post)
    session.commit()
    session.refresh(db_post)
    if hx_request:
        return config.templates.TemplateResponse(
            "post_item.html",
            {
                "request": request,
                "config": config,
                "post": db_post,
                "md": config.md,
                "is_logged_in": is_logged_in,
                "current_user": current_user,
            },
        )
    # config.mastodon.toot(f"https://thoughts.waylonwalker.com/post/{db_post['id']}")
    return db_post


# @post_router.post("/post/html/", response_class=HTMLResponse)
# async def post_post(
#     request: Request,
#     title: Annotated[str, Form()],
#     link: Annotated[str, Form()],
#     tags: Annotated[str, Form()],
#     message: Annotated[str, Form()],
#     current_user: Annotated[User, Depends(try_get_current_active_user)],
#     session: Session = Depends(get_session),
# ) -> PostRead:
#     "create a post"
#     post = PostCreate(title=title, link=link, tags=tags, message=message)
#     db_post = Post.from_orm(post)
#     session.add(db_post)
#     session.commit()
#     session.refresh(db_post)
#     return templates.TemplateResponse("post_item.html", {"request": request, "config": config, "post": db_post})


@post_router.get("/edit-thought/{post_id}", response_class=HTMLResponse)
async def edit_thought(
    *,
    request: Request,
    current_user: Annotated[User, Depends(try_get_current_active_user)],
    post_id: int,
    session: Session = Depends(get_session),
):
    if isinstance(current_user, RedirectResponse):
        return current_user
    else:
        is_logged_in = True

    post = session.get(Post, post_id)

    if current_user != post.author:
        return config.templates.TemplateResponse(
            "post_item.html",
            {
                "request": request,
                "config": config,
                "post": post,
                "error": "Not Authorized to edit this post",
            },
        )

    if not post:
        raise HTTPException(status_code=404, detail="Post not found")

    return config.templates.TemplateResponse(
        "edit_thought.html",
        {
            "request": request,
            "config": config,
            "current_user": current_user,
            "post": post,
            "post_id": post_id,
            "md": config.md,
            "is_logged_in": is_logged_in,
        },
    )


@post_router.patch("/post/")
async def patch_post(
    *,
    request: Request,
    post: PostUpdate,
    current_user: Annotated[User, Depends(try_get_current_active_user)],
    session: Session = Depends(get_session),
) -> PostRead:
    "update a post"
    if isinstance(current_user, RedirectResponse):
        return current_user
    else:
        is_logged_in = True
    db_post = session.get(Post, post.id)

    if current_user != db_post.author:
        return config.templates.TemplateResponse(
            "post_item.html",
            {
                "request": request,
                "config": config,
                "post": post,
                "error": "Not Authorized to edit this post",
            },
        )

    if not db_post:
        raise HTTPException(status_code=404, detail="Post not found")
    for key, value in post.dict(exclude_unset=True).items():
        setattr(db_post, key, value)
    session.add(db_post)
    session.commit()
    session.refresh(db_post)

    return config.templates.TemplateResponse(
        "post_item.html",
        {
            "request": request,
            "config": config,
            "current_user": current_user,
            "post": post,
            "md": config.md,
            "is_logged_in": is_logged_in,
            "current_user": current_user,
        },
    )


@post_router.patch("/post/html/", response_class=HTMLResponse)
async def patch_post_html(
    request: Request,
    id: Annotated[int, Form()],
    title: Annotated[str, Form()],
    link: Annotated[str, Form()],
    tags: Annotated[str, Form()],
    message: Annotated[str, Form()],
    current_user: Annotated[User, Depends(try_get_current_active_user)],
    session: Session = Depends(get_session),
) -> PostRead:
    "update a post"
    db_post = session.get(Post, id)
    if isinstance(current_user, RedirectResponse):
        return current_user
    else:
        is_logged_in = True

    if current_user != db_post.author:
        return config.templates.TemplateResponse(
            "post_item.html",
            {
                "request": request,
                "config": config,
                "post": db_post,
                "error": "Not Authorized to edit this post",
            },
        )
    db_post.title = title
    db_post.link = link
    db_post.tags = tags
    db_post.message = message
    session.add(db_post)
    session.commit()
    session.refresh(db_post)

    return config.templates.TemplateResponse(
        "post_item.html",
        {
            "request": request,
            "config": config,
            "current_user": current_user,
            "post": db_post,
            "md": config.md,
            "is_logged_in": is_logged_in,
            "current_user": current_user,
        },
    )


@post_router.delete("/post/{post_id}", response_class=HTMLResponse)
async def delete_post(
    *,
    request: Request,
    post_id: int,
    current_user: Annotated[User, Depends(try_get_current_active_user)],
    session: Session = Depends(get_session),
):
    "delete a post"

    if isinstance(current_user, RedirectResponse):
        return current_user

    db_post = session.get(Post, post_id)
    if not db_post:
        raise HTTPException(status_code=404, detail="Post not found")

    if current_user != db_post.author:
        return config.templates.TemplateResponse(
            "post_item.html",
            {
                "request": request,
                "config": config,
                "post": db_post,
                "error": "Not Authorized to edit this post",
                "current_user": current_user,
            },
        )

    db_post.published = False

    session.add(db_post)
    session.commit()
    session.refresh(db_post)

    return config.templates.TemplateResponse(
        "delete_post_item.html",
        {
            "request": request,
            "config": config,
            "post": db_post,
            "current_user": current_user,
        },
    )


@post_router.post("/undo/{post_id}", response_class=HTMLResponse)
async def undo_delete_post(
    *,
    request: Request,
    post_id: int,
    current_user: Annotated[User, Depends(try_get_current_active_user)],
    session: Session = Depends(get_session),
):
    "delete a post"

    if isinstance(current_user, RedirectResponse):
        return current_user
    else:
        is_logged_in = True

    db_post = session.get(Post, post_id)
    if not db_post:
        raise HTTPException(status_code=404, detail="Post not found")

    db_post.published = True

    session.add(db_post)
    session.commit()
    session.refresh(db_post)

    return config.templates.TemplateResponse(
        "post_item.html",
        {
            "request": request,
            "config": config,
            "post": db_post,
            "md": config.md,
            "is_logged_in": is_logged_in,
            "current_user": current_user,
        },
    )


@post_router.get("/posts/")
async def get_posts(
    *,
    request: Request,
    session: Session = Depends(get_session),
    hx_request: Annotated[str | None, Header()] = None,
    accept: Annotated[str | None, Header()] = None,
    current_user: Annotated[User, Depends(try_get_current_active_user)],
    page_size: int = 10,
    page: int = 1,
):
    "get all posts"
    statement = (
        select(Post)
        .where(Post.published)
        .order_by(Post.id.desc())
        .limit(page_size)
        .offset((page - 1) * page_size)
    )
    posts = session.exec(statement).all()
    posts = Posts(__root__=posts)

    if isinstance(current_user, RedirectResponse):
        is_logged_in = False
    else:
        is_logged_in = True

    if hx_request and page == 1 and len(posts.__root__) == 0:
        return HTMLResponse(
            '<ul id="posts" class="flex-grow container m-auto max-w-4xl flex flex-col min-h-[100vh]"><li class="p-4 text-center text-zinc-500 flex-grow flex items-start justify-center">No posts</li></ul>'
        )
    if hx_request and len(posts.__root__) == 0:
        return HTMLResponse("")
    if not hx_request and len(posts.__root__) == 0:
        return ["no posts"]
    if hx_request:
        return config.templates.TemplateResponse(
            "posts.html",
            {
                "request": request,
                "config": config,
                "posts": posts,
                "md": config.md,
                "is_logged_in": is_logged_in,
                "page_size": page_size,
                "page": page,
                "current_user": current_user,
            },
        )


@post_router.get("/posts/{username}/")
async def get_posts_by_user(
    *,
    request: Request,
    username: str,
    session: Session = Depends(get_session),
    hx_request: Annotated[str | None, Header()] = None,
    accept: Annotated[str | None, Header()] = None,
    current_user: Annotated[User, Depends(try_get_current_active_user)],
    page_size: int = 10,
    page: int = 1,
) -> Posts:
    "get all posts"
    user = session.exec(select(User).where(User.username == username)).one()
    statement = (
        select(Post)
        .where(Post.published)
        .where(Post.author == user)
        .order_by(Post.id.desc())
        .limit(page_size)
        .offset((page - 1) * page_size)
    )
    posts = session.exec(statement).all()
    posts = Posts(__root__=posts)

    if isinstance(current_user, RedirectResponse):
        is_logged_in = False
    else:
        is_logged_in = True

    if hx_request and page == 1 and len(posts.__root__) == 0:
        return HTMLResponse(
            '<ul id="posts" class="flex-grow container m-auto max-w-4xl flex flex-col min-h-[100vh]"><li class="p-4 text-center text-zinc-500 flex-grow flex items-start justify-center">No posts</li></ul>'
        )
    if hx_request and len(posts.__root__) == 0:
        return HTMLResponse("")
    if not hx_request and len(posts.__root__) == 0:
        return ["no posts"]
    if hx_request:
        return config.templates.TemplateResponse(
            "posts.html",
            {
                "request": request,
                "config": config,
                "posts": posts,
                "md": config.md,
                "is_logged_in": is_logged_in,
                "page_size": page_size,
                "page": page,
                "current_user": current_user,
                "username": username,
            },
        )

    if accept.startswith("text/html"):
        return config.templates.TemplateResponse(
            "base.html",
            {
                "request": request,
                "config": config,
                "posts": posts,
                "md": config.md,
                "is_logged_in": is_logged_in,
                "page_size": page_size,
                "page": page,
                "username": username,
            },
        )

    return posts


@post_router.post("/search/")
async def search_posts(
    *,
    search: Optional[str] = Form(""),
    request: Request,
    session: Session = Depends(get_session),
    hx_request: Annotated[str | None, Header()] = None,
    accept: Annotated[str | None, Header()] = None,
    current_user: Annotated[User, Depends(try_get_current_active_user)],
) -> Posts:
    "get all posts"
    page_size = 999999
    page = 1

    if search.strip() == "" or search is None:
        statement = (
            select(Post).where(Post.published).order_by(Post.id.desc())
            # .limit(page_size)
            # .offset((page - 1) * page_size)
        )
        posts = session.exec(statement).all()

    else:
        try:
            db = Database(config.database_url.split(":///")[-1])
            posts = list(db["post"].search(search))
        except AssertionError:
            db = Database(config.database_url.split(":///")[-1])
            db["post"].enable_fts(
                ["title", "message", "tags"], create_triggers=True, tokenize="trigram"
            )
            posts = list(db["post"].search(search))
        for post in posts:
            post["author"] = session.get(User, post["author_id"])

    posts = Posts(__root__=posts)

    if isinstance(current_user, RedirectResponse):
        is_logged_in = False
    else:
        is_logged_in = True

    if hx_request and page == 1 and len(posts.__root__) == 0:
        return HTMLResponse(
            '<ul id="posts" class="flex-grow container m-auto max-w-4xl flex flex-col min-h-[100vh]"><li class="p-4 text-center text-zinc-500 flex-grow flex items-start justify-center">No posts</li></ul>'
        )
    if hx_request and len(posts.__root__) == 0:
        return HTMLResponse("")
    if not hx_request and len(posts.__root__) == 0:
        return ["no posts"]
    if hx_request:
        return config.templates.TemplateResponse(
            "posts.html",
            {
                "request": request,
                "config": config,
                "posts": posts,
                "md": config.md,
                "is_logged_in": is_logged_in,
                "page_size": page_size,
                "page": page,
                "current_user": current_user,
            },
        )

    if accept.startswith("text/html"):
        return config.templates.TemplateResponse(
            "base.html",
            {
                "request": request,
                "config": config,
                "posts": posts,
                "md": config.md,
                "is_logged_in": is_logged_in,
                "current_user": current_user,
                "page_size": page_size,
                "page": page,
            },
        )

    return posts


class Test(BaseModel):
    value: Optional[str] = "the value"
    title: Optional[str] = "the title"


@post_router.get("/headers/")
@htmx
async def get_headers(request: Request):
    "get all headers"
    # return Test(value="test")
    headers = [f"<li>{key}: {value}</li>" for key, value in request.headers.items()]
    body = '<ul id="headers">headers</ul>'
    return HTMLResponse(body)


@post_router.get("/new-thought/", response_class=HTMLResponse)
async def get_new_thought_modal(
    *,
    request: Request,
    current_user: Annotated[User | None, Depends(try_get_current_active_user)],
    hx_request: Annotated[str | None, Header()] = None,
):
    """Get the new thought modal"""
    if current_user is None:
        return config.templates.TemplateResponse(
            "login_form.html",
            {
                "request": request,
                "config": config,
                "error": "Please log in to create a new thought",
            },
        )

    return config.templates.TemplateResponse(
        "new_thought_modal.html",
        {
            "request": request,
            "config": config,
            "current_user": current_user,
        },
    )


@post_router.get("/fetch-title/", response_class=HTMLResponse)
async def fetch_title(
    *,
    request: Request,
    url: str,
    current_user: Annotated[User | None, Depends(try_get_current_active_user)],
):
    """Fetch the title of a webpage"""
    if current_user is None:
        return config.templates.TemplateResponse(
            "login_form.html",
            {
                "request": request,
                "config": config,
                "error": "Please log in to fetch titles",
            },
        )

    if not url.startswith(("http://", "https://")):
        return """<input class="w-full rounded-lg border border-black bg-zinc-950 p-3 focus:bg-zinc-900"
                        type="text" id="title" name="title" required />"""

    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        async with httpx.AsyncClient(timeout=5.0, follow_redirects=True) as client:
            response = await client.get(url, headers=headers)
            response.raise_for_status()

            # Use BeautifulSoup to parse the HTML and extract the title
            from bs4 import BeautifulSoup

            soup = BeautifulSoup(response.text, "html.parser")
            title = soup.title.string if soup.title else None

            if title:
                print(f"Found title: {title.strip()}")
                return f"""<input class="w-full rounded-lg border border-black bg-zinc-950 p-3 focus:bg-zinc-900"
                               type="text" id="title" name="title" required value="{title.strip()}" />"""
            else:
                print(f"No title found for URL: {url}")
                return """<input class="w-full rounded-lg border border-black bg-zinc-950 p-3 focus:bg-zinc-900"
                               type="text" id="title" name="title" required />"""
    except Exception as e:
        print(f"Error fetching title: {str(e)}")
        return """<input class="w-full rounded-lg border border-black bg-zinc-950 p-3 focus:bg-zinc-900"
                        type="text" id="title" name="title" required />"""
