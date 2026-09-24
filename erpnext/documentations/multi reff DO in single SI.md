# Multi-reference Delivery Notes and Sales Orders in One Sales Invoice

## Objective

Support one Sales Invoice containing items from multiple Delivery Notes and Sales Orders while keeping mapping, grouping, batch handling, billing status, and cancellation consistent with ERPNext.

Supported actions:

- Get Items From > Delivery Note
- Get Items From > Sales Order
- Map multiple source documents into one Sales Invoice
- Group rows by `item_code`, `uom`, and `batch_no`
- Preserve every source relationship through custom references
- Update Sales Order and Delivery Note billing status on submit and cancel

## Source code

Main files:

- `accounts/doctype/sales_invoice/sales_invoice.js`
- `public/js/utils.js`
- `stock/doctype/delivery_note/delivery_note.py`
- `selling/doctype/sales_order/sales_order.py`
- `accounts/doctype/sales_invoice/sales_invoice.py`
- `accounts/doctype/sales_invoice_item/sales_invoice_item.json`
- `hooks.py`

## User flow

1. User opens Sales Invoice.
2. User selects Sales Orders or Delivery Notes.
3. Dialog displays `Group same item and UOM`.
4. Checkbox defaults to checked when `is_lazada_order` is enabled.
5. JavaScript sends selected source names and dialog values to `frappe.model.mapper.map_docs`.
6. Backend maps each source document into the same target Sales Invoice.
7. Backend rebuilds, groups, sorts, and recalculates all item rows.
8. Client receives the final document and refreshes the form.

JavaScript must not calculate quantities, resolve batches, merge rows, or update billing status.

## Dialog argument handling

The Sales Invoice buttons use the same dialog option as Delivery Note mapping:

```javascript
dialog_fields: [{
    fieldname: "group_same_item_uom",
    label: __("Group same item and UOM"),
    fieldtype: "Check",
    default: me.frm.doc.is_lazada_order ? 1 : 0
}]
```

`erpnext.utils.map_current_doc` must copy all dialog values into `opts.args` before calling the backend mapper. Do not pass ordinary dialog values only when `allow_child_item_selection` is enabled.

## Sales Order mapping

For every Sales Order Item:

```text
pending quantity = Sales Order Item.qty - billed quantity
```

`delivered_qty` is intentionally ignored.

Sales Order Item has no `billed_qty` field. Billed quantity is derived as:

```text
billed quantity = billed_amt / rate
```

When `rate` is zero, billed quantity is zero.

### Delivery Note batch resolution

If submitted Delivery Note Items exist for the Sales Order Item:

1. Fetch submitted Delivery Note Items using `so_detail`.
2. Split quantity by Delivery Note Item quantity.
3. Copy Delivery Note Item `batch_no` and UOM.
4. Preserve any remaining quantity as a row with empty `batch_no`.

If no Delivery Note exists, map the Sales Order quantity with empty `batch_no`. Later batch assignment is handled separately.

Rows are grouped by:

```text
item_code + uom + batch_no
```

Different batches remain separate. Empty batch values are grouped only with other empty batch values.

### Multiple Sales Orders

`frappe.model.mapper.map_docs` calls the mapper once per selected Sales Order with the same target document. The mapper must:

1. Preserve rows from previously mapped Sales Orders.
2. Rebuild only rows belonging to the current Sales Order.
3. Append current rows to preserved rows.
4. Group all target rows again.
5. Sort all target rows again.
6. Recalculate totals.

Never clear all `target.items` on every source call. Otherwise, the last selected Sales Order replaces earlier Sales Orders.

## Delivery Note mapping

Delivery Note grouping follows the existing implementation. The grouping key is:

```text
item_code + uom + conversion_factor + rate + batch_no
```

After grouping, recalculate:

- `stock_qty`
- `amount`
- row `idx`
- taxes and totals

## Row ordering

After every mapping and grouping operation:

```python
target.items.sort(key=lambda item: (item.item_code or "", item.uom or "", item.batch_no or ""))
for idx, item in enumerate(target.items, 1):
    item.idx = idx
```

## Reference fields

