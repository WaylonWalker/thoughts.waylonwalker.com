"""published

Revision ID: 6fbc4459f3d3
Revises: d754168984f4
Create Date: 2023-07-23 21:09:16.493701

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "6fbc4459f3d3"
down_revision = "d754168984f4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column(
        "post", sa.Column("published", sa.Boolean(), nullable=False, server_default="1")
    )
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column("post", "published")
    # ### end Alembic commands ###
