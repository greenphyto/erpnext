# Bug Fixes, Minor Changes & Maintenance

## Summary

Combined documentation for non-feature changes across the GP ERPNext v14 codebase: bug fixes, code cleanup, testing improvements, and minor enhancements that don't warrant individual feature documentation.

## Statistics

| Category | Commits |
|----------|---------|
| Bug Fixes | 353 |
| Other/Miscellaneous | 714 |
| Chores & Cleanup | 94 |
| Testing | 16 |
| Hooks & Customization | 15 |
| Patches & Migration | 11 |
| Auth & Users | 3 |
| HR & Payroll | 3 |
| CRM | 2 |
| Website | 1 |
| Dashboard | 4 |
| Purchase Order | 4 |
| **Total** | **1,220** |

## Bug Fixes by Module

### Accounts & General Ledger

- Fixed GL entry creation with correct against account values and debit/credit rows
- Fixed duplicate GL entries and false ledger creation issues
- Fixed ledger amount calculations and closing totals
- Fixed bank reconciliation tool opening balance miss and ambiguity issues
- Fixed against account setting for debit notes and payment entries
- Fixed GST tax amount sources and return values
- Fixed journal entry processing and finish ledger entries
- Fixed near-zero value handling in accounting entries
- Fixed advance paid amount reset on order cancel and amend
- Fixed party type and party mandatory on updating outstanding

### Stock & Inventory

- Fixed stock ledger entry issues and qty after transaction calculations
- Fixed stock integration on GRN and missing GL entry for GRN
- Fixed update last purchase rate and valuation rate issues
- Fixed stock recon cancel and submit flow
- Fixed packing slip issues and missing module references
- Fixed expired product handling for multi-entity setups
- Fixed material request type and qty calculations
- Fixed stock issue notifications and partial stock issue validation
- Fixed conversion factor calculations in Production Plan
- Fixed duplicate entry creation in Stock Entry

### Manufacturing

- Fixed produced qty and status updates on Work Orders
- Fixed WO status when cancelled return
- Fixed finish goods amount equal to raw materials amount
- Fixed total qty on manufacture finish
- Fixed operation raw material mapping
- Fixed manufacturing expense row and additional cost issues
- Fixed finish goods stock account selection
- Fixed Material Consumption option with Skip Transfer to WIP
- Fixed scrap accounting from previous amount calculations
- Fixed workstation name references

### Selling & Delivery

- Fixed missing reference SO in documents
- Fixed delivery order expiry date and draft DO issues
- Fixed Consignment Order cancel flow and status
- Fixed discount amount and percentage calculations
- Fixed item name missing in transactions
- Fixed rate and price list rule resets
- Fixed billed amount value mapping

### Buying & Purchase

- Fixed Purchase Receipt timeout error and missing doc references
- Fixed purchase receipt bug and read-only field issues
- Fixed PO date none handling and pull PO flow
- Fixed schedule date missing in purchase documents
- Fixed net amount mapping and key PE map
- Fixed discount issues in buying transactions
- Fixed auto indent issues

### Subcontracting & SCR

- Fixed consumed_qty based on received_qty in Subcontracting Receipt
- Fixed rejected-qty handling in return SCR
- Fixed consumed_qty read-only in SCR Supplied Items
- Fixed Internal Transfer Material Request cycle and tracking

### UI & UX

- Fixed table layout with percentage column widths
- Fixed POS item selector image border radius
- Fixed CSS and missing selector issues
- Fixed QR code styling
- Fixed button updates and missing data displays
- Fixed Scan Barcode UX improvements

### General / Cross-Module

- Fixed numerous typo and syntax errors across the codebase
- Fixed date format handling (dd/mm/yy and yyyy-mm-dd from CSV)
- Fixed add_button signature for Frappe v14 compatibility
- Fixed circular import issues
- Fixed status percent rounding
- Fixed various None/null guard issues
- Fixed JSON dump errors and bad JSON handling
- Fixed allow on submit field behaviors
- Fixed inventory dimension duplicate custom fields

## Chores & Cleanup

- Removed debugging statements and console logs across modules (20+ occurrences)
- Removed unused functions, variables, and libraries
- Resolved linting issues and code formatting
- Refactored Packing Slip: moved JS validations to Python, removed Get Items button
- Refactored job_card.py queries to use Query Builder
- Removed deprecated method usage (backport from upstream)
- Split delete GL utility function into two separate functions
- Refactored Exchange Rate Revaluation to submit through background job
- Added German translations
- Added translation functions to Bank Reconciliation Tool and report files
- Improved translatable strings in stock_ageing.py and other reports
- Linked SCR Return in SCR Dashboard
- Added Material Request Reference in Purchase Receipt Dashboard
- Removed AI Agent module (deprecated)
- Removed unused text below barcode, unit price display changes
- Managed deleted document tracking and expired stock removal

## Testing

- Added test cases for Packing Slip functionality
- Added test cases for consumed_qty in Subcontracting Receipt
- Added test case for workstation type validation
- Added test case for Material Request internal transfer
- Fixed existing test cases for supplied-items consumed_qty
- Added scheduler tests and CI integration tests
- Refactored tests to use @change_settings decorator where possible

## Hooks & Customization

- Added AI Agent Memory auto-update on Purchase Invoice submit
- Registered custom validate for purchase user in hooks
- Added custom bucket and folder configuration for file storage
- Moved custom AI fields to customize form
- Added custom footer support
- Moved triggers to hooks for better modularity
- Added custom date handling in AI operations
- Set posting date equal to custom date for consistency
- Added custom account for direct scrap entry submission
- Registered custom validation functions in hooks

## Minor Features

### Auth & Users

- Added ability to disable user access for sales manager role only
- Added purchase user role and permissions
- Added exclude user from notification settings

### HR & Payroll

- Added PO number validation (throw if exists)
- Updated employee.js UI
- Added multi-department support in employee records

### CRM

- Enabled quick entry on Lead doctype
- Added lead time validation on Request

### Website

- Initialized bulk approval page for web interface

### Dashboard

- Added dashboard links for various modules
- Added UOB dashboard link integration
- Updated dashboard for Salad product line
- Added dashboard views for new doctypes

### Purchase Order

- Added purchase order naming series configuration
- Added complete free text field in Purchase Order
- Updated purchase_order.js UI improvements

## Patches & Migration

See [patches_and_migration.md](./patches_and_migration.md) for detailed documentation on data migration patches.

## Notes

- Many bug fixes are iterative (fix, then fix again) indicating complex business logic around manufacturing costs, GL entries, and multi-company transactions
- The "Other/Miscellaneous" category (714 commits) includes incremental development work on features like:
  - UOB bank integration (bulk approval, SWIFT code validation, payment processing)
  - AI Agent integration (vision agent, OpenAI library, email invoice processing)
  - Consignment Order workflow
  - Scrap Request management
  - Product variance cost reporting
  - QR code generation
  - Minio backup management
  - Financial statement formulas (P&L, Balance Sheet, Cashflow)
  - Weight-based calculations and precision improvements
  - XML file generation for bank payments
- Precision improvements were applied extensively (4-7 decimal places) for weight and rate calculations
- CI/CD pipeline was set up and maintained across multiple iterations (prod, dev, candidate environments)
