# Email & Notifications

## Summary
Custom email sending, notification system, and templates for various business events including low stock alerts, expired raw materials, material request rate issues, email sent status tracking, auto-generated material requests, missing rate stock entries, and AI agent error notifications.

## Commits
| Hash | Message | Date |
|------|---------|------|
| cbf59ff51e | add notification for PR rate issue | 2026-02-06 |
| 5476c6a533 | ai: fix email status | 2025-10-31 |
| 67ecd15a11 | ai: fix email status | 2025-10-31 |
| 34e3492169 | move notification to inside function | 2025-10-15 |
| 883a7e738a | prod: add notification for draft PI | 2025-09-16 |
| d9a55615b5 | add error notification on background job | 2025-09-02 |
| 6a5403a01d | add settings if any email issue | 2025-09-02 |
| 705955555f | process email from new method | 2025-08-28 |
| 993df7e632 | add rizky email | 2025-07-25 |
| 228ee07e52 | split email with ai agent flow | 2025-07-17 |
| 65c2ca2014 | ignore security email | 2025-07-15 |
| 253a2b1b0e | add low stock alert notifications | 2025-06-25 |
| cb19f84d5a | add notification for auto PR created | 2025-06-25 |
| 423f296800 | add notification reorder level | 2025-06-19 |
| 4cd9fcbdfa | read email inbox and integrate with AI | 2025-03-27 |
| 6feb8b7ce2 | add email status | 2025-03-26 |
| d878615893 | add email status sent | 2025-03-26 |
| 7efc8eb9d6 | add last email value | 2025-03-25 |
| 7fe4721c95 | add last email value | 2025-03-25 |
| ee3ff663c6 | update notification system | 2025-01-22 |
| 7c39283992 | adjust email template | 2024-12-20 |
| 79ad1a3a2f | fix scrap issue notification | 2024-12-20 |
| bbaf83f5ff | expired raw material notification | 2024-12-19 |
| cc3dbf4c29 | included rizky in notification | 2023-12-07 |

## Affected Files

### Notification Definitions (FOMS Module)
- erpnext/foms/notification/auto_generated_material_request/
- erpnext/foms/notification/email_sent_status/
- erpnext/foms/notification/expired_raw_material/
- erpnext/foms/notification/low_stock_alert/
- erpnext/foms/notification/material_request_rate_issue/
- erpnext/foms/notification/new_draft_stock_entry_for_scrap/
- erpnext/foms/notification/product_waste_notification/
- erpnext/foms/notification/submit_invoice_draft/

### Notification Definitions (GP ERP Module)
- erpnext/gp_erp/notification/missing_rate_stock_entry/
- erpnext/gp_erp/notification/missing_work_order_rate/

### AI Agent Notifications
- erpnext/ai_agent/notification/ai_agent_not_working/

### Email Controller
- erpnext/controllers/email.py

### Email Templates
- erpnext/templates/emails/low_stock_alert.html

### Core Integration
- erpnext/controllers/erp.py
- erpnext/controllers/erp_api.py
- erpnext/controllers/ai.py
- erpnext/stock/reorder_item.py
- erpnext/stock/doctype/scrap_request/scrap_request.py
- erpnext/hooks.py

## Flow/Logic

### 1. Email Last-Used Default (`controllers/email.py`)
- `get_last_email_default(doctype, docname)` is a whitelisted function that retrieves the last email recipients/cc/bcc/template used for a given party.
- Determines party type (supplier for buying docs, customer for selling docs).
- Queries the Communication doctype joined with the source document to find the most recent email sent by the current user to the same party.
- Returns recipients, cc, bcc, and email_template to pre-fill the email dialog.

### 2. Low Stock Alert Notification
- Triggered from `erpnext/stock/reorder_item.py` during the scheduled reorder process.
- When projected qty falls below the reorder level, Material Requests are auto-created.
- The "Low Stock Alert" notification (custom event) sends email to Purchase Manager and Purchase User roles.
- Email template (`templates/emails/low_stock_alert.html`) shows items below safety stock with item code, safety stock level, current quantity, and warehouse.

### 3. Auto-Generated Material Request Notification
- Triggered as a custom event when a Material Request is auto-created from reorder levels.
- Sends to the PIC (person-in-charge) specified in the `pic` document field.
- Lists items with item code, warehouse, requested qty, UOM, and projected qty.

### 4. Material Request Rate Issue Notification
- Custom event triggered when a Material Request has items with >100% price increase.
- Sends to specific recipients (rizky@greenphyto.com, weiquan@greenphyto.com).
- Shows a table of items with current rate, new rate, and increase percentage.
- Subject includes alert emoji for visibility.

### 5. Expired Raw Material Notification
- Triggered on "New" event for Scrap Request documents where `system_generated == 1`.
- Sends to Stock Manager, Stock Master Manager, and CEO roles.
- Excludes specific recipients (doreen@greenphyto.com).
- Lists products approaching expiration within 30 days with batch number, qty, UOM, and expiry date.

### 6. Email Sent Status Notification
- Custom event on Communication documents.
- Notifies the sender (via `receiver_by_document_field: sender`) when their email has been successfully sent.
- Provides a link back to the source document.

### 7. Missing Rate Stock Entry Notification (GP ERP)
- Custom event triggered when a Stock Entry is submitted with zero-rate items.
- Checks `item.basic_amount == 0` for each item row.
- Sends to specific recipients with a table of zero-rate items (item code, name, qty, rate, amount).

### 8. Reorder Item Flow Enhancement
- `reorder_item.py` groups Material Requests by company and PIC (person-in-charge).
- Each item reorder entry includes a `pic` field from the Item Reorder child table.
- Supports warehouse groups for aggregated projected qty checks.
- Deduplicates existing rows using `find_existing_row()` to prevent duplicate MR items.
- After creating MRs, triggers the Auto-Generated Material Request notification via `send_notif` flag.

## Dependencies
- Frappe Notification framework (standard Frappe notification system)
- Communication doctype for email tracking
- Stock Settings (`auto_indent` flag to enable auto reorder)
- Item Reorder child table (defines reorder levels per warehouse)
- Scrap Request module (for expired raw material flow)
- AI Agent module (for AI-related error notifications)

## Notes
- Notifications use the "Custom" event type which means they are triggered programmatically via `frappe.enqueue_doc` or direct calls, not automatically by the framework.
- The `email_sent_status` notification tracks when Communications are sent, providing delivery confirmation to users.
- The low stock alert uses a dedicated HTML template while other notifications use inline HTML in the notification JSON.
- The `from_scheduler` parameter in some flows distinguishes between user-initiated and scheduler-initiated actions.
- Security emails are explicitly ignored in the email processing flow to avoid processing automated security notifications.
