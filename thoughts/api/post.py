from typing import Annotated, Optional
from fastapi.responses import RedirectResponse
from fastapi.responses import HTMLResponse
import urllib.parse
from fastapi import APIRouter, Depends, HTTPException, Form
from sqlmodel import Session, select
from fastapi import Request
from fastapi.templating import Jinja2Templates

from thoughts.config import get_session
from thoughts.models.post import Post, PostCreate, PostRead, PostUpdate, Posts
from thoughts.api.user import try_get_current_active_user, User
from thoughts.config import config

post_router = APIRouter()
templates = Jinja2Templates(directory="templates")


@post_router.on_event("startup")
async def on_startup() -> None:
    # SQLModel.metadata.create_all(get_config().database.engine)
    ...


@post_router.get("/post/{post_id}", response_class=HTMLResponse)
async def get_post(
    *,
    request: Request,
    session: Session = Depends(get_session),
    post_id: int,
) -> PostRead:
    "get one post"
    post = session.get(Post, post_id)
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    return templates.TemplateResponse("post_item.html", {"request": request, "config": config, "post": post})


@post_router.get("/link/")
async def get_post_by_link(
    *,
    session: Session = Depends(get_session),
    link: str,
) -> PostRead:
    "get one post by link"
    link = urllib.parse.unquote(link)
    post = session.exec(select(Post).where(Post.link==link)).first()
    if not post:
        raise HTTPException(status_code=404, detail=f"Post not found for link: {link}")

    return post


@post_router.post("/post/")
async def post_post(
    post: Annotated[PostCreate, Form()],
    current_user: Annotated[User, Depends(try_get_current_active_user)],
    session: Session = Depends(get_session),
) -> PostRead:
    "create a post"
    db_post = Post.from_orm(post)
    session.add(db_post)
    session.commit()
    session.refresh(db_post)
    return db_post

@post_router.post("/post/html/", response_class=HTMLResponse)
async def post_post(
    request: Request,
    title: Annotated[str, Form()],
    link: Annotated[str, Form()],
    tags: Annotated[str, Form()],
    message: Annotated[str, Form()],
    current_user: Annotated[User, Depends(try_get_current_active_user)],
    session: Session = Depends(get_session),
) -> PostRead:
    "create a post"
    post = PostCreate(title=title, link=link, tags=tags, message=message)
    db_post = Post.from_orm(post)
    session.add(db_post)
    session.commit()
    session.refresh(db_post)
    return templates.TemplateResponse("post_item.html", {"request": request, "config": config, "post": db_post})

@post_router.get("/edit-thought/{post_id}", response_class=HTMLResponse)
async def edit_thought(
        *,
    request: Request,
    current_user: Annotated[User, Depends(try_get_current_active_user)],
    post_id: int,
    session: Session = Depends(get_session),
):
    print('here')
    if isinstance(current_user, RedirectResponse):
        return current_user
    post = session.get(Post, post_id)
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    return templates.TemplateResponse("edit_thought.html", {"request": request, "config": config, "current_user": current_user, "post": post, "post_id":post_id})


@post_router.patch("/post/")
async def patch_post(
    *,
    post: PostUpdate,
    current_user: Annotated[User, Depends(try_get_current_active_user)],
    session: Session = Depends(get_session),
) -> PostRead:
    "update a post"
    db_post = session.get(Post, post.id)
    if not db_post:
        raise HTTPException(status_code=404, detail="Post not found")
    for key, value in post.dict(exclude_unset=True).items():
        setattr(db_post, key, value)
    session.add(db_post)
    session.commit()
    session.refresh(db_post)
    return templates.TemplateResponse("post_item.html", {"request": request, "config": config, "post": db_post})

@post_router.patch("/post/html/", response_class=HTMLResponse)
async def patch_post(
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
    db_post.title = title
    db_post.link = link
    db_post.tags = tags
    db_post.message = message
    session.add(db_post)
    session.commit()
    session.refresh(db_post)
    return templates.TemplateResponse("post_item.html", {"request": request, "config": config, "post": db_post})


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

    db_post.published = False

    session.add(db_post)
    session.commit()
    session.refresh(db_post)

    return templates.TemplateResponse("delete_post_item.html", {"request": request, "config": config, "post": db_post})

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

    db_post = session.get(Post, post_id)
    if not db_post:
        raise HTTPException(status_code=404, detail="Post not found")

    db_post.published = True

    session.add(db_post)
    session.commit()
    session.refresh(db_post)

    return templates.TemplateResponse("post_item.html", {"request": request, "config": config, "post": db_post})



@post_router.get("/posts/")
async def get_posts(
    *,
    session: Session = Depends(get_session),
) -> Posts:
    "get all posts"
    statement = select(Post).where(Post.published)
    posts = session.exec(statement).all()
    posts.reverse()
    return Posts(__root__=posts)

@post_router.get("/posts/html/", response_class=HTMLResponse)
async def get_posts(
    *,
    request: Request,
    session: Session = Depends(get_session),
) -> Posts:
    "get all posts"
    statement = select(Post).where(Post.published)
    posts = session.exec(statement).all()
    if len(posts) == 0:
        return HTMLResponse('<ul id="posts"><li>No posts</li></ul>')
    posts.reverse()
    posts = Posts(__root__=posts)
    return templates.TemplateResponse("posts.html", {"request": request, "config": config, "posts": posts})
