
from datetime import datetime, timedelta
from typing import Annotated

from fastapi.responses import RedirectResponse
from fastapi.responses import HTMLResponse
from fastapi import APIRouter, Depends, HTTPException, status
import starlette
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel
from fastapi.security import APIKeyCookie
from starlette.responses import Response, HTMLResponse
from fastapi import  Request
from fastapi.templating import Jinja2Templates

from thoughts.config import config

# to get a string like this run:
# openssl rand -hex 32
SECRET_KEY="6137f641b26e5265dbde501323954d345b06dd30b174a3e3dfd6606de2207c52"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

user_router = APIRouter()
cookie_sec = APIKeyCookie(name="session")
templates = Jinja2Templates(directory="templates")

fake_users_db = {
    "waylonwalker": {
        "username": "waylonwalker",
        "full_name": "Waylon Walker",
        "email": "waylon@waylonwalker.com",
        "hashed_password": "$2b$12$fph57TJ1UrGU/wAaRVXOWulG/7nOwCn89B9z3wOPCqb7O6uAoZSHC",
        "disabled": False,
    }
}


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    username: str | None = None


class User(BaseModel):
    username: str
    email: str | None = None
    full_name: str | None = None
    disabled: bool | None = None


class UserInDB(User):
    hashed_password: str


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token", auto_error=False)


def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password):
    return pwd_context.hash(password)


def get_user(db, username: str):
    if username in db:
        user_dict = db[username]
        return UserInDB(**user_dict)


def authenticate_user(fake_db, username: str, password: str):
    user = get_user(fake_db, username)
    if not user:
        return False
    if not verify_password(password, user.hashed_password):
        return False
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
    print(session)
    print(token)
    if session is not None:
        try:
            payload = jwt.decode(session, SECRET_KEY)
            username: str = payload.get("sub")
            if username is None:
                print('username is none')
                # return RedirectResponse(url="/login")
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
                # return RedirectResponse(url="/login")
                raise credentials_exception
            token_data = TokenData(username=username)
        except JWTError:
            # return RedirectResponse(url="/login")
            raise credentials_exception
    user = get_user(fake_users_db, username=token_data.username)
    if user is None:
        # return RedirectResponse(url="/login")
        raise credentials_exception
    return user


async def get_current_active_user(
    current_user: Annotated[User, Depends(get_current_user)]
):
    if isinstance(current_user, User):
        if current_user.disabled:
            raise HTTPException(status_code=400, detail="Inactive user")
    return current_user

async def try_get_current_active_user(
        # token: Annotated[str | None, Depends(oauth2_scheme)],
        request: Request,
        # session: Annotated[str | None, Depends(cookie_sec)],
        # token, session
    ):
    print(f'request: {request}')
    print('getting session')
    try:
        session = await cookie_sec(request)
    except starlette.exceptions.HTTPException:
        session = None
    print('getting token')
    try:
        token = await oauth2_scheme(request)
    except starlette.exceptions.HTTPException:
        token = None
    print('try_get_current_active_user')
    print(f'token: {token}')
    print(f'session: {session}')

    if token is None and session is None:
        print('user not logged in')
        return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)

    try:
        current_user = await get_current_user(token, session)
        return await get_current_active_user(current_user)
    except HTTPException:
        print('failed to get current active user')
        return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)


@user_router.post("/token", response_model=Token)
async def login_for_access_token(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()]
):
    user = authenticate_user(fake_users_db, form_data.username, form_data.password)
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

html = f'''
    <div id="loginwrapper">
        <h1>login</h1>
        <form class='login' /hx-post="{ config.root }/login/" hx-target="#loginwrapper" method="POST" name="login">
            <label for="username">Username:</label>
            <input type="text" id="username" name="username">
            <label for="password">Password:</label>
            <input type="password" id="password" name="password">
            <input type="submit" value="Login">
        </form>
    </div>
'''
@user_router.get("/login")
async def get_login():
    return HTMLResponse(html)

logouthtml = '''
<h1>goodbye</h1>
<script>
localStorage.removeItem("access_token")
</script>
'''
@user_router.get("/logout")
async def get_logout():
    response = HTMLResponse(content=logouthtml)
    response.delete_cookie("session")
    return response

htmluser = f'''
<!DOCTYPE html>
    <head>
        <title>thoughts login</title>
    </head>
    <body>
        <div hx-get='{ config.root }/users/me/new-thought/' hx-trigger='load'>
        Welcome {'{{ user }}'}
        </div>
        <div id="user" data-token="{'{{ token }}'}"></div>
    </body>
</html>
'''
@user_router.post("/login")
async def post_login(
    response: Response,
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()]
        ):
    user = authenticate_user(fake_users_db, form_data.username, form_data.password)
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
    response = HTMLResponse(content=htmluser.replace('{{ user }}', user.username).replace('{{ token }}', access_token))
    response.set_cookie('session', access_token)
    return response

@user_router.get("/users/me/", response_model=User)
async def read_users_me(
    current_user: Annotated[User, Depends(try_get_current_active_user)]
):
    if isinstance(current_user, RedirectResponse):
        return current_user
    return HTMLResponse(f'<p>{current_user.username}</p>')

@user_router.get("/users/me/new-thought/", response_class=HTMLResponse)
async def get_new_thought(
    request: Request,
    current_user: Annotated[User, Depends(try_get_current_active_user)]
):
    if isinstance(current_user, RedirectResponse):
        return current_user
    return templates.TemplateResponse("new_thought.html", {"request": request, "config": config, "current_user": current_user })

@user_router.get("/users/hash/", response_model=str)
async def hash(password: str):
    return get_password_hash(password)


@user_router.get("/users/me/items/")
async def read_own_items(
    current_user: Annotated[User, Depends(get_current_active_user)]
):
    return [{"item_id": "Foo", "owner": current_user.username}]
