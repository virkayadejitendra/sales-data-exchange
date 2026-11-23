# Day 3: Daily sales ingestion

Retailers submit sales against their own active outlets and retailer SKU mappings. The API
resolves the mapped manufacturer product internally; callers never provide a `product_id`.

## JSON batch import

`POST /api/v1/retailer/sales/batch`

```json
{
  "retailer_id": "10000000-0000-0000-0000-000000000001",
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
      "source_reference": "BATCH-MA01-20261018"
    }
  ]
}
```

The response reports whether rows were inserted or updated. Sending the same retailer,
outlet, product, and business date again updates the existing record.

## CSV import

`POST /api/v1/retailer/sales/import?retailer_id=<retailer-uuid>&dry_run=true`

Send the file as multipart form-data under the `file` field. Use `dry_run=true` first: it
validates every row and returns counts/errors without writing anything. Remove `dry_run` for
the transactional import.

The required headers are exactly:

```text
business_date,outlet_code,source_reference,currency,retailer_sku,units_sold,units_returned,gross_amount,discount_amount,net_amount,closing_stock
```

`sample-data/retailer_daily_sales.csv` uses this layout. Before importing it, create the
corresponding outlets and retailer SKU mappings from `sample-data/retailer_product_mappings.csv`.

## Validation and atomicity

- Outlet code must identify an active outlet owned by the retailer.
- Retailer SKU must have an active mapping to an active product.
- Quantities and money cannot be negative.
- Returns cannot exceed units sold.
- Discount cannot exceed gross amount.
- Net amount must equal gross amount minus discount.
- An invalid row rejects the entire real import. Use a dry run to see every CSV row error.

Import [postman/Sales-Data-Exchange-Day-3.postman_collection.json](../postman/Sales-Data-Exchange-Day-3.postman_collection.json)
to exercise the Day 3 API.
