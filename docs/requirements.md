# Sales Data Exchange

## Product Requirements Document

| Field | Value |
| --- | --- |
| Document status | Draft v0.1 |
| Project type | FastAPI learning project and production-style REST API |
| Domain | FMCG/CPG retail sell-out data sharing |
| Delivery plan | Seven daily feature milestones |

## 1. Purpose

Retailers sell daily-use products to end consumers. Manufacturers need authorized sell-out data for product, pricing, geographic, promotion, and inventory analysis.

The platform will allow:

1. Retailers to upload daily product-level sales information.
2. Retailers to control which manufacturers can access their data.
3. Manufacturers to retrieve only data for their own products.
4. Manufacturers to filter and aggregate the authorized data through REST APIs.
5. Platform administrators to manage organizations and investigate access through audit logs.

The first version will store sales aggregated by retailer, outlet, product, and business date. It will not store individual consumer identities or complete receipts.

## 2. Product goals

- Provide a secure multi-tenant API for retailers and manufacturers.
- Prevent one manufacturer from accessing another manufacturer's product data.
- Accept repeatable, idempotent daily sales uploads.
- Support useful filters, pagination, sorting, and sales summaries.
- Demonstrate important FastAPI concepts in a realistic application.
- Run locally with PostgreSQL in Docker and have automated tests.

## 3. Non-goals for the seven-day MVP

- A web or mobile frontend.
- Consumer-level profiling or loyalty-program management.
- Receipt-level basket analysis.
- Real-time streaming through Kafka or another event broker.
- Machine-learning forecasts.
- Automated billing or manufacturer subscriptions.
- Kubernetes or a microservice architecture.
- Support for regulated products such as prescription medicines.

## 4. Actors and permissions

### 4.1 Platform administrator

- Create and view retailer and manufacturer organizations.
- Create initial organization users or API clients.
- View platform health and audit information.
- Must not silently bypass data-sharing rules when using normal manufacturer APIs.

### 4.2 Retailer

- Manage its outlets.
- Map retailer SKUs to manufacturer products.
- Upload and correct its daily sales records.
- Grant or revoke a manufacturer's access to its sales data.
- View its own uploaded records.

### 4.3 Manufacturer

- Read sales records for its own products.
- Read data only from retailers with an active sharing grant.
- Filter, sort, paginate, and aggregate authorized sales data.
- Never choose its identity using a request parameter.

## 5. Important terminology

- **Sell-out data:** Products sold by a retailer to end consumers.
- **Organization:** A retailer or manufacturer tenant in the platform.
- **Outlet:** A physical or online retail location.
- **Manufacturer SKU:** The product identifier assigned by the manufacturer.
- **Retailer SKU:** The retailer's internal identifier for the same product.
- **GTIN/barcode:** A standard product identifier when one is available.
- **Business date:** The retailer's local date on which sales occurred.
- **Sharing grant:** An explicit relationship allowing one manufacturer to read a retailer's applicable data.
- **Authorized data:** The intersection of the authenticated manufacturer's products and active retailer sharing grants.

## 6. Core data model

### 6.1 Organization

| Field | Rules |
| --- | --- |
| `id` | UUID primary key |
| `name` | Required |
| `type` | `RETAILER` or `MANUFACTURER` |
| `is_active` | Defaults to `true` |
| `created_at` | UTC timestamp |

### 6.2 User

| Field | Rules |
| --- | --- |
| `id` | UUID primary key |
| `organization_id` | Required foreign key |
| `email` | Globally unique, normalized to lowercase |
| `hashed_password` | Never store a plain-text password |
| `role` | `ADMIN`, `RETAILER_USER`, or `MANUFACTURER_USER` |
| `is_active` | Defaults to `true` |

### 6.3 Outlet

| Field | Rules |
| --- | --- |
| `id` | UUID primary key |
| `retailer_id` | Must reference a retailer organization |
| `code` | Unique within the retailer |
| `name` | Required |
| `channel` | Example: `SUPERMARKET`, `GENERAL_TRADE`, `ONLINE` |
| `city`, `district`, `state`, `country` | Used for geographic analysis |
| `is_active` | Defaults to `true` |

### 6.4 Product

