# Sample retailer data

`day2_organizations.sql` creates the retailer and manufacturer required by the Day 2 catalog
examples. It is repeatable because existing sample UUIDs are left unchanged.

## Files

- `retailer_daily_sales.csv` is a realistic retailer sales submission containing 43 rows across three outlets and seven business dates.
- `retailer_product_mappings.csv` is reference setup data that maps each retailer SKU in the sales file to its manufacturer product.

The sales submission intentionally does not contain `retailer_id` or `manufacturer_id`. The API must derive the retailer from the authenticated caller and the manufacturer from the mapped product. This prevents a caller from selecting another tenant in the CSV.

## Required sales CSV columns

| Column | Format and rule |
| --- | --- |
| `business_date` | ISO date: `YYYY-MM-DD` |
| `outlet_code` | Must belong to the authenticated retailer |
| `source_reference` | Retailer-defined batch reference |
| `currency` | Three uppercase characters, such as `INR` |
| `retailer_sku` | Must have an active product mapping |
| `units_sold` | Non-negative whole number |
| `units_returned` | Non-negative whole number; cannot exceed units sold |
| `gross_amount` | Non-negative decimal with at most two fractional digits |
| `discount_amount` | Non-negative decimal; cannot exceed gross amount |
| `net_amount` | Must equal gross amount minus discount amount |
| `closing_stock` | Optional non-negative whole number |

CSV requirements:

- UTF-8 encoding.
- Comma delimiter.
- One header row with the exact column names above.
- Period (`.`) as the decimal separator.
- No currency symbols or thousands separators in numeric values.
- A maximum of 5,000 data rows per upload in the MVP.
- A file is processed atomically: if any row is invalid, no rows are stored.

## Planned upload request

After the Day 3 endpoint has been implemented, the file can be validated without saving it:

```powershell
curl.exe -X POST "http://localhost:8000/api/v1/retailer/sales/import?dry_run=true" `
  -H "Authorization: Bearer <retailer-access-token>" `
  -F "file=@sample-data/retailer_daily_sales.csv;type=text/csv"
```

To perform the import:

```powershell
curl.exe -X POST "http://localhost:8000/api/v1/retailer/sales/import" `
  -H "Authorization: Bearer <retailer-access-token>" `
  -F "file=@sample-data/retailer_daily_sales.csv;type=text/csv"
```

Expected high-level response:

```json
{
  "file_name": "retailer_daily_sales.csv",
  "total_rows": 43,
  "inserted_rows": 43,
  "updated_rows": 0,
  "rejected_rows": 0,
  "dry_run": false
}
```

Uploading the same file a second time should report the records as updates and must not create duplicates.
