from typing import List, Optional
from pydantic import validator

from pydantic import BaseModel
from sqlmodel import Field, Relationship, SQLModel
from passlib.context import CryptContext

from thoughts.optional import optional
from thoughts.as_form import as_form

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class UserBase(SQLModel, table=False):
    username: str
    full_name: str
    email: str
    disabled: bool


class User(UserBase, table=True):
    id: int = Field(default=None, primary_key=True)
    hashed_password: str
    posts: List["Post"] = Relationship(back_populates="author")


class UserPosts(BaseModel):
    posts: List["Post"] = Relationship(back_populates="author")


@as_form
class UserCreate(UserBase):
    password: str
    hashed_password: Optional[str]

    @validator("hashed_password", pre=True, always=True)
    def password_hashing(cls, v, values, **kwargs):
        if "password" in values:
            return pwd_context.hash(values["password"])
        return v

    def get_password_hash(password):
        return pwd_context.hash(password)


class UserRead(UserBase):
    id: int


class Users(BaseModel):
    __root__: list[User]


@optional
class UserUpdate(UserBase):
    id: int


class UserDelete(BaseModel):
    id: int
