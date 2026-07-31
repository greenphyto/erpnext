# Patches & Migration

## Summary
Data patches and migration scripts for GP custom fields, default settings, and data fixes. Includes creating non-stock items, asset change logs, company settings updates, delivery note SI references, and GP-specific patches for bank purposes, cost center defaults, and batch status management.

## Commits
| Hash | Message | Date |
|------|---------|------|
| 8007304a00 | add ignore patches files | 2026-06-17 |
| 3653547afe | remove patch log | 2024-12-18 |
| 5a3e0a447b | remove patch log | 2024-12-18 |
| 110e1687c7 | fix patches | 2024-12-17 |
| 93cb19068c | remove patches | 2024-12-17 |
| 47aa61aa90 | add patches | 2024-12-17 |
| 3068ccf84f | fix patches | 2024-12-05 |
| de5bd314be | add patches | 2024-12-03 |
| 4d6c2a5599 | add patches | 2023-12-28 |
| 50b3b2e1ef | add patches for non stock | 2023-10-11 |
| 683b12fc11 | update patches | 2023-09-22 |

## Affected Files
**Patch Registry:**
- erpnext/patches.txt

**v14_0 Patches:**
- erpnext/patches/v14_0/create_non_stock_item.py
- erpnext/patches/v14_0/make_asset_change_log.py
- erpnext/patches/v14_0/update_account_settings.py
- erpnext/patches/v14_0/update_company_settings.py
- erpnext/patches/v14_0/update_dn_reference_to_si.py

**GP-Specific Patches:**
- erpnext/patches/gp/add_bank_purpose.py
- erpnext/patches/gp/add_bank_standart_sg.py
- erpnext/patches/gp/set_default_cost_center_in_account.py
- erpnext/patches/gp/set_batch_status.py

**Other:**
- .gitignore (ignore patches files)

## Flow/Logic

### patches.txt Registration
Patches are registered at the end of `patches.txt` in execution order:
```
erpnext.patches.v14_0.update_dn_reference_to_si
erpnext.patches.v14_0.create_non_stock_item
erpnext.patches.v14_0.make_asset_change_log
erpnext.patches.v14_0.fix_manufacturing
erpnext.patches.v14_0.modify_stock_entry_type2
erpnext.patches.v14_0.add_operation_default
erpnext.patches.v14_0.set_default_warehouse_production
erpnext.patches.v14_0.update_company_settings
erpnext.patches.gp.add_bank_purpose
erpnext.patches.gp.add_bank_standart_sg
erpnext.patches.gp.set_default_cost_center_in_account
erpnext.patches.gp.set_batch_status
```

### create_non_stock_item.py
1. Checks if `Buying Settings.non_stock_item` is already set; skips if so.
2. Creates a new Item with:
   - `item_code`: "Non-stock"
   - `is_stock_item`: 0
   - `is_fixed_asset`: 0
   - `include_item_in_manufacturing`: 0
   - `stock_uom`: "Nos"
   - `item_group`: root item group (lft=1)
3. Sets `Buying Settings.non_stock_item` to the new item name.
4. Used for non-stock purchase invoices where no physical inventory is tracked.

### set_default_cost_center_in_account.py
1. Maps specific GPL accounts to their correct default cost centers.
2. Categories mapped:
   - **Accumulated Depreciation accounts** -> "1020 - Finance - GPL"
   - **Depreciation expense accounts** -> "1020 - Finance - GPL"
   - **Sales Income accounts** -> "1040 - Sales - GPL"
   - **HR-related accounts** -> "1030 - HR - GPL"
   - **Infrastructure accounts** -> "1080 - Infrastructure & Maintenance - GPL"
   - **Production accounts** -> "2020 - Production-WH - GPL"
   - **System accounts** -> "5010 - System - GPL"
   - **CEO Office accounts** -> "1090 - CEO Office - GPL"
3. Iterates mapping, finds Account by full name, finds Cost Center by name, updates `Account.cost_center`.
4. Skips accounts with conflicting cost centers across voucher types (e.g., Legal & Professional Fees).
5. Commits all changes and prints summary.

### add_bank_purpose.py
1. Inserts standard Singapore bank payment purpose codes into `Bank Purpose` doctype.
2. 54 purpose codes including: SALA (Salary), SUPP (Supplier Payment), RENT, LOAN, TAXS, etc.
3. Checks for existing records by code before inserting to prevent duplicates.
4. Used by UOB payment integration for FAST/GIRO transfers.

### add_bank_standart_sg.py
1. Inserts standard Singapore bank records (bank names, SWIFT codes).
2. Similar pattern to bank purpose - inserts only if not existing.

### set_batch_status.py
1. Updates batch status field for existing batches.
2. Ensures batch lifecycle states are consistent after schema changes.

### update_dn_reference_to_si.py
1. Fixes references between Delivery Notes and Sales Invoices.
2. Updates linking fields to maintain document traceability.

### update_company_settings.py
1. Sets GP-specific default values in Company doctype.
2. Configures default accounts, warehouses, and other company-level settings.

### make_asset_change_log.py
1. Creates asset change log entries for audit trail.
2. Records historical asset modifications.

### Patch Log Management
- Several commits deal with removing/fixing patch logs (`Patch Log` doctype).
- When patches fail or need re-running, their log entries are removed to allow re-execution.
- `add ignore patches files` in .gitignore prevents local patch state files from being committed.

## Dependencies
- `frappe.patches` framework (patches.txt execution engine)
- Buying Settings doctype (non_stock_item field)
- Account doctype (cost_center field)
- Bank Purpose doctype (GP custom)
- Item doctype (for non-stock item creation)
- Company settings (default accounts/warehouses)

## Notes
- Patches run once per site during `bench migrate`. Re-running requires deleting the corresponding `Patch Log` entry.
- The `erpnext/patches/gp/` directory is GP-specific and not present in standard ERPNext.
- Cost center mapping in `set_default_cost_center_in_account.py` is hardcoded for GPL company. Other companies would need their own mappings.
- Bank purpose codes follow Singapore FAST payment standard (ISO 20022 purpose codes).
- The `.gitignore` addition for patch files prevents conflicts when multiple developers run patches locally.
- Some patches reference other custom patches (e.g., `fix_manufacturing`, `modify_stock_entry_type2`, `add_operation_default`) that set up manufacturing defaults for FOMS integration.
