# Migration Plan: Move GP customizations out of std ERPNext doctype files into GP override classes

Status: PLAN ONLY. No files edited yet.
Baseline for comparison: pristine upstream ERPNext `v15.95.2` (commit `621558a30c`).
GP override classes live in `erpnext/gp_erp/controllers/`, registered in `erpnext/hooks.py` (`override_doctype_class`).

## Key finding

Most "customizations in std files" are leftovers from before the override-class pattern. In many cases the GP class **already** carries the logic. But several std-file edits are still **load-bearing**:
- GP classes rely on `super().validate()` running the std-file body (stock_entry, delivery_note, job_card).
- Some GP helper methods exist but are **never wired in** because the GP class has no `validate()` (material_request, work_order).

So this is NOT a simple "revert std files" job. Each file needs its own handling.

---

## Category A — Can move cleanly to GP class / already covered

### 1. sales_order.py  (SalesOrderGP exists) — SAFE TO REVERT
All in-class edits already exist identically in `SalesOrderGP`:
- `validate_po` pending_po/is_pledge branches  -> already in class (calls super()).
- `update_work_order_reference` -> already in class.
- `update_work_progress` -> already in class.
Action: revert `erpnext/selling/doctype/sales_order/sales_order.py` to pristine. No class change needed.

---

## Category B — Add method(s) to GP class, then revert std file

### 2. buying_settings.py  (BuyingSettingsGP exists)
Std edits:
- `update_supplier_account` — DIVERGENT: std version has new signature `(self, series_filter=None, mode="Only if not set")` + "Replace all"/"Only if not set" branching. Class has old `(self)` always-replace version.
- `get_series_pr_required(series)` — module-level function, but WRONGLY placed inside the class body in the std file (placement bug).
Actions:
1. Update `BuyingSettingsGP.update_supplier_account` to the new signature + mode logic.
2. Add module-level `get_series_pr_required(series)` to `gp_erp/controllers/buying/buying_settings.py`.
3. Update any caller/JS referencing `get_series_pr_required` to the new module path.
4. Revert std `buying_settings.py` to pristine.

### 3. supplier.py  (SupplierGP exists)
Std edit: `create_internal_supplier` guard `if not self.represents_company: return` — NOT in class.
(Also `has_permission` module func — see Category D.)
Actions:
1. Add `create_internal_supplier` override to `SupplierGP` (guard + `super().create_internal_supplier()`).
2. Revert the in-class part of std `supplier.py`. Keep/relocate `has_permission` per Category D.

### 4. delivery_note.py  (DeliveryNoteGP exists)
Std edit: `validate_packed_qty` packing-slip rework — NOT in class; currently reached via `super().validate()`.
Actions:
1. Add `validate_packed_qty` override to `DeliveryNoteGP` carrying the packing-slip logic.
2. Revert std `delivery_note.py` to pristine.

### 5. item.py  (ItemGP exists)
Std edits:
- `get_item_material_group(self, set_data=False)` — new method, NOT in class.
- `set_opening_stock` `not frappe.flags.in_test` guard — NOT in class.
- `parse_material_group_series` module func — already duplicated in class.
- `update_item_pic`, `get_default_pic` (whitelisted) — module-level (Category D).
Actions:
1. Add `get_item_material_group` to `ItemGP`.
2. Add `before_insert`/`set_opening_stock` override to `ItemGP` carrying the in_test guard.
3. Move whitelisted `update_item_pic`/`get_default_pic` per Category D.
4. Revert std `item.py` to pristine.

### 6. material_request.py  (MaterialRequestGP exists)
Std edits:
- Helpers `set_is_low_amount`, `check_attachment`, `set_expense_code` — ALREADY in class.
- `get_attachments` — class inlines it; add if other callers need it.
- `validate()` wiring these calls — MISSING: MaterialRequestGP has no `validate()`. The std `validate` edit is the only thing wiring the helpers. Reverting now = dead code.
- Module funcs `validate_purchase_request*`, `has_permission`, `get_permission_query_conditions`, `confirm_workflow_action_page` (Category D).
Actions:
1. Add `validate()` to `MaterialRequestGP` that calls `super().validate()` then `set_is_low_amount()`, `check_attachment()`, `set_expense_code()`.
2. Add `get_attachments` if referenced elsewhere.
3. Handle module funcs per Category D.
4. Revert in-class part of std `material_request.py`.

