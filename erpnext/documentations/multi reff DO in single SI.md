# Multi-reference DO in single SI

## Objective

Support one Sales Invoice (SI) containing combined items from multiple Delivery Notes (DO), with these conditions:

- One DO may be billed to only one SI.
- One SI may contain multiple DOs.
- SI rows may be combined by `item_code` and `uom`.
- Batch is ignored for grouping according to business requirements.
- DO references are stored as comma-separated values in a custom field according to integration requirements.
- Standard fields remain populated when they have only one valid value.

## Important limitations

The following standard fields are single-value fields and must not contain comma-separated lists:

- `Sales Invoice.delivery_note`
- `Sales Invoice Item.delivery_note`
- `Sales Invoice Item.dn_detail`
- `Sales Invoice Item.sales_order`
- `Sales Invoice Item.so_detail`

ERPNext uses these fields for queries, dashboards, per-billed, billed quantity, returns, cancellation, and links between documents. Comma-separated values are the custom data source; standard fields are only a cache or primary reference when the value is singular.

## Data model

Add a Long Text custom field to `Sales Invoice Item`, for example `custom_delivery_note_references`.

Minimum comma-separated format:

```text
DN-001|DN-ITEM-001|2|SO-001|SO-ITEM-001,DN-002|DN-ITEM-009|3|SO-002|SO-ITEM-009
```

Order of each entry: `delivery_note|dn_detail|qty|sales_order|so_detail`. Use a delimiter that cannot appear in IDs, escape values if the delimiter may appear, and document one parser for the entire process.

Data rules:

- One entry represents one `Delivery Note Item`.
- `dn_detail` must be unique within one SI.
- `delivery_note` must match the parent of `dn_detail`.
- `qty` must be positive for a normal invoice and follow return rules for a credit note.
- References must store `sales_invoice_item` after the SI row is created if reverse updates require it.
- Add a checksum or version if needed to detect payload changes.

If metadata must be updated without touching item rows, add a Long Text custom field to the SI parent, for example `custom_delivery_note_references`, using the same format. Avoid duplicating the data source; use the child row as the primary source when both levels are required.

## SI creation flow

1. Fetch the submitted DOs selected by the user.
2. Validate that each DO has no active SI.
3. Fetch DO Items with pending quantity.
4. Group rows by `item_code` and `uom`.
5. Sum quantity per group.
6. Ignore batches only during grouping; do not alter the stock ledger or batch transactions.
7. Create one `Sales Invoice Item` row per group.
8. Store all source DO Items as comma-separated values in that row's custom field.
9. Store `sales_invoice_item` in each reference if reverse lookup requires it.
10. Run standard price, account, tax, payment term, and total calculations.

## Validation before submit

Custom validation is required:

- The comma-separated value is valid and each entry has the expected number of fields according to the schema.
- All linked DOs have submitted status.
- All `dn_detail` values exist and have the correct parent.
- No duplicate `dn_detail` exists across active SIs.
- The total reference quantity does not exceed the DO quantity that has not been billed or returned.
- A DO is not linked to another SI.
- Reference `item_code` and `uom` match the grouped SI row.
- Company, customer, currency, warehouse, and return status are consistent.
- References cannot change after submit without an amend process.
- Use a database transaction and locks during validation and updates to prevent double billing.

## Updating related documents

When the SI is submitted:

- Update the custom billed state and billed quantity on each DO Item.
- Populate `Delivery Note Item.si_detail` only when the standard relationship can still represent one SI Item; do not write JSON to this field.
- Populate `Delivery Note Item.against_sales_invoice` with the target SI.
- Set `Delivery Note.per_billed` and billed status through custom aggregation.
- Update standard SI fields only as a cache when their values are unambiguous.

When the SI is cancelled:

- Reverse all updates based on the JSON snapshot.
- Reduce the billed quantity of each DO Item.
- Remove or cancel the SI relationship on DO Items.
- Rebuild `per_billed` and the DO status from all active SIs, not from previous values.

When the SI is amended or returned:

- Treat it as a new operation after the original document is cancelled according to ERPNext rules.
- Revalidate quantity and duplicate references.
- A return must not reduce DO quantity below the quantity previously billed.

## Dashboard and links

Standard dashboards that read `delivery_note` or `dn_detail` will not find all DOs. Add:

- A custom dashboard link/query from SI to all DOs from JSON.
- A custom query report from DO to SI.
- A link formatter or server method that parses the JSON and fetches the related documents.
- A billed-status indicator based on custom aggregation.

Do not rely on comma-separated fields for filtering, joins, or referential integrity.

## Planned code changes

1. Add a comma-separated custom field to SI Item through a fixture/customization.
2. Add a custom multi-DO mapper, separate from the standard `make_sales_invoice()`.
3. Add a centralized parser and schema validator.
4. Add `before_submit` and `before_cancel` validation.
5. Add a service to update/rebuild the DO billed state.
6. Add locking and transaction boundaries.
7. Add a custom dashboard/query.
8. Add permission validation for all referenced DOs.

## Minimum tests

- Two DOs with the same item and UOM become one SI Item.
- The same item with different UOMs remains in separate rows.
- A comma-separated reference containing 100 items is valid.
- Duplicate `dn_detail` is rejected.
- A DO that has already been billed is rejected.
- Partial quantity is calculated correctly.
- Submit updates billed quantity and `per_billed`.
- Cancel restores billed quantity and status.
- Amend and return do not cause double billing.
- Concurrent submit cannot use the same DO Item.
- The custom dashboard displays all DOs.
- Invalid comma-separated value, missing DN, mismatched parent, company, customer, or UOM is rejected.

## Decisions requiring confirmation

- Custom field name and whether the payload belongs in SI Item, the SI parent, or both.
- Whether batches may truly be ignored for stock items.
- Whether one DO may be distributed across multiple SI Items due to grouping.
- Whether the standard SI `delivery_note` field is used as a cache or cleared for multi-DO.
- Official definition of billed quantity and `per_billed` after grouping.
- Return format and quantity allocation among references.
