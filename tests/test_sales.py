from fastapi import status
from fastapi.testclient import TestClient

from tests.test_catalog import RETAILER_ID, create_product, outlet_payload

pytest_plugins = ("tests.test_catalog",)


def create_catalog_prerequisites(client: TestClient) -> dict[str, str]:
    product = create_product(client)
    outlet_response = client.post("/api/v1/outlets", json=outlet_payload())
    assert outlet_response.status_code == status.HTTP_201_CREATED
    mapping_response = client.post(
        "/api/v1/retailer-product-mappings",
        json={
            "retailer_id": str(RETAILER_ID),
            "retailer_sku": "SOAP-DOVE-100",
            "product_id": product["id"],
        },
    )
    assert mapping_response.status_code == status.HTTP_201_CREATED
    return {"product_id": product["id"], "outlet_id": outlet_response.json()["id"]}


def sales_batch_payload(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "retailer_id": str(RETAILER_ID),
        "business_date": "2026-10-18",
        "items": [
            {
                "outlet_code": "MUM-ANDHERI-01",
                "retailer_sku": "SOAP-DOVE-100",
                "units_sold": 24,
                "units_returned": 1,
                "gross_amount": "1560.00",
                "discount_amount": "60.00",
                "net_amount": "1500.00",
                "closing_stock": 38,
                "currency": "INR",
                "source_reference": "BATCH-001",
            }
        ],
    }
    payload.update(overrides)
    return payload


def test_batch_import_inserts_then_updates_existing_sale(catalog_client: TestClient) -> None:
    create_catalog_prerequisites(catalog_client)

    insert_response = catalog_client.post(
        "/api/v1/retailer/sales/batch", json=sales_batch_payload()
    )
    assert insert_response.status_code == status.HTTP_201_CREATED
    assert insert_response.json() == {
        "dry_run": False,
        "inserted_count": 1,
        "updated_count": 0,
        "error_count": 0,
        "errors": [],
    }

    corrected = sales_batch_payload()
    corrected["items"][0]["units_sold"] = 25  # type: ignore[index]
    corrected["items"][0]["gross_amount"] = "1625.00"  # type: ignore[index]
    corrected["items"][0]["net_amount"] = "1565.00"  # type: ignore[index]
    update_response = catalog_client.post("/api/v1/retailer/sales/batch", json=corrected)
    assert update_response.status_code == status.HTTP_201_CREATED
    assert update_response.json()["inserted_count"] == 0
    assert update_response.json()["updated_count"] == 1


def test_batch_rejects_unknown_sku_without_partial_insert(catalog_client: TestClient) -> None:
    create_catalog_prerequisites(catalog_client)
    payload = sales_batch_payload()
    payload["items"].append(  # type: ignore[union-attr]
        {
            "outlet_code": "MUM-ANDHERI-01",
            "retailer_sku": "UNKNOWN-SKU",
            "units_sold": 1,
            "units_returned": 0,
            "gross_amount": "10.00",
            "discount_amount": "0.00",
            "net_amount": "10.00",
            "currency": "INR",
        }
    )

    response = catalog_client.post("/api/v1/retailer/sales/batch", json=payload)
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    assert response.json()["detail"] == "Sales validation failed."
    assert response.json()["errors"][0]["row_number"] == 2


def test_csv_dry_run_does_not_persist_and_real_import_does(catalog_client: TestClient) -> None:
    create_catalog_prerequisites(catalog_client)
    csv_data = (
        "business_date,outlet_code,source_reference,currency,retailer_sku,units_sold,"
        "units_returned,gross_amount,discount_amount,net_amount,closing_stock\n"
        "2026-10-19,MUM-ANDHERI-01,BATCH-CSV-001,INR,SOAP-DOVE-100,10,0,"
        "650.00,0.00,650.00,24\n"
    )
    files = {"file": ("sales.csv", csv_data, "text/csv")}
    query = {"retailer_id": str(RETAILER_ID), "dry_run": "true"}

    dry_run_response = catalog_client.post(
        "/api/v1/retailer/sales/import", params=query, files=files
    )
    assert dry_run_response.status_code == status.HTTP_200_OK
    assert dry_run_response.json()["dry_run"] is True
    assert dry_run_response.json()["inserted_count"] == 1

    import_response = catalog_client.post(
        "/api/v1/retailer/sales/import",
        params={"retailer_id": str(RETAILER_ID)},
        files=files,
    )
    assert import_response.status_code == status.HTTP_200_OK
    assert import_response.json()["inserted_count"] == 1

    replay_response = catalog_client.post(
        "/api/v1/retailer/sales/import",
        params={"retailer_id": str(RETAILER_ID)},
        files=files,
    )
    assert replay_response.status_code == status.HTTP_200_OK
    assert replay_response.json()["updated_count"] == 1


def test_csv_dry_run_returns_row_errors(catalog_client: TestClient) -> None:
    create_catalog_prerequisites(catalog_client)
    csv_data = (
        "business_date,outlet_code,source_reference,currency,retailer_sku,units_sold,"
        "units_returned,gross_amount,discount_amount,net_amount,closing_stock\n"
        "2026-10-19,MUM-ANDHERI-01,BATCH-CSV-002,INR,SOAP-DOVE-100,5,6,"
        "100.00,0.00,100.00,12\n"
    )
    response = catalog_client.post(
        "/api/v1/retailer/sales/import",
        params={"retailer_id": str(RETAILER_ID), "dry_run": "true"},
        files={"file": ("invalid-sales.csv", csv_data, "text/csv")},
    )
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["error_count"] > 0
    assert response.json()["errors"][0]["row_number"] == 2
