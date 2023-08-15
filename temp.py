from sqlmodel import select

from thoughts.config import get_session
from thoughts.models.post import Post

session = next(get_session())

post = session.exec(select(Post)).first()
