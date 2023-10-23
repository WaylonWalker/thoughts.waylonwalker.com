from datetime import datetime, timedelta, timezone
from typing import Annotated
from sqlalchemy.exc import NoResultFound
from thoughts.htmx import htmx
from sqlmodel import select, Session

from fastapi import APIRouter, Depends, Form, HTTPException, Header, Request, status
from fastapi.responses import RedirectResponse
from fastapi.security import (
    APIKeyCookie,
    OAuth2PasswordBearer,
    OAuth2PasswordRequestForm,
)
from fastapi.templating import Jinja2Templates
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel
from sqlmodel import select
import starlette
from starlette.responses import HTMLResponse

from thoughts.config import config, get_session
from thoughts.models.user import User, UserCreate

# to get a string like this run:
# openssl rand -hex 32
SESSION_NAME = "thoughts-session"
SECRET_KEY = "6137f641b26e5265dbde501323954d345b06dd30b174a3e3dfd6606de2207c52"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 525960

user_router = APIRouter()
cookie_sec = APIKeyCookie(name=SESSION_NAME)
# templates = Jinja2Templates(directory="templates")


UserExistsException = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="No user found",
    headers={"WWW-Authenticate": "Bearer"},
)


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    username: str | None = None


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token", auto_error=False)


def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password):
    return pwd_context.hash(password)


def get_user(username: str):
    db_session = next(get_session())
    try:
        user = db_session.exec(select(User).where(User.username == username)).one()
        return user
    except NoResultFound:
        return


NoUserFoundException = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="No user found",
    headers={"WWW-Authenticate": "Bearer"},
)

IncorrectPasswordException = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Incorrect password",
    headers={"WWW-Authenticate": "Bearer"},
)


def authenticate_user(username: str, password: str):
    user = get_user(username)

    if not user:
        raise NoUserFoundException
    if not verify_password(password, user.hashed_password):
        raise IncorrectPasswordException
    return user


def create_access_token(data: dict, expires_delta: timedelta | None = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


async def get_current_user(
    token: Annotated[str | None, Depends(oauth2_scheme)],
    session: Annotated[str | None, Depends(cookie_sec)],
):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if session is not None:
        try:
            payload = jwt.decode(session, SECRET_KEY)
            username: str = payload.get("sub")
            if username is None:
                raise credentials_exception
            token_data = TokenData(username=username)
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Invalid authentication"
            )
    else:
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            username: str = payload.get("sub")
            if username is None:
                raise credentials_exception
            token_data = TokenData(username=username)
        except JWTError:
            raise credentials_exception

    # user = authenticate_user(token_data.username, token_data.password)
    user = get_user(token_data.username)
    return user


async def get_current_active_user(
    current_user: Annotated[User, Depends(get_current_user)]
):
    if isinstance(current_user, User):
        if current_user.disabled:
            raise HTTPException(status_code=400, detail="Inactive user")
    return current_user


async def try_get_current_active_user(
    request: Request,
    hx_request: Annotated[str | None, Header()] = None,
):
    try:
        session = await cookie_sec(request)
    except starlette.exceptions.HTTPException:
        session = None
    try:
        token = await oauth2_scheme(request)
    except starlette.exceptions.HTTPException:
        token = None

    if token is None and session is None and hx_request:
        return config.templates.TemplateResponse(
            "login_form.html",
            {"request": request, "config": config, "error": "Not authenticated"},
        )
    if token is None and session is None:
        return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)

    try:
        current_user = await get_current_user(token, session)
        return await get_current_active_user(current_user)
    except HTTPException:
        return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)


@user_router.post("/token", response_model=Token)
async def login_for_access_token(
    username: Annotated[str, Form()],
    password: Annotated[str, Form()],
):
    user = authenticate_user(username, password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}


@user_router.get("/login")
async def get_login(
    request: Request,
    hx_request: Annotated[str | None, Header()] = None,
):
    if hx_request:
        return config.templates.TemplateResponse(
            "login_form.html", {"request": request, "config": config}
        )
    return config.templates.TemplateResponse(
        "login.html", {"request": request, "config": config}
    )


