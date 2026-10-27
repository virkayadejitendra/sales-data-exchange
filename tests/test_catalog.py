import asyncio
from collections.abc import AsyncIterator, Iterator
from pathlib import Path
from uuid import UUID

import pytest
from fastapi import status
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.infrastructure.database import get_db_session
from app.infrastructure.models import Base, Organization, OrganizationType
from app.main import create_app

RETAILER_ID = UUID("10000000-0000-0000-0000-000000000001")
MANUFACTURER_ID = UUID("20000000-0000-0000-0000-000000000001")


@pytest.fixture
def catalog_client(tmp_path: Path) -> Iterator[TestClient]:
    database_path = tmp_path / "catalog.db"
    test_engine = create_async_engine(
        f"sqlite+aiosqlite:///{database_path.as_posix()}",
        poolclass=NullPool,
    )
    test_session_factory = async_sessionmaker(
        bind=test_engine,
        autoflush=False,
        expire_on_commit=False,
    )

    async def prepare_database() -> None:
        async with test_engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        async with test_session_factory() as session:
            session.add_all(
                [
                    Organization(
                        id=RETAILER_ID,
                        name="Demo Retailer",
                        type=OrganizationType.RETAILER,
                    ),
                    Organization(
                        id=MANUFACTURER_ID,
                        name="Demo Manufacturer",
                        type=OrganizationType.MANUFACTURER,
                    ),
                ]
            )
            await session.commit()

    async def override_database_session() -> AsyncIterator[object]:
        async with test_session_factory() as session:
            try:
                yield session
            except Exception:
                await session.rollback()
                raise

    asyncio.run(prepare_database())
    application = create_app()
    application.dependency_overrides[get_db_session] = override_database_session

    with TestClient(application) as client:
        yield client

    application.dependency_overrides.clear()
    asyncio.run(test_engine.dispose())


def product_payload(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "manufacturer_id": str(MANUFACTURER_ID),
        "manufacturer_sku": "DOVE-SOAP-100G",
        "gtin": "8901030123456",
        "name": "Dove Cream Beauty Bathing Bar",
        "brand": "Dove",
        "category": "Personal Care",
        "subcategory": "Bathing Soap",
        "variant": "Original",
        "pack_size": "100.000",
        "unit_of_measure": "GRAM",
        "mrp": "65.00",
    }
    payload.update(overrides)
    return payload


def outlet_payload(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "retailer_id": str(RETAILER_ID),
        "code": "MUM-ANDHERI-01",
        "name": "Andheri Supermarket",
        "channel": "SUPERMARKET",
        "city": "Mumbai",
        "state": "Maharashtra",
        "country": "India",
    }
    payload.update(overrides)
    return payload


def create_product(client: TestClient, **overrides: object) -> dict[str, object]:
    response = client.post("/api/v1/products", json=product_payload(**overrides))
    assert response.status_code == status.HTTP_201_CREATED
    return response.json()


def test_create_get_filter_patch_and_deactivate_product(catalog_client: TestClient) -> None:
    product = create_product(catalog_client)

    assert product["manufacturer_sku"] == "DOVE-SOAP-100G"
    assert product["mrp"] == "65.00"
    assert "_sa_instance_state" not in product

    get_response = catalog_client.get(f"/api/v1/products/{product['id']}")
    assert get_response.status_code == status.HTTP_200_OK
    assert get_response.json() == product

    list_response = catalog_client.get("/api/v1/products", params={"brand": "dov"})
    assert list_response.status_code == status.HTTP_200_OK
    assert [item["id"] for item in list_response.json()] == [product["id"]]

    patch_response = catalog_client.patch(
        f"/api/v1/products/{product['id']}",
        json={"mrp": "70.50"},
    )
    assert patch_response.status_code == status.HTTP_200_OK
    assert patch_response.json()["mrp"] == "70.50"
    assert patch_response.json()["name"] == product["name"]

    delete_response = catalog_client.delete(f"/api/v1/products/{product['id']}")
    assert delete_response.status_code == status.HTTP_204_NO_CONTENT
    assert catalog_client.get(f"/api/v1/products/{product['id']}").json()["is_active"] is False


def test_product_requires_manufacturer_and_valid_decimals(catalog_client: TestClient) -> None:
    wrong_owner = catalog_client.post(
        "/api/v1/products",
        json=product_payload(manufacturer_id=str(RETAILER_ID)),
    )
    assert wrong_owner.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    assert "must be a manufacturer" in wrong_owner.json()["detail"]

    invalid_pack_size = catalog_client.post(
        "/api/v1/products",
        json=product_payload(pack_size="0"),
    )
    assert invalid_pack_size.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT

    invalid_money = catalog_client.post(
        "/api/v1/products",
        json=product_payload(mrp="65.999"),
    )
    assert invalid_money.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT


def test_duplicate_product_sku_returns_conflict(catalog_client: TestClient) -> None:
    create_product(catalog_client)

    duplicate_response = catalog_client.post(
        "/api/v1/products",
        json=product_payload(gtin="8901030123457"),
    )

    assert duplicate_response.status_code == status.HTTP_409_CONFLICT
    assert "already exists" in duplicate_response.json()["detail"]


def test_outlet_crud_requires_retailer_and_rejects_duplicate_code(
    catalog_client: TestClient,
) -> None:
    create_response = catalog_client.post("/api/v1/outlets", json=outlet_payload())
    assert create_response.status_code == status.HTTP_201_CREATED
    outlet = create_response.json()
    assert "_sa_instance_state" not in outlet

    get_response = catalog_client.get(f"/api/v1/outlets/{outlet['id']}")
    assert get_response.status_code == status.HTTP_200_OK

    patch_response = catalog_client.patch(
        f"/api/v1/outlets/{outlet['id']}",
        json={"name": "Updated Andheri Supermarket"},
    )
    assert patch_response.status_code == status.HTTP_200_OK
    assert patch_response.json()["name"] == "Updated Andheri Supermarket"

    duplicate_response = catalog_client.post("/api/v1/outlets", json=outlet_payload())
    assert duplicate_response.status_code == status.HTTP_409_CONFLICT

    wrong_owner_response = catalog_client.post(
        "/api/v1/outlets",
        json=outlet_payload(retailer_id=str(MANUFACTURER_ID), code="MUM-BKC-01"),
    )
    assert wrong_owner_response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    assert "must be a retailer" in wrong_owner_response.json()["detail"]


def test_map_retailer_sku_to_manufacturer_product(catalog_client: TestClient) -> None:
    product = create_product(catalog_client)
    payload = {
        "retailer_id": str(RETAILER_ID),
        "retailer_sku": "SOAP-DOVE-100",
        "product_id": product["id"],
    }

    create_response = catalog_client.post("/api/v1/retailer-product-mappings", json=payload)
    assert create_response.status_code == status.HTTP_201_CREATED
    mapping = create_response.json()
    assert mapping["retailer_sku"] == "SOAP-DOVE-100"
    assert mapping["product_id"] == product["id"]
    assert "_sa_instance_state" not in mapping

    get_response = catalog_client.get(f"/api/v1/retailer-product-mappings/{mapping['id']}")
    assert get_response.status_code == status.HTTP_200_OK
    assert get_response.json() == mapping

    duplicate_response = catalog_client.post("/api/v1/retailer-product-mappings", json=payload)
    assert duplicate_response.status_code == status.HTTP_409_CONFLICT
