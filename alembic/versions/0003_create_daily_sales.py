"""Create daily sales table.

Revision ID: 0003_create_daily_sales
Revises: 0002_create_catalog
Create Date: 2026-11-23
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0003_create_daily_sales"
down_revision: str | None = "0002_create_catalog"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "daily_sales",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("retailer_id", sa.Uuid(), nullable=False),
        sa.Column("outlet_id", sa.Uuid(), nullable=False),
        sa.Column("product_id", sa.Uuid(), nullable=False),
        sa.Column("business_date", sa.Date(), nullable=False),
        sa.Column("units_sold", sa.Integer(), nullable=False),
        sa.Column("units_returned", sa.Integer(), server_default="0", nullable=False),
        sa.Column("gross_amount", sa.Numeric(precision=14, scale=2), nullable=False),
        sa.Column(
            "discount_amount", sa.Numeric(precision=14, scale=2), server_default="0", nullable=False
        ),
        sa.Column("net_amount", sa.Numeric(precision=14, scale=2), nullable=False),
        sa.Column("closing_stock", sa.Integer(), nullable=True),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("source_reference", sa.String(length=100), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["outlet_id"], ["outlets.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["retailer_id"], ["organizations.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "retailer_id",
            "outlet_id",
            "product_id",
            "business_date",
            name="uq_daily_sales_retailer_outlet_product_date",
        ),
    )
    op.create_index(
        op.f("ix_daily_sales_business_date"), "daily_sales", ["business_date"], unique=False
    )
    op.create_index(op.f("ix_daily_sales_outlet_id"), "daily_sales", ["outlet_id"], unique=False)
    op.create_index(op.f("ix_daily_sales_product_id"), "daily_sales", ["product_id"], unique=False)
    op.create_index(
        op.f("ix_daily_sales_retailer_id"), "daily_sales", ["retailer_id"], unique=False
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_daily_sales_retailer_id"), table_name="daily_sales")
    op.drop_index(op.f("ix_daily_sales_product_id"), table_name="daily_sales")
    op.drop_index(op.f("ix_daily_sales_outlet_id"), table_name="daily_sales")
    op.drop_index(op.f("ix_daily_sales_business_date"), table_name="daily_sales")
    op.drop_table("daily_sales")