### 7. job_card.py  (JobCardGP exists)
Std edits:
- `set_status` single_complete — ALREADY in class (superset).
- `validate_job_card_qty` gutted to `pass` — NOT in class; reverting restores the overproduction throw.
Actions:
1. Add `def validate_job_card_qty(self): pass` to `JobCardGP` (or a proper override reflecting intent).
2. Revert std `job_card.py` to pristine.

---

## Category C — Large / high-risk (recommend separate dedicated pass)

### 8. work_order.py  (WorkOrderGP exists)  [LARGE: +519/-29]
Already in class (10 helpers): autoname, validate_non_stock_items, validate_cost_editing, write_opr_version, update_sales_order, get_workstation_cost, set_packet_size, get_packaging_from_order, set_is_salad_item, calculate_operating_cost.
MISSING from class (must add before reverting std):
- `validate` — wires get_workstation_cost + packaging/salad/non-stock helpers (NONE currently called by the class).
- `on_update_after_submit`
- `update_batch_produced_qty` (also referenced by stock_entry edit)
- `set_status` (full stock-entry-driven rework + single_complete + Closed + update_sales_order(state="Finish"))
- `update_work_order_qty` guard (`if not allowance_percentage: return`)
Actions: add the above to WorkOrderGP (carrying exact logic from std diff), then revert std work_order.py. Verify thoroughly.

### 9. stock_entry.py  (StockEntryGP exists)  [LARGE: +115/-16]
StockEntryGP overrides `validate` + `validate_finished_goods` but RELIES on `super().validate()` for several std edits.
MISSING from class (must add before reverting std):
- `get_previous_rate` (new)
- `set_expense_account` (new; needs imports get_warehouse_account_map, get_item_account)
- `validate` behaviors: auto_repack ignore_linked, difference-account pass, operation-completion allowance
- `update_work_order` -> `pro_doc.update_batch_produced_qty(self)` call (depends on pair 8)
- single_complete material-consumption branch
- bundle qty sync in `add_to_stock_entry_detail`
- `get_stock_entry_data` module func field additions (basic_rate, basic_amount)
Actions: add/override the above in StockEntryGP, then revert std stock_entry.py. Depends on #8. Verify thoroughly.

---

## Category D — CANNOT move into a Doctype class (structural)

These are module-level functions. They belong in hooks, not an override class.

- `has_permission(doc, user)` entries (supplier, customer, material_request) -> register under `has_permission` in hooks.py, point to a GP module.
- Whitelisted methods (customer `get_customer_list`, item `update_item_pic`/`get_default_pic`, material_request validators, work_order `make_scrap_materials`/`get_foms_task_status`, bulk_transaction_log `retry_failing_transaction`, asset `check_unposted_depr_before_disposal`) -> move function body to a GP module and register via `override_whitelisted_methods` OR update all callers/JS to the new path.
- Scheduler/util functions (currency_exchange `save_main_currency_rate`/`fetch_month_rate`, batch helpers, warehouse `create_warehouse`, gl_entry `allow_cost_center_missing`, depreciation helpers) -> move to a GP util module and update callers / scheduler_events in hooks.

Files that are ONLY Category D (revert std file after relocating functions):
- gl_entry.py, customer.py, batch.py, warehouse.py, depreciation.py, bulk_transaction_log.py, currency_exchange.py

---

## Category E — Nothing to migrate

- sales_invoice_item.py — only auto-generated DF type hints. Leave or revert to pristine; no logic.
- company.py — only type hints + module func `switch_to_company_admin`; no Company GP class. If keeping, treat `switch_to_company_admin` as Category D. Otherwise leave.

### packing_slip.py — needs NEW GP class
Has an in-class edit (`calculate_net_weight_pkg` rework) but NO GP override class and NO hook registration. To follow the pattern: create `PackingSlipGP`, register in `override_doctype_class`, move the method, then revert std file. (Confirm whether Packing Slip is actually used before investing effort.)

---

## Recommended execution order
1. sales_order.py (trivial revert).
2. Category B: job_card, supplier, delivery_note, item, material_request, buying_settings.
3. Category D relocation (hooks + whitelisted + scheduler) — one module at a time, update callers.
4. Category C: work_order then stock_entry (stock_entry depends on work_order).
5. packing_slip (only if needed; create new GP class).

## Verification after each file
- `bench --site test5-15 execute <temp check>` to confirm `get_controller()` + the moved method resolves.
- Re-run the override-class load test (all GP classes import cleanly).
- Diff std file == pristine (`git diff 621558a30c -- <file>` empty) once migrated.
- For whitelisted/has_permission moves, grep JS and python for old dotted paths.
