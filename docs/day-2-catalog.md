# Day 2: Product, outlet, and SKU catalog

All catalog endpoints are available under `/api/v1` and documented interactively at
<http://localhost:8000/docs>.

You can also import `postman/Sales-Data-Exchange.postman_collection.json` into Postman. The
collection contains the examples below, automatically stores created UUIDs, and includes
response assertions.

## 1. Load prerequisite organizations

Products must belong to a manufacturer, while outlets and retailer SKU mappings must belong
to a retailer. Load the two repeatable development records before trying the examples:

```powershell
Get-Content sample-data/day2_organizations.sql |
    docker compose exec -T postgres psql -U postgres -d sales_data_exchange
```

The sample identifiers are:

- Retailer: `10000000-0000-0000-0000-000000000001`
- Manufacturer: `20000000-0000-0000-0000-000000000001`

## 2. Create a product

`POST /api/v1/products`

```json
{
  "manufacturer_id": "20000000-0000-0000-0000-000000000001",
  "manufacturer_sku": "DOVE-SOAP-100G",
  "gtin": "8901030123456",
  "name": "Dove Cream Beauty Bathing Bar",
  "brand": "Dove",
  "category": "Personal Care",
  "subcategory": "Bathing Soap",
  "variant": "Original",
  "pack_size": "100.000",
  "unit_of_measure": "GRAM",
  "mrp": "65.00"
}
```

Copy the returned product `id`; it is required when creating the retailer SKU mapping.

## 3. Create an outlet

`POST /api/v1/outlets`

```json
{
  "retailer_id": "10000000-0000-0000-0000-000000000001",
  "code": "MUM-ANDHERI-01",
  "name": "Andheri Supermarket",
  "channel": "SUPERMARKET",
  "city": "Mumbai",
  "district": "Mumbai Suburban",
  "state": "Maharashtra",
  "country": "India"
}
```

## 4. Map a retailer SKU

Replace `<product-id>` with the product UUID returned in step 2.

`POST /api/v1/retailer-product-mappings`

```json
{
  "retailer_id": "10000000-0000-0000-0000-000000000001",
  "retailer_sku": "SOAP-DOVE-100",
  "product_id": "<product-id>"
}
```

## 5. Explore query parameters and PATCH

Examples:

```http
GET /api/v1/products?brand=Dove&is_active=true&limit=20
GET /api/v1/outlets?state=Maharashtra&channel=SUPERMARKET
GET /api/v1/retailer-product-mappings?retailer_sku=SOAP-DOVE-100
```

A `PATCH` body contains only the fields to change:

```json
{
  "mrp": "70.50"
}
```

`DELETE` is intentionally a soft delete. It preserves the record and changes `is_active` to
`false`, which protects references from future sales history.

## Validation behavior

- Money uses fixed-precision decimal values with at most two decimal places.
- Pack size must be positive and supports at most three decimal places.
- Manufacturer SKU is unique within a manufacturer.
- GTIN is globally unique when supplied.
- Outlet code and retailer SKU are unique within a retailer.
- Organization ownership is checked before a catalog record is stored.
- Duplicate catalog identifiers return `409 Conflict`.
- Invalid values or organization types return `422 Unprocessable Content`.
