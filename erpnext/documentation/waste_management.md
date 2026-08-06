# Waste Tracking & Notification

## Summary
Product waste email notification triggered on Stock Entry submission for expired products, scrap waste creation from stopped Work Orders, and waste type material handling in stock entries.

## Commits
| Hash | Message | Date |
|------|---------|------|
| c549c60ce4 | update email waste template | 2026-07-09 |
| b984b42324 | scrap waste stopped work order | 2025-05-16 |
| 6d1cb596d3 | update product waste | 2025-01-22 |
| 65f285f55a | add waste type materials | 2024-12-27 |
| 0970166d7f | notification for product waste | 2024-12-19 |

## Affected Files
- erpnext/foms/notification/product_waste_notification/__init__.py
- erpnext/foms/notification/product_waste_notification/product_waste_notification.json
- erpnext/foms/notification/product_waste_notification/product_waste_notification.py
- erpnext/manufacturing/doctype/work_order/work_order.js
- erpnext/manufacturing/doctype/work_order/work_order.py
- erpnext/patches/v14_0/modify_stock_entry_type2.py
- erpnext/stock/doctype/scrap_request/scrap_request.py

## Flow/Logic
1. **Product Waste Notification** (`product_waste_notification.json`):
   - Frappe Notification (standard, Email channel) on Stock Entry document type.
   - **Trigger**: On Submit event.
   - **Condition**: `doc.system_generated == 1 and doc.request_no == "Expired Product" and doc.purpose == "Material Issue" and doc.docstatus == 1`.
   - **Recipients**: Users with "Waste Manager" role.
   - **Email Template**: HTML table listing each item's product name, batch number, warehouse, qty, and UOM from the Stock Entry items.
   - **Subject**: "Product Waste {posting_date}".
   - **Sender**: "ERP" (erp@greenphyto.com).

2. **Scrap Waste from Stopped Work Order** (`work_order.py` → `make_scrap_materials`):
   - Triggered from Work Order JS via "Scrap Components" button (shown when WO is Stopped with status conditions).
   - Calls `get_available_materials(work_order, percentage)` to find non-consumed raw materials.
   - Creates a Stock Entry with:
     - `stock_entry_type_view = "Waste Materials"`
     - `purpose = "Material Issue"`
     - `request_no = "Scrap Item from Stoped Work Order"`
     - `is_return = 1`
   - Each item row is marked `is_scrap_item = 1` with `expense_account` set to company's `production_attrition_expense_account`.
   - Quantities are rounded for UOMs that require whole numbers.
   - Remarks: "Waste materials from Work Order {name}".

3. **Work Order JS** (`work_order.js`):
   - Adds "Scrap Components" primary button when Work Order is in appropriate stopped/completed state.
   - Button triggers `create_stock_return_entry` which calls `make_scrap_materials` and routes to the new Stock Entry form.

4. **Waste Type Materials** (`modify_stock_entry_type2.py` patch):
   - Data migration patch that adds/modifies Stock Entry Type records to support "Waste Materials" type.

5. **Scrap Request Integration** (`scrap_request.py`):
   - Related doctype for managing scrap/waste requests that feed into stock entries.

## Dependencies
- Frappe Notification framework
- Stock Entry doctype (system_generated flag, request_no field)
- Work Order doctype (status management, BOM items)
- Stock Entry Type configuration
- Company settings (production_attrition_expense_account)
- "Waste Manager" role

## Notes
- The notification only fires for system-generated Stock Entries with `request_no == "Expired Product"` — manual waste entries won't trigger it.
- The `make_scrap_materials` function uses WIP warehouse from FOMS integration settings.
- The email template displays yesterday's date as the waste date (`frappe.utils.add_days(today(), -1)`).
- Scrap from stopped Work Orders uses the `production_attrition_expense_account` from Company defaults — this must be configured.
