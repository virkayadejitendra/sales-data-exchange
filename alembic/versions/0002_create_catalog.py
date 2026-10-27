"""Create products, outlets, and retailer product mappings.

Revision ID: 0002_create_catalog
Revises: 0001_create_organizations
Create Date: 2026-10-24
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0002_create_catalog"
down_revision: str | None = "0001_create_organizations"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "products",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("manufacturer_id", sa.Uuid(), nullable=False),
        sa.Column("manufacturer_sku", sa.String(length=100), nullable=False),
        sa.Column("gtin", sa.String(length=14), nullable=True),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("brand", sa.String(length=100), nullable=False),
        sa.Column("category", sa.String(length=100), nullable=False),
        sa.Column("subcategory", sa.String(length=100), nullable=True),
        sa.Column("variant", sa.String(length=100), nullable=True),
        sa.Column("pack_size", sa.Numeric(precision=12, scale=3), nullable=False),
        sa.Column(
            "unit_of_measure",
            sa.Enum(
                "EACH",
                "GRAM",
                "KILOGRAM",
                "MILLILITRE",
                "LITRE",
                name="unit_of_measure",
                native_enum=False,
                create_constraint=True,
                length=20,
            ),
            nullable=False,
        ),
        sa.Column("mrp", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
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
        sa.ForeignKeyConstraint(
            ["manufacturer_id"],
            ["organizations.id"],
            name=op.f("fk_products_manufacturer_id_organizations"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_products")),
        sa.UniqueConstraint("gtin", name=op.f("uq_products_gtin")),
        sa.UniqueConstraint(
            "manufacturer_id",
            "manufacturer_sku",
            name="uq_products_manufacturer_sku",
        ),
    )
    op.create_index(op.f("ix_products_brand"), "products", ["brand"], unique=False)
    op.create_index(op.f("ix_products_category"), "products", ["category"], unique=False)
    op.create_index(
        op.f("ix_products_manufacturer_id"),
        "products",
        ["manufacturer_id"],
        unique=False,
    )

    op.create_table(
        "outlets",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("retailer_id", sa.Uuid(), nullable=False),
        sa.Column("code", sa.String(length=100), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column(
            "channel",
            sa.Enum(
                "SUPERMARKET",
                "GENERAL_TRADE",
                "CONVENIENCE",
                "ONLINE",
                "OTHER",
                name="outlet_channel",
                native_enum=False,
                create_constraint=True,
                length=30,
            ),
            nullable=False,
        ),
        sa.Column("city", sa.String(length=100), nullable=True),
        sa.Column("district", sa.String(length=100), nullable=True),
        sa.Column("state", sa.String(length=100), nullable=True),
        sa.Column("country", sa.String(length=100), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
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
        sa.ForeignKeyConstraint(
            ["retailer_id"],
            ["organizations.id"],
            name=op.f("fk_outlets_retailer_id_organizations"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_outlets")),
        sa.UniqueConstraint("retailer_id", "code", name="uq_outlets_retailer_code"),
    )
    op.create_index(op.f("ix_outlets_channel"), "outlets", ["channel"], unique=False)
    op.create_index(
        op.f("ix_outlets_retailer_id"),
        "outlets",
        ["retailer_id"],
        unique=False,
    )
    op.create_index(op.f("ix_outlets_state"), "outlets", ["state"], unique=False)

    op.create_table(
        "retailer_product_mappings",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("retailer_id", sa.Uuid(), nullable=False),
        sa.Column("retailer_sku", sa.String(length=100), nullable=False),
        sa.Column("product_id", sa.Uuid(), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
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
        sa.ForeignKeyConstraint(
            ["product_id"],
            ["products.id"],
            name=op.f("fk_retailer_product_mappings_product_id_products"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["retailer_id"],
            ["organizations.id"],
            name=op.f("fk_retailer_product_mappings_retailer_id_organizations"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_retailer_product_mappings")),
        sa.UniqueConstraint(
            "retailer_id",
            "retailer_sku",
            name="uq_retailer_product_mappings_retailer_sku",
        ),
    )
    op.create_index(
        op.f("ix_retailer_product_mappings_product_id"),
        "retailer_product_mappings",
        ["product_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_retailer_product_mappings_retailer_id"),
        "retailer_product_mappings",
        ["retailer_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_retailer_product_mappings_retailer_id"),
        table_name="retailer_product_mappings",
    )
    op.drop_index(
        op.f("ix_retailer_product_mappings_product_id"),
        table_name="retailer_product_mappings",
    )
    op.drop_table("retailer_product_mappings")
    op.drop_index(op.f("ix_outlets_state"), table_name="outlets")
    op.drop_index(op.f("ix_outlets_retailer_id"), table_name="outlets")
    op.drop_index(op.f("ix_outlets_channel"), table_name="outlets")
    op.drop_table("outlets")
    op.drop_index(op.f("ix_products_manufacturer_id"), table_name="products")
    op.drop_index(op.f("ix_products_category"), table_name="products")
    op.drop_index(op.f("ix_products_brand"), table_name="products")
    op.drop_table("products")