@user_router.get("/logout")
async def get_logout(
    request: Request,
    hx_request: Annotated[str | None, Header()] = None,
):
    if hx_request:
        response = config.templates.TemplateResponse(
            "logout_partial.html", {"request": request, "config": config}
        )
    else:
        response = config.templates.TemplateResponse(
            "logout.html", {"request": request, "config": config}
        )
    response.delete_cookie(SESSION_NAME)

    return response


@user_router.post("/login")
async def post_login(
    request: Request,
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    hx_request: Annotated[str | None, Header()] = None,
):
    try:
        user = authenticate_user(form_data.username, form_data.password)
    except HTTPException:
        return config.templates.TemplateResponse(
            "login_form.html",
            {
                "request": request,
                "config": config,
                "error": "Incorrect username or password",
            },
        )

    if not user and hx_request:
        return config.templates.TemplateResponse(
            "login_form.html",
            {"request": request, "config": config, "error": "Not authenticated"},
        )

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    response = config.templates.TemplateResponse(
        "hx_get_new_thought.html",
        {
            "request": request,
            "config": config,
        },
    )

    expires = (datetime.utcnow() + timedelta(weeks=52)).replace(tzinfo=timezone.utc)
    response.set_cookie(SESSION_NAME, access_token, expires=expires)
    return response


@user_router.get("/signup")
@htmx(template="signup")
async def get_signup(
    request: Request,
):
    return {}


@user_router.post("/signup")
async def post_signup(
    request: Request,
    user: UserCreate = Depends(UserCreate.as_form),
    # form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    # form_data: Annotated[UserCreate, Depends()],
    session: Session = Depends(get_session),
    hx_request: Annotated[str | None, Header()] = None,
):
    db_user = User.from_orm(user)
    existing = session.exec(select(User).where(User.username == user.username)).first()
    existing_email = session.exec(select(User).where(User.email == user.email)).first()

    if (existing is not None or existing_email is not None) and hx_request:
        return config.templates.TemplateResponse(
            "signup_partial.html",
            {"request": request, "config": config, "error": "username already exists"},
        )
    if existing is not None or existing_email is not None:
        return config.templates.TemplateResponse(
            "signup.html",
            {"request": request, "config": config, "error": "username already exists"},
        )
    session.add(db_user)
    session.commit()
    session.refresh(db_user)

    if not user and hx_request:
        return config.templates.TemplateResponse(
            "login_form.html",
            {"request": request, "config": config, "error": "Not authenticated"},
        )

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    response = config.templates.TemplateResponse(
        "hx_get_new_thought.html",
        {
            "request": request,
            "config": config,
        },
    )

    expires = (datetime.utcnow() + timedelta(weeks=52)).replace(tzinfo=timezone.utc)
    response.set_cookie(SESSION_NAME, access_token, expires=expires)
    return response


@user_router.get("/users/me/", response_model=User)
async def read_users_me(
    current_user: Annotated[User, Depends(try_get_current_active_user)]
):
    if isinstance(current_user, User):
        return HTMLResponse(f"<p>{current_user.username}</p>")
    return current_user


@user_router.get("/users/me/new-thought/", response_class=HTMLResponse)
async def get_new_thought(
    request: Request,
    current_user: Annotated[User, Depends(try_get_current_active_user)],
    hx_request: Annotated[str | None, Header()] = None,
):
    if isinstance(current_user, User):
        return config.templates.TemplateResponse(
            "new_thought.html",
            {"request": request, "config": config, "current_user": current_user},
        )
    if hx_request:
        return config.templates.TemplateResponse(
            "login_form.html", {"request": request, "config": config}
        )
    return current_user


@user_router.get("/users/hash/", response_model=str)
async def hash(password: str):
    return get_password_hash(password)


@user_router.get("/users/me/items/")
async def read_own_items(
    current_user: Annotated[User, Depends(get_current_active_user)]
):
    return [{"item_id": "Foo", "owner": current_user.username}]
