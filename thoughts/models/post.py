from datetime import datetime
from typing import List, Optional, Union

from pydantic import BaseModel
from sqlmodel import Column, Field, JSON, Relationship, SQLModel

from thoughts.models.user import User, UserBase
from thoughts.optional import optional


class PostBase(SQLModel, table=False):
    title: str
    link: str
    tags: Optional[Union[str, List[str]]] = Field(sa_column=Column(JSON))
    message: Optional[str]
    published: bool = Field(default=True)
    public: bool = Field(default=True)
    date: datetime = Field(default_factory=datetime.now)

    @property
    def hr_date(self) -> str:
        if self.date.year != datetime.now().year:
            return self.date.year
        days = (datetime.now() - self.date).days
        if days == 0:
            return "Today"
        elif days == 1:
            return "Yesterday"
        else:
            return f"{days} days ago"


class Post(PostBase, table=True):
    id: int = Field(default=None, primary_key=True)
    author: Optional[User] = Relationship(back_populates="posts")
    author_id: int = Field(foreign_key="user.id")


class PostCreate(PostBase):
    author_id: Optional[int] = Field(foreign_key="user.id")


class PostRead(PostBase):
    id: int
    author: UserBase


class Posts(BaseModel):
    __root__: list[PostRead]


@optional
class PostUpdate(PostBase):
    id: int


class PostDelete(BaseModel):
    id: int
