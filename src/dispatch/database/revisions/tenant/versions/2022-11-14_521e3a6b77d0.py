"""Adds subject to notifications to handle case/incident split

Revision ID: 521e3a6b77d0
Revises: eb348d46afd0
Create Date: 2022-11-14 10:51:56.769322

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "521e3a6b77d0"
down_revision = "eb348d46afd0"
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.alter_column(
        "search_filter",
        "type",
        nullable=True,
        new_column_name="subject",
    )
    op.add_column("notification", sa.Column("subject", sa.String(), nullable=True))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.alter_column(
        "search_filter",
        "subject",
        nullable=True,
        new_column_name="type",
    )
    op.drop_column("notification", "subject")
    # ### end Alembic commands ###
