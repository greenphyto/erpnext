# Automatic 1:1 Repack After Manufacturing

## Objective

Automatically create and submit a 1:1 Repack Stock Entry when a Manufacture Stock Entry is submitted and its finished item matches an Item Change mapping.

The feature changes the item code from `from_item` to `to_item`. Quantity, UOM, and conversion factor remain unchanged. Batch handling for the target item remains under the standard ERPNext auto-batch process.

## Configuration

Configure mappings in:

`Manufacturing Settings > Item Change`

Each row contains:

- `from_item`: Item produced by the Manufacture Stock Entry.
- `to_item`: Replacement item to produce through Repack.
- `warehouse`: Target warehouse on the Manufacture Stock Entry.

A mapping is used only when both conditions match:

```text
Manufacture item_code == from_item
Manufacture t_warehouse == mapping warehouse
```

Item-only matches are not sufficient.

## Submit flow

1. User submits a Manufacture Stock Entry.
2. The system searches `Manufacturing Settings.item_change`.
3. Matching finished-item rows are selected by item and target warehouse.
4. If a production Delivery Note exists for the Work Order, its sample quantity is deducted.
5. Repack quantity is calculated as:

```text
Repack quantity = Manufacture finished quantity - production sample quantity
```

6. If the resulting quantity is greater than zero, the system creates a Repack Stock Entry.
7. The Repack consumes `from_item` from the configured warehouse.
8. The Repack produces `to_item` in the configured warehouse.
9. Quantity, UOM, and conversion factor are copied 1:1.
10. The Repack is submitted automatically.

The Repack remark uses this format:

```text
Auto Repack: Manufacture {manufacture_stock_entry_name}
```

## Link behavior

The relationship is stored in one direction only:

```text
Manufacture.auto_repack = Repack.name
```

The Repack does not store a link back to the Manufacture Stock Entry. This avoids creating a reverse Stock Entry dependency that can block cancellation.

`auto_repack` and `auto_repack_source` remain available as Stock Entry fields, but automatic creation populates only `auto_repack` on the Manufacture entry.

## Cancellation flow

When a Manufacture Stock Entry with `auto_repack` is cancelled:

1. The linked Repack is located.
2. The Repack is cancelled automatically if it is submitted.
3. Standard Stock Entry cancellation reverses the Repack Stock Ledger Entry and GL Entry.
4. The Manufacture Stock Entry cancellation continues normally.

The cancellation uses Stock Entry link bypass settings for this controlled automatic relationship. This bypass affects link validation only; it does not skip stock ledger, GL, valuation, batch, or serial cancellation logic.

## Idempotency and safeguards

- A Manufacture entry with an existing `auto_repack` is not processed again.
- Existing non-cancelled Repack entries with the same source are not duplicated.
- Repack cancellation runs only for Manufacture entries with an `auto_repack` value.
- Repack creation is skipped when the quantity after sample deduction is zero or negative.

## Source code

Main implementation files:

- `erpnext/controllers/foms.py`
  - `create_item_change_repack`
  - `cancel_item_change_repack`
- `erpnext/hooks.py`
  - Stock Entry submit and before-cancel hooks
- `erpnext/stock/doctype/stock_entry/stock_entry.py`
  - Stock Entry cancellation link handling
- `erpnext/stock/doctype/stock_entry/stock_entry.json`
  - Automatic Repack link fields
- `erpnext/manufacturing/doctype/manufacturing_settings/manufacturing_settings.json`
  - `item_change` table configuration
- `erpnext/gp_erp/doctype/item_finish_goods_change/item_finish_goods_change.json`
  - Item Change child table fields

## Troubleshooting

### Negative stock during Repack

Check:

- `from_item` is the item available in the configured warehouse.
- `warehouse` matches the Manufacture finished row `t_warehouse`.
- A production sample Delivery Note has reduced the available quantity.
- Repack quantity equals Manufacture finished quantity minus sample quantity.

### Repack was not created

Check:

- Manufacture purpose is `Manufacture`.
- Finished item matches `from_item`.
- Finished row `t_warehouse` matches mapping `warehouse`.
- Resulting quantity after sample deduction is greater than zero.
- `auto_repack` is not already populated.

### Manufacture cancellation is blocked

Ensure the latest code is loaded and Stock Entry metadata is migrated. The automatic link must exist only on the Manufacture Stock Entry; the Repack must not contain a reverse `auto_repack_source` value.
