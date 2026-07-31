# Swagger API Documentation

## Summary
Interactive Swagger UI for GP ERP API endpoints, served as a web page at `/swagger`. Provides API documentation with example endpoints, session-based authentication, and JSON API specification.

## Commits
| Hash | Message | Date |
|------|---------|------|
| 1a43e41e2f | add example api to swagger | 2026-07-01 |
| 93b5bfe19e | save login session swagger | 2024-03-18 |
| 3b0675e329 | create recipe by swagger | 2024-03-18 |
| 26a3f018c2 | adjust swagger to push data | 2024-03-18 |
| 91d2e852fb | ini swagger documentation | 2024-03-18 |

## Affected Files
- erpnext/www/swagger/__init__.py
- erpnext/www/swagger/index.html
- erpnext/www/swagger/index.py
- erpnext/www/swagger/api.json
- erpnext/www/swagger/api_refs.json
- erpnext/controllers/erp_api.py
- erpnext/controllers/foms.py

## Flow/Logic
1. **Web Page Setup**:
   - Served at `/swagger` via Frappe's `www` directory convention.
   - `index.py` provides page context with CSRF token from `frappe.sessions.get_csrf_token()` for authenticated API calls.
   - `index.html` renders the Swagger UI loading the `api.json` specification.

2. **API Specification** (`api.json`):
   - OpenAPI/Swagger JSON document defining available GP ERP API endpoints.
   - Includes endpoint definitions, request/response schemas, and example payloads.
   - `api_refs.json` contains additional reference schemas.

3. **Authentication**:
   - Uses Frappe session-based auth (CSRF token injected into Swagger UI).
   - Login session is preserved so authenticated users can test endpoints directly from the UI.

4. **Documented Endpoints** (via `erp_api.py` and `foms.py`):
   - Forecast/lead time APIs (receive_forecast, get_lead_time).
   - Recipe creation endpoints.
   - Data push endpoints for external system integration.

5. **Migration Note**: Originally at `/gp-swagger`, later moved to `/swagger` (the `www/gp-swagger/` path was the initial location).

## Dependencies
- Frappe www page serving mechanism
- Swagger UI (embedded in index.html)
- Frappe session/CSRF authentication
- erp_api.py controller endpoints
- foms.py controller endpoints

## Notes
- The CSRF token is injected server-side via `get_context()` to enable authenticated API testing without manual token management.
- The Swagger page is accessible to logged-in users only (Frappe session required).
- API spec is maintained manually in `api.json` — new endpoints must be added to this file for documentation.
- The old path `www/gp-swagger/` may still exist in some branches but the canonical location is `www/swagger/`.