| Field | Rules |
| --- | --- |
| `id` | UUID primary key |
| `manufacturer_id` | Must reference a manufacturer organization |
| `manufacturer_sku` | Unique within the manufacturer |
| `gtin` | Optional; unique when supplied |
| `name` | Required |
| `brand` | Required |
| `category` | Required |
| `subcategory` | Optional |
| `variant` | Optional |
| `pack_size` | Positive decimal value |
| `unit_of_measure` | Example: `GRAM`, `MILLILITRE`, `EACH` |
| `mrp` | Non-negative decimal value |
| `is_active` | Defaults to `true` |

### 6.5 Retailer product mapping

| Field | Rules |
| --- | --- |
| `id` | UUID primary key |
| `retailer_id` | Required |
| `retailer_sku` | Unique within the retailer |
| `product_id` | Required manufacturer product |
| `is_active` | Defaults to `true` |

### 6.6 Data-sharing grant

| Field | Rules |
| --- | --- |
| `id` | UUID primary key |
| `retailer_id` | Required retailer |
| `manufacturer_id` | Required manufacturer |
| `status` | `ACTIVE` or `REVOKED` |
| `valid_from` | Required UTC timestamp |
| `valid_until` | Optional UTC timestamp |
| `created_at`, `updated_at` | UTC timestamps |

Only one active grant may exist for a retailer/manufacturer pair.

### 6.7 Daily sale

| Field | Rules |
| --- | --- |
| `id` | UUID primary key |
| `retailer_id` | Derived from authenticated retailer |
| `outlet_id` | Must belong to the retailer |
| `product_id` | Resolved from the retailer SKU mapping |
| `business_date` | Required date |
| `units_sold` | Non-negative integer |
| `units_returned` | Non-negative integer |
| `gross_amount` | Non-negative fixed-precision decimal |
| `discount_amount` | Non-negative fixed-precision decimal |
| `net_amount` | Non-negative fixed-precision decimal |
| `closing_stock` | Optional non-negative integer |
| `currency` | Three-character ISO-style code such as `INR` |
| `source_reference` | Optional retailer batch/reference ID |
| `created_at`, `updated_at` | UTC timestamps |

The natural uniqueness rule is:

```text
retailer_id + outlet_id + product_id + business_date
```

Re-uploading that combination must update the existing record rather than insert a duplicate.

### 6.8 Audit log

| Field | Rules |
| --- | --- |
| `id` | UUID primary key |
| `actor_id` | Authenticated user or API client |
| `organization_id` | Actor's organization |
| `action` | Example: `SALES_READ`, `SALES_UPLOAD`, `GRANT_CREATED` |
| `resource_type` | Type of resource accessed |
| `filters` | Sanitized JSON; no secrets |
| `record_count` | Number of records returned or modified |
| `request_id` | Request correlation identifier |
| `created_at` | UTC timestamp |

## 7. Functional requirements

### FR-1: Health and API information

- `GET /health/live` reports whether the process is running.
- `GET /health/ready` checks database connectivity.
- OpenAPI documentation is available through FastAPI.
- All business endpoints are versioned under `/api/v1`.

### FR-2: Organization management

- An administrator can create retailer and manufacturer organizations.
- Organization names are required and organization types are validated.
- Deactivated organizations cannot upload or retrieve sales data.

### FR-3: Product catalog

- A manufacturer or administrator can create and update products belonging to that manufacturer.
- Manufacturer SKU is unique within one manufacturer.
- Product prices use fixed-precision decimal values, not floating-point values.
- Products can be filtered by brand, category, SKU, barcode, and active status.

### FR-4: Retail outlets and SKU mapping

- A retailer can create and update only its own outlets.
- An outlet code is unique within a retailer.
- A retailer can map its SKU to a manufacturer product.
- An unknown or inactive SKU mapping causes a clear validation error during upload.

### FR-5: Daily sales ingestion

- A retailer can submit one or many daily sales items in a single request.
- A retailer can upload a UTF-8 CSV file using `POST /api/v1/retailer/sales/import` with multipart form data.
- CSV uploads support `dry_run=true` to return validation results without storing records.
- The authenticated organization determines `retailer_id`; it is not trusted from the request body.
- The outlet must belong to the authenticated retailer.
- All items in one request are committed atomically: either all succeed or all fail.
- Re-uploading the same retailer/outlet/product/date combination updates the record.
- The response reports inserted and updated record counts.
- The maximum initial batch size is 1,000 items.
- The maximum CSV upload size is 5,000 data rows.
- The CSV header and row format are documented in `sample-data/README.md`.

Example request:

```json
{
  "business_date": "2026-10-24",
  "outlet_code": "MUM-STORE-01",
  "source_reference": "BATCH-20261024-01",
  "currency": "INR",
  "items": [
    {
      "retailer_sku": "SOAP-DOVE-100",
      "units_sold": 25,
      "units_returned": 1,
      "gross_amount": "1500.00",
      "discount_amount": "100.00",
      "net_amount": "1400.00",
      "closing_stock": 35
    }
  ]
}
```

### FR-6: Sharing-grant management

- A retailer can grant access to a manufacturer.
- A retailer can revoke an existing grant.
- Grant validity dates are enforced when manufacturer data is queried.
- Revocation prevents future API reads but does not delete historical sales.
- Creating, updating, or revoking a grant produces an audit record.

### FR-7: Manufacturer sales retrieval

- A manufacturer can retrieve only items for products it owns.
- Results include only retailers with a currently valid sharing grant.
- `manufacturer_id` is derived from authentication and cannot be overridden with a parameter.
- Supported filters include:
  - `from_date` and `to_date`
  - retailer and outlet
  - product, manufacturer SKU, and GTIN
  - brand, category, and subcategory
  - city, district, state, and channel
  - minimum units and minimum net amount
- Results support an explicit sort field and direction.
- Results use cursor pagination with a configurable page size up to 500.
- The maximum requested date range is initially 366 days.
- Every successful manufacturer read creates an audit record.

Example request:

```http
GET /api/v1/manufacturer/sales?from_date=2026-10-01&to_date=2026-10-24&brand=Dove&state=Maharashtra&page_size=100
```

### FR-8: Manufacturer analytics

- A manufacturer can request an authorized sales summary.
- Supported groupings for the MVP are `day`, `product`, `brand`, `category`, `retailer`, and `state`.
- Each result can provide:
  - units sold
  - units returned
  - gross amount
  - discount amount
  - net amount
  - average selling price
- Analytics queries enforce the same product-ownership and sharing-grant rules as raw sales queries.
- Empty results return an empty data list rather than an error.

### FR-9: Authentication and authorization

- Human users authenticate using email and password and receive a time-limited JWT access token.
- Passwords are securely hashed.
- Protected endpoints reject missing, invalid, or expired credentials.
- FastAPI dependencies provide the current actor and organization.
- Role and organization policies are enforced in the application layer in addition to route-level checks.
- Manufacturer read permissions include `sales:read` and `analytics:read`.
- Retailer write permissions include `sales:write` and `sharing:manage`.

### FR-10: Error responses

All application errors use a consistent shape:

```json
{
  "error": {
    "code": "PRODUCT_MAPPING_NOT_FOUND",
    "message": "No active product mapping exists for retailer SKU SOAP-001.",
    "details": {},
    "request_id": "req_01H..."
  }
}
```

Expected status codes include:

- `400` for invalid business requests.
- `401` for missing or invalid authentication.
- `403` for insufficient permission or tenant access.
- `404` for resources not visible to the caller.
- `409` for uniqueness or state conflicts.
- `422` for request-schema validation errors.
- `500` for unexpected server failures without leaking internal details.

## 8. Business rules

1. A retailer can write only its own outlet and sales data.
2. A manufacturer can read only its own product data.
3. A valid sharing grant is required for manufacturer access to a retailer's data.
4. Query parameters may narrow authorized data but may never expand authorization.
5. Consumer name, phone, email, address, and payment details are not collected in the MVP.
6. Monetary values are represented with `Decimal` in Python and `NUMERIC` in PostgreSQL.
7. Stored timestamps use UTC. `business_date` remains a retailer-local calendar date.
8. Returns cannot be negative. Whether returns may exceed units sold is a documented retailer-data policy; the MVP will reject this condition.
9. `discount_amount` cannot exceed `gross_amount`.
10. `net_amount` must equal `gross_amount - discount_amount` for the MVP.
11. Records are deactivated or superseded where practical instead of silently deleted.

## 9. Architecture requirements

Use a modular monolith with these responsibilities:

```text
HTTP request
    -> FastAPI router and request schema
    -> authentication/authorization dependency
    -> application service
    -> repository
    -> SQLAlchemy and PostgreSQL
```

Suggested source structure:

```text
app/
  main.py
  api/
    dependencies.py
    v1/
      auth.py
      organizations.py
      products.py
      outlets.py
      sales.py
      analytics.py
  application/
    services/
    exceptions.py
  domain/
    entities.py
    policies.py
    repositories.py
  infrastructure/
    database.py
    models/
    repositories/
  schemas/
  core/
    config.py
    security.py
    logging.py
tests/
  unit/
  integration/
```