`Sales Invoice Item` contains read-only Code fields:

- `custom_delivery_note_references`
- `custom_sales_order_references`

These fields are authoritative when a grouped row represents multiple source rows. Standard single-value link fields cannot safely represent multiple sources.

### Delivery Note references

Format:

```text
delivery_note|dn_detail|qty|sales_order|so_detail
```

Example:

```text
DN-001|DN-ITEM-001|2|SO-001|SO-ITEM-001,DN-002|DN-ITEM-009|3|SO-002|SO-ITEM-009
```

### Sales Order references

Without Delivery Note:

```text
sales_order|so_detail|qty
```

With Delivery Note:

```text
sales_order|so_detail|qty|delivery_note|dn_detail
```

Example:

```text
SO-001|SO-ITEM-001|5|DN-001|DN-ITEM-001,SO-002|SO-ITEM-009|3|DN-002|DN-ITEM-009
```

Multiple entries are comma-separated. Each entry represents one source allocation.

## Standard link fields

These fields hold only one value:

- `Sales Invoice.delivery_note`
- `Sales Invoice Item.delivery_note`
- `Sales Invoice Item.dn_detail`
- `Sales Invoice Item.sales_order`
- `Sales Invoice Item.so_detail`

If a grouped row contains more than one reference, clear these fields:

- `sales_order`
- `so_detail`
- `delivery_note`
- `dn_detail`

Do not store comma-separated values in standard link fields. Keep all source data in the custom reference fields.

## Overbilling validation

Validation must support both custom reference fields.

### Delivery Note validation

1. Parse every `custom_delivery_note_references` entry.
2. Validate the five-part format.
3. Aggregate quantity by `dn_detail`.
4. Confirm each `dn_detail` exists.
5. Confirm the reference parent matches the Delivery Note Item parent.
6. Reject quantity greater than the allowed Delivery Note Item quantity.

### Sales Order validation

1. Parse every `custom_sales_order_references` entry.
2. Validate the three-part or five-part format.
3. Aggregate quantity by `so_detail`.
4. Confirm each `so_detail` exists.
5. Reject quantity greater than the Sales Order Item quantity.

A single custom reference must activate custom validation. Detection must not require multiple comma-separated entries.

## Billing status updates

Billing status must be rebuilt from active submitted Sales Invoices, not incremented from previous values.

### Sales Order

For each referenced Sales Order Item:

1. Calculate billed amount from direct `so_detail` rows that have no custom reference.
2. Add proportional amount from `custom_sales_order_references`.
3. Add proportional amount from Delivery Note references containing the same `so_detail`.
4. Store the result in `Sales Order Item.billed_amt`.
5. Recalculate Sales Order `per_billed`.
6. Update `billing_status`.
7. Call `SalesOrder.set_status(update=True)` to synchronize the main Sales Order status.

Proportional amount:

```text
reference billed amount = invoice row amount * reference quantity / invoice row quantity
```

Direct SQL must exclude rows already represented by either custom reference field. Otherwise, amounts are double-counted.

### Delivery Note

For each referenced Delivery Note Item:

1. Calculate billed amount from direct `dn_detail` rows without custom references.
2. Add proportional amount from `custom_delivery_note_references`.
3. Add proportional amount from `custom_sales_order_references` containing the Delivery Note Item reference.
4. Update `Delivery Note Item.billed_amt`.
5. Recalculate Delivery Note billing percentage and status.

## Submit and cancel

On Sales Invoice submit:

- Update Sales Order billing amounts and status.
- Update Delivery Note billing amounts and status.
- Create normal stock ledger and accounting entries.

On Sales Invoice cancel:

- Reverse the Sales Invoice stock ledger entries.
- Rebuild Sales Order billing values from active invoices.
- Rebuild Delivery Note billing values from active invoices.
- Keep Delivery Notes submitted.
- Recalculate main Sales Order status, not only `per_billed`.

A single custom reference must trigger the custom submit/cancel updater. Otherwise cancellation can fall back to the standard updater and leave SO or DN status as `To Bill`.

## Linked-document cancellation

Only Delivery Note is exempt from automatic linked-document cancellation.

