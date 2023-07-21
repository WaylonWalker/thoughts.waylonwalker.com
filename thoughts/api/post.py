from typing import Annotated
from fastapi.responses import RedirectResponse
import urllib.parse
from fastapi import APIRouter, Depends, HTTPException, Form
from sqlmodel import Session, select

from thoughts.config import get_session
from thoughts.models.post import Post, PostCreate, PostRead, PostUpdate, Posts
from thoughts.api.user import get_current_active_user, User

post_router = APIRouter()


@post_router.on_event("startup")
async def on_startup() -> None:
    # SQLModel.metadata.create_all(get_config().database.engine)
    ...


@post_router.get("/post/{post_id}")
async def get_post(
    *,
    session: Session = Depends(get_session),
    post_id: int,
) -> PostRead:
    "get one post"
    post = session.get(Post, post_id)
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    return post

@post_router.get("/link/")
async def get_post_by_link(
    *,
    session: Session = Depends(get_session),
    link: str,
) -> PostRead:
    "get one post by link"
    link = urllib.parse.unquote(link)
    print(f'link: {link}')
    post = session.exec(select(Post).where(Post.link==link)).first()
    if not post:
        raise HTTPException(status_code=404, detail=f"Post not found for link: {link}")

    return post


@post_router.post("/post/")
async def post_post(
    post: PostCreate,
    current_user: Annotated[User, Depends(get_current_active_user)],
    session: Session = Depends(get_session),
) -> PostRead:
    "create a post"
    # if isinstance(current_user, RedirectResponse):
    #     raise HTTPException(
    #             status_code=status.HTTP_401_UNAUTHORIZED,
    #             detail="Could not validate credentials",
    #             headers={"WWW-Authenticate": "Bearer"},
    #         )
    db_post = Post.from_orm(post)
    session.add(db_post)
    session.commit()
    session.refresh(db_post)
    # await manager.broadcast({post.json()}, id=1)
    return db_post


@post_router.patch("/post/")
async def patch_post(
    *,
    post: PostUpdate,
    current_user: Annotated[User, Depends(get_current_active_user)],
    session: Session = Depends(get_session),
) -> PostRead:
    "update a post"
    if isinstance(current_user, RedirectResponse):
        return current_user
    db_post = session.get(Post, post.id)
    if not db_post:
        raise HTTPException(status_code=404, detail="Post not found")
    for key, value in post.dict(exclude_unset=True).items():
        setattr(db_post, key, value)
    session.add(db_post)
    session.commit()
    session.refresh(db_post)
    # await manager.broadcast({post.json()}, id=1)
    return db_post


@post_router.delete("/post/{post_id}")
async def delete_post(
    *,
    post_id: int,
    current_user: Annotated[User, Depends(get_current_active_user)],
    session: Session = Depends(get_session),
):
    "delete a post"
    if isinstance(current_user, RedirectResponse):
        return current_user
    post = session.get(Post, post_id)
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    session.delete(post)
    session.commit()
    # await manager.broadcast(f"deleted post {post_id}", id=1)
    return {"ok": True}


@post_router.get("/posts/")
async def get_posts(
    *,
    session: Session = Depends(get_session),
) -> Posts:
    "get all posts"
    statement = select(Post)
    posts = session.exec(statement).all()
    posts.reverse()
    return Posts(__root__=posts)