Routers handle HTTP concerns. Services coordinate business use cases. Repositories handle persistence. Domain policies express access rules without depending on FastAPI.

## 10. Non-functional requirements

### Security and privacy

- Secrets come from environment variables and are never committed.
- Logs must not contain passwords, tokens, or complete authorization headers.
- Responses must not reveal whether an inaccessible cross-tenant resource exists.
- Database queries must always include tenant and data-sharing constraints.
- Audit records are append-only through normal application operations.
- Production traffic must use HTTPS.

### Performance

- A normal filtered sales request should target a response time under 500 ms in the local test dataset.
- Pagination is mandatory; unbounded list endpoints are not allowed.
- Initial indexes should support manufacturer/date, retailer/date, product/date, and SKU mapping lookups.
- Large file exports are outside the seven-day MVP and should eventually use an asynchronous job.

### Reliability

- Sales batches are transactional.
- Database migrations are managed by Alembic.
- Readiness fails when the database is unavailable.
- Duplicate retailer submissions do not create duplicate daily records.

### Maintainability

- Public functions and API schemas use type hints.
- Ruff is used for linting and formatting.
- pytest is used for automated tests.
- Configuration is loaded through `pydantic-settings`.
- Dependencies are recorded in `pyproject.toml` and locked with `uv.lock`.

## 11. Seven-day implementation plan

Each day should end with running code, tests, and a small Git commit. Do not begin the next day's optional work until the day's acceptance criteria pass.

### Day 1: Application foundation and database

**Features**

- Initialize the `uv` Python project.
- Add FastAPI, Uvicorn, SQLAlchemy, Alembic, PostgreSQL driver, Pydantic Settings, pytest, HTTPX, and Ruff.
- Create the application factory and `/health/live` endpoint.
- Add settings loaded from environment variables.
- Add PostgreSQL to Docker Compose.
- Configure SQLAlchemy sessions and Alembic.
- Create the `organizations` table and first migration.

**FastAPI concepts**

- Creating an application.
- Path operations and response models.
- Application configuration.
- Dependency injection for database sessions.
- Lifespan setup.

**Acceptance criteria**

- `docker compose up` starts PostgreSQL.
- Alembic upgrades a blank database successfully.
- `GET /health/live` returns `200`.
- `GET /health/ready` returns `200` when PostgreSQL is available.
- At least one health endpoint test passes.

### Day 2: Product, outlet, and SKU catalog

**Features**

- Add product, outlet, and retailer-product-mapping models and migrations.
- Create product CRUD endpoints.
- Create outlet CRUD endpoints.
- Create a retailer SKU mapping endpoint.
- Add validation for decimal money, pack size, organization type, and uniqueness.

**FastAPI concepts**

- Pydantic request and response schemas.
- Path and query parameters.
- `APIRouter` and API versioning.
- Status codes and exception handling.
- Partial updates with `PATCH`.

**Acceptance criteria**

- A product can be created and retrieved.
- An outlet can be created only for a retailer.
- A retailer SKU can be mapped to a manufacturer product.
- Duplicate SKUs and outlet codes return `409`.
- API responses never expose SQLAlchemy implementation details.

### Day 3: Daily sales ingestion

**Features**

- Add the `daily_sales` table and migration.
- Implement single-date batch upload.
- Implement CSV upload through `multipart/form-data`.
- Add CSV header validation, row-level validation details, and dry-run mode.
- Resolve products from retailer SKU mappings.
- Validate monetary totals and quantities.
- Insert new records and update existing natural-key matches.
- Return inserted and updated counts.

**FastAPI concepts**

- Nested request models.
- List and field validation.
- Transaction-scoped dependencies.
- Request headers and idempotent behavior.
- Domain exceptions mapped to HTTP errors.

**Acceptance criteria**

- A valid batch is stored atomically.
- The sample `retailer_daily_sales.csv` file passes dry-run validation and imports successfully.
- An unknown outlet or SKU rejects the complete batch.
- Re-uploading a batch does not create duplicate daily sales.
- Invalid totals or negative quantities return a useful error.
- Integration tests verify insert, update, and rollback behavior.

### Day 4: Authentication, tenant isolation, and sharing grants

**Features**

