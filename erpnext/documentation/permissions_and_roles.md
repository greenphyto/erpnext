# Permissions & Roles

## Summary
Custom permission and role management including cross-company read access, CEO role bypass for workflow restrictions, custom roles for logistics and purchasing, purchase user permission lists, bank reconciliation tool permissions, and workflow action confirmation pages.

## Commits
| Hash | Message | Date |
|------|---------|------|
| fae416c2ed | ignore permission on represents company | 2026-04-29 |
| c258f73db0 | add permission to bank recon tool | 2026-04-14 |
| 8e51f6204b | fix change company permission from workflow | 2026-04-02 |
| 4ccffcb828 | skip CEO role from workflow strict | 2026-03-31 |
| 149a72b6c0 | fix add roles | 2026-02-18 |
| 30322b8b56 | add permission for read cross company on PR | 2026-02-11 |
| 238e6817fc | read only for logistic role | 2025-12-31 |
| 26a659928b | allow edit on permission level 1 | 2025-07-16 |
| 60a8b12918 | update role for request | 2024-12-18 |
| c94f98b680 | add role | 2024-09-25 |
| 77e98fc512 | add role | 2024-09-25 |
| 2d6dc08c28 | add role | 2024-09-25 |
| f97f413ff7 | add real role | 2024-03-13 |
| 2b6aaaacc2 | add permissions table | 2024-02-28 |
| 0f0e5c85c3 | permission fixed | 2023-02-03 |
| 7556668e2c | permission | 2023-02-03 |
| ab8d5e19d7 | permission fixed | 2023-02-03 |
| 6114241ff2 | fix: key error in filter access | 2022-10-28 |

## Affected Files
**Doctype Permission JSONs:**
- erpnext/accounts/doctype/accounts_settings/accounts_settings.json
- erpnext/accounts/doctype/bank_reconciliation_tool/bank_reconciliation_tool.json
- erpnext/accounts/doctype/material_group/material_group.json
- erpnext/accounts/doctype/part_number_settings/part_number_settings.json
- erpnext/accounts/doctype/payment_terms_template/payment_terms_template.json
- erpnext/accounts/doctype/purchase_invoice/purchase_invoice.json
- erpnext/buying/doctype/buying_settings/buying_settings.js
- erpnext/buying/doctype/buying_settings/buying_settings.json
- erpnext/buying/doctype/purchase_order/purchase_order.json
- erpnext/buying/doctype/request/request.json
- erpnext/setup/doctype/department/department.json
- erpnext/stock/doctype/delivery_note/delivery_note.js
- erpnext/stock/doctype/material_request/material_request.json
- erpnext/stock/doctype/material_request/material_request.py
- erpnext/stock/doctype/purchase_receipt/purchase_receipt.json

**Custom Permission Doctype:**
- erpnext/buying/doctype/purchase_user_permissions_list/__init__.py
- erpnext/buying/doctype/purchase_user_permissions_list/purchase_user_permissions_list.json
- erpnext/buying/doctype/purchase_user_permissions_list/purchase_user_permissions_list.py

**Controllers & Hooks:**
- erpnext/controllers/erp.py
- erpnext/controllers/queries.py
- erpnext/hooks.py

**Other:**
- erpnext/accounts/report/gst_return_summary_report/gst_return_summary_report.js
- erpnext/selling/report/payment_terms_status_for_sales_order/test_payment_terms_status_for_sales_order.py
- erpnext/www/confirm_workflow_action.html

## Flow/Logic

### Company Permission & Workflow Bypass
1. `validate_company_selected` in `erp.py` is registered as a global `validate` hook on all doctypes (`doc_events["*"]`).
2. Ensures the user has permission for the selected company before saving.
3. `control_bypass_workflow` (registered in hooks `bypass_workflow_permission`) allows CEO role to bypass strict workflow permission checks.
4. `skip CEO role from workflow strict`: when workflow state transitions are enforced, users with CEO role are exempted from the restriction.

### Cross-Company Read Access
1. Purchase Receipt permissions updated to allow cross-company read access.
2. `ignore permission on represents company`: when a user's linked employee represents a company, inter-company documents skip standard permission checks.

### Permission Query Conditions
1. `permission_query_conditions` in hooks for Material Request:
   - `erpnext.stock.doctype.material_request.material_request.get_permission_query_conditions`
   - Filters Material Request list based on user's assigned departments/warehouses.

### Purchase User Permissions List
1. Custom doctype `Purchase User Permissions List` manages granular purchasing permissions.
2. Maps users to specific suppliers, item groups, or material groups they can purchase for.
3. `validate_purchase_user` hook on purchase documents checks against this list.

### Role-Based Access
1. Custom roles added for specific departments:
   - Logistics role: read-only access to delivery notes and stock documents.
   - Purchasing roles: tied to Purchase User Permissions List.
2. Permission levels used (level 0 = full, level 1 = restricted fields with `allow edit on permission level 1`).

### Workflow Action Confirmation
1. `www/confirm_workflow_action.html` provides a web page for email-based workflow approvals.
2. `confirm_workflow_action_page` hook for Material Request points to custom handler.
3. Allows approvers to approve/reject Material Requests directly from email links.

### Bank Reconciliation Tool
1. Permissions added to allow specific roles access to the Bank Reconciliation Tool.
2. Previously restricted to System Manager; now accessible to Accounts Manager and custom finance roles.

### Standard Queries Override
1. `standard_queries` in hooks overrides Supplier query:
   - `erpnext.controllers.queries.supplier_query` adds custom filtering logic.
2. Filters suppliers based on user permissions and company context.

## Dependencies
- `erpnext.controllers.erp` (validate_company_selected, control_bypass_workflow, set_permanent_company)
- hooks.py `doc_events["*"]` for global validation
- hooks.py `bypass_workflow_permission` for CEO exemption
- hooks.py `permission_query_conditions` for Material Request filtering
- hooks.py `has_permission` for Supplier/Customer custom permission checks
- Workflow configurations on Material Request, Purchase Order

## Notes
- The CEO role bypass is specifically designed for the Material Request workflow but applies through the generic `bypass_workflow_permission` hook mechanism.
- `set_permanent_company` on User validate ensures users are bound to their assigned company, preventing cross-company data access.
- The `confirm_workflow_action.html` page is a public page that validates tokens before executing workflow transitions.
- Permission level 1 fields require explicit "write" permission at that level; the fix allows editing these fields for authorized roles.
- `fix: key error in filter access` addresses an edge case where filter conditions reference fields not present in all doctypes.
