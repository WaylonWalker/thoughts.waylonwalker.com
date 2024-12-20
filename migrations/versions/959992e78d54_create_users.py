"""create users

Revision ID: 959992e78d54
Revises: f419e0f94968
Create Date: 2023-08-04 19:46:20.033868

"""

from alembic import op
import sqlalchemy as sa
import sqlmodel
from sqlmodel import Session

from thoughts.config import database
from thoughts.models.user import User

# revision identifiers, used by Alembic.
revision = "959992e78d54"
down_revision = "f419e0f94968"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table(
        "user",
        sa.Column("username", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("full_name", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("email", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column(
            "hashed_password", sqlmodel.sql.sqltypes.AutoString(), nullable=False
        ),
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("disabled", sa.Boolean(), nullable=False, server_default="0"),
        sa.PrimaryKeyConstraint("id", name="user_pkey"),
    )

    # create record for user
    with Session(database.engine) as session:
        user = User(
            username="waylonwalker",
            full_name="Waylon Walker",
            email="waylon@waylonwalker.com",
            hashed_password="$2b$12$fph57TJ1UrGU/wAaRVXOWulG/7nOwCn89B9z3wOPCqb7O6uAoZSHC",
            disabled=False,
        )
        session.add(user)
        session.commit()

    with op.batch_alter_table("post", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column("public", sa.Boolean(), nullable=False, server_default="1")
        )
        batch_op.add_column(
            sa.Column("author_id", sa.Integer(), nullable=False, server_default="1")
        )
        batch_op.create_foreign_key(
            "fk_post_author_id_user", "user", ["author_id"], ["id"]
        )

    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table("post", schema=None) as batch_op:
        batch_op.drop_constraint(None, type_="foreignkey")
        batch_op.drop_column("author_id")
        batch_op.drop_column("public")

    op.drop_table("user")
    # ### end Alembic commands ###
