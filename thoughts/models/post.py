
from typing import Dict, Optional, List, Union

# import httpx
import pydantic
from pydantic import BaseModel
from sqlmodel import Field, SQLModel, Column, JSON

# from thoughts.config import config
from thoughts.optional import optional


class PostBase(SQLModel, table=False):
    title: str
    link: str
    tags: Optional[Union[str, List[str]]] = Field(sa_column=Column(JSON))
    message: Optional[str]
    published: bool = Field(default=True)

class Post(PostBase, table=True):
    id: int = Field(default=None, primary_key=True)


class PostCreate(PostBase):
    ...

    # def post(self) -> Post:
    #     r = httpx.post(
    #         f"{config.api_client.url}/post/",
    #         json=self.dict(),
    #     )
    #     if r.status_code != 200:
    #         raise RuntimeError(f"{r.status_code}:\n {r.text}")

    #     return Post.parse_obj(r.json())


class PostRead(PostBase):
    id: int

    # @classmethod
    # def get(
    #     cls,
    #     id: int,
    # ) -> Post:
    #     r = httpx.get(f"{config.api_client.url}/post/{id}")
    #     if r.status_code != 200:
    #         raise RuntimeError(f"{r.status_code}:\n {r.text}")
    #     return PostRead.parse_obj(r.json())


class Posts(BaseModel):
    __root__: list[Post]

    # @classmethod
    # def list(
    #     self,
    # ) -> Post:
    #     r = httpx.get(f"{config.api_client.url}/posts/")
    #     if r.status_code != 200:
    #         raise RuntimeError(f"{r.status_code}:\n {r.text}")
    #     return Posts.parse_obj({"__root__": r.json()})


@optional
class PostUpdate(PostBase):
    id: int

    # def update(self) -> Post:
    #     r = httpx.patch(
    #         f"{config.api_client.url}/post/",
    #         json=self.dict(exclude_none=True),
    #     )
    #     if r.status_code != 200:
    #         raise RuntimeError(f"{r.status_code}:\n {r.text}")
    #     return Post.parse_obj(r.json())


class PostDelete(BaseModel):
    id: int

#     @classmethod
#     def delete(self, id: int) -> Dict[str, bool]:
#         r = httpx.delete(
#             f"{config.api_client.url}/post/{id}",
#         )
#         if r.status_code != 200:
#             raise RuntimeError(f"{r.status_code}:\n {r.text}")
#         return {"ok": True}