`SalesInvoice.before_cancel()` must set:

```python
self.ignore_linked_doctypes = ("Delivery Note",)
```

`hooks.py` must include:

```python
auto_cancel_exempted_doctypes = [
    "Payment Entry",
    "Delivery Note",
]
```

Do not ignore these doctypes:

- `Repost Item Valuation`
- `GL Entry`
- `Stock Ledger Entry`
- `Payment Ledger Entry`

They must retain standard ERPNext behavior.

## Save and batch behavior

Sales Invoice validation can automatically assign and split batches for stock items with empty `batch_no`.

For Sales Order mapped rows containing `custom_sales_order_references`, automatic batch splitting must be skipped. This preserves the intended behavior:

- SO without DN: batch remains empty until later selection.
- SO with DN: batch comes from DN.

Without this guard, an invoice can grow from 18 rows to 33 rows during save because an empty-batch row is split across available batches.

## Stock ledger and cancellation errors

A cancellation can raise `NegativeStockError` when a later transaction would become negative after the invoice reversal. This is a stock-ledger sequence problem, not permission to bypass validation.

Inspect Stock Ledger Entries by:

- item code;
- warehouse;
- batch number;
- posting date and time;
- voucher type and voucher number;
- actual quantity;
- quantity after transaction.

Do not cancel Delivery Notes to bypass a Sales Invoice cancellation. Resolve later stock transactions or repair inconsistent stock history first.

## Troubleshooting

### Only the last Sales Order appears

Cause: mapper clears `target.items` for every selected source.

Fix: preserve rows from earlier source documents and rebuild only current-source rows.

### Checkbox is always ignored

Check that:

1. Sales Invoice JS defines `dialog_fields`.
2. `map_current_doc` copies all dialog values to `opts.args`.
3. Backend mapper accepts `args`.
4. Backend reads `args.get("group_same_item_uom")`.

### Same item, UOM, and batch are not grouped

Check that grouping runs after all selected sources are mapped and uses `batch_no` in the key.

### Row count increases during save

Cause: automatic batch assignment splits empty-batch stock rows.

Check whether the row has `custom_sales_order_references`. Such rows must skip automatic batch splitting.

### SO shows `To Bill` while `per_billed` is 100

Call `SalesOrder.set_status(update=True)` after updating `per_billed` and `billing_status`.

### DN shows `To Bill` after SI cancel

Check that `custom_sales_order_references` entries containing the fifth field (`dn_detail`) are parsed by the Delivery Note status updater.

### Cancel dialog includes Delivery Note

Check both controls:

- `SalesInvoice.before_cancel()` ignores only `Delivery Note`.
- `auto_cancel_exempted_doctypes` includes `Delivery Note`.

## Verification checklist

1. Map one SO without DN and confirm empty batch.
2. Map one SO with DN and confirm DN batch.
3. Map multiple SOs and confirm earlier SO rows remain.
4. Tick Group same item and UOM.
5. Confirm same item/UOM/batch rows merge.
6. Confirm different batches remain separate.
7. Confirm empty batch groups only with empty batch.
8. Save and confirm row count does not unexpectedly increase.
9. Submit and verify SO and DN billing status.
10. Cancel and verify SO and DN statuses reverse.
11. Confirm Delivery Notes remain submitted.
12. Confirm Repost Item Valuation and ledger doctypes keep normal behavior.
13. Inspect stock ledger if cancellation reports negative stock.

## Validation commands

From the ERPNext app directory:

```bash
python -m py_compile erpnext/accounts/doctype/sales_invoice/sales_invoice.py
python -m py_compile erpnext/accounts/doctype/sales_invoice_item/sales_invoice_item.json
python -m py_compile erpnext/selling/doctype/sales_order/sales_order.py
python -m py_compile erpnext/stock/doctype/delivery_note/delivery_note.py
python -m py_compile erpnext/hooks.py
git diff --check
```

`python -m py_compile` is not valid for JSON files; validate JSON separately:

```bash
python -m json.tool erpnext/accounts/doctype/sales_invoice_item/sales_invoice_item.json >/dev/null
```