- Add users, password hashing, login, and JWT access tokens.
- Add current-user and current-organization dependencies.
- Enforce retailer/manufacturer/admin roles.
- Add sharing-grant create, list, and revoke operations.
- Add basic audit logging for grant changes.

**FastAPI concepts**

- OAuth2 bearer authentication.
- Security dependencies and scopes.
- Dependency composition.
- Authentication versus authorization.
- Testing with dependency overrides.

**Acceptance criteria**

- A valid user can log in and call an authorized endpoint.
- Invalid or expired tokens return `401`.
- A retailer cannot change another retailer's outlets or mappings.
- A retailer can grant and revoke access for a manufacturer.
- Cross-tenant tests demonstrate that unauthorized data is unavailable.

### Day 5: Manufacturer sales API

**Features**

- Implement the authorized manufacturer sales query.
- Add date, product, brand, category, retailer, outlet, geography, channel, units, and amount filters.
- Add validated sorting.
- Add cursor pagination and maximum page size.
- Write an audit record for each successful read.

**FastAPI concepts**

- Reusable query-parameter models.
- Complex dependencies.
- Response serialization.
- Pagination metadata.
- OpenAPI descriptions and examples.

**Acceptance criteria**

- A manufacturer sees only its products.
- A manufacturer sees only retailers with active grants.
- Revoking a grant immediately prevents subsequent reads.
- Combining multiple filters returns the expected intersection.
- Pagination has no duplicate or skipped records in deterministic tests.

### Day 6: Sales analytics

**Features**

- Implement sales summary analytics.
- Support grouping by day, product, brand, category, retailer, and state.
- Calculate units sold, returns, gross, discounts, net sales, and average selling price.
- Reuse the same authorization policy and filters as raw sales retrieval.
- Add empty-result and invalid-grouping behavior.

**FastAPI concepts**

- Enum query parameters.
- Typed aggregate response models.
- Service reuse.
- SQLAlchemy aggregation and grouping.
- Testing computed responses.

**Acceptance criteria**

- Aggregate totals match seeded raw records.
- Unauthorized products and retailers never affect totals.
- Every supported grouping returns a documented response shape.
- A date range greater than 366 days is rejected.
- Empty data returns `200` with an empty list.

### Day 7: Production hardening and delivery

**Features**

- Add consistent error responses and request IDs.
- Add structured request logging and timing middleware.
- Complete audit logging for sales upload and retrieval.
- Add CORS configuration controlled by settings.
- Add Dockerfile and complete Docker Compose application setup.
- Add unit and integration test suites.
- Add seed data and README usage examples.
- Run formatting, linting, tests, and migration checks.

**FastAPI concepts**

- Middleware.
- Custom exception handlers.
- CORS.
- Lifespan testing.
- Dependency overrides and test isolation.
- Deployment configuration.

**Acceptance criteria**

- The complete stack starts with documented commands.
- A clean database can be migrated and seeded.
- Swagger UI demonstrates login, upload, grants, queries, and analytics.
- Tests cover successful flows and tenant-isolation failures.
- Ruff checks pass.
- No secrets or consumer PII are present in the repository or logs.

## 12. MVP definition of done

The seven-day MVP is complete when this scenario works end to end:

1. An administrator creates one retailer and two manufacturers.
2. Manufacturers have products, and the retailer maps its SKUs to those products.
3. The retailer creates an outlet and uploads daily sales containing products from both manufacturers.
4. The retailer grants access to Manufacturer A but not Manufacturer B.
5. Manufacturer A authenticates and retrieves only its own sales lines.
6. Manufacturer A filters results and retrieves an accurate summary.
7. Manufacturer B cannot retrieve retailer data without a grant.
8. Re-uploading corrected sales updates the existing records.
9. Relevant upload, grant, and read actions appear in the audit log.
10. The complete behavior is covered by automated tests and runs through Docker Compose.

## 13. Future features after the MVP

- OAuth2 client-credentials authentication for machine-to-machine integrations.
- Excel bulk upload with validation reports.
- Asynchronous exports and expiring download links.
- Receipt-level basket analysis.
- Promotion and campaign effectiveness.
- Inventory snapshots and out-of-stock alerts.
- Rate limiting and manufacturer quotas.
- Webhooks when new retailer data becomes available.
- Data-retention configuration.
- Manufacturer dashboards.
- Forecasting and anomaly detection.
- Additional currencies, tax breakdowns, and unit conversions.

