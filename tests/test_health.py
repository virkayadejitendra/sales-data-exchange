from collections.abc import Iterator

import pytest
from fastapi import HTTPException, status
from fastapi.testclient import TestClient

from app.api.v1.routes.health import verify_database_connection
from app.main import create_app


@pytest.fixture
def client() -> Iterator[TestClient]:
    application = create_app()

    async def healthy_database() -> None:
        return None

    application.dependency_overrides[verify_database_connection] = healthy_database
    with TestClient(application) as test_client:
        yield test_client
    application.dependency_overrides.clear()


def test_liveness(client: TestClient) -> None:
    response = client.get("/health/live")

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {"status": "ok"}


def test_readiness_when_database_is_available(client: TestClient) -> None:
    response = client.get("/health/ready")

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {"status": "ok"}


def test_readiness_when_database_is_unavailable() -> None:
    application = create_app()

    async def unavailable_database() -> None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database is unavailable.",
        )

    application.dependency_overrides[verify_database_connection] = unavailable_database
    with TestClient(application) as test_client:
        response = test_client.get("/health/ready")

    assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
    assert response.json() == {"detail": "Database is unavailable."}
