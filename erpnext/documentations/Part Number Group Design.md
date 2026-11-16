# Part Number Group Packaging Breakdown

## Objective

Credit multiple packaging items into a Work Order's required items from a single configured group, instead of a single packaging item.

When a Work Order resolves its packaging quantity (the pack qty, for example 24), each item in the Part Number Group is credited separately using its own `credit_factor`. Pack qty is divided by `credit_factor` to get the required quantity per packaging item.

## Terminology

- **Pack qty**: total number of packs resolved for the production item, calculated as `self.qty / conversion_factor`. In the Request flow this is `ceil(self.qty * quantity / stock_qty / conversion_factor)`.
- **Credit factor**: how many packs equal one unit of a packaging item. Minimum is 1.
- **Credited quantity**: `ceil(pack_qty / credit_factor)`.

Example: pack qty = 24.

- Item A `credit_factor = 12` -> credited qty = 2.
- Item B `credit_factor = 1` -> credited qty = 24.

## Data model

### Part Number Group (`gp_erp/doctype/part_number_group`)

Naming: `RM-PNG-.###`

- `disabled` (Check)
- `group_list` (Table, child `Part Number Table List`, required)

### Part Number Table List (`gp_erp/doctype/part_number_table_list`)

Child table, one row per packaging item in the group.

- `item_code` (Link Item, required)
- `part_number` (fetch from `item_code.material_number`, read only)
- `item_name` (fetch from `item_code.item_name`, read only)
- `credit_factor` (Int, default 1): how much qty needed to credit this item out, minimum 1.

### Links to Part Number Group

- `Request Items.part_number_group` (Link): group chosen per request line.
- `Packaging List Available.part_number_group` (Link): group configured on the Item master packaging list, used as fallback.

## Resolution

For each Request line of the production item:

1. If `Request Items.part_number_group` is set, use it.
2. Otherwise fall back to the matched `Packaging List Available` row's `part_number_group` for the production item.

If a Part Number Group resolves, it **overrides** the single `packaging_item` logic. The group is broken down into one required item per `group_list` row. If no group resolves, the existing single packaging item flow runs unchanged.

## Credit flow

In `get_packaging_from_order()` (`manufacturing/doctype/work_order/work_order.py`):

1. Existing packaging rows are removed (`is_packaging` filter).
2. Pack qty is resolved as before.
3. If a Part Number Group is resolved for the line:
   - For each row in `group_list`:
     - `required_qty = ceil(pack_qty / credit_factor)`
     - `rate = get_valuation_rate(item_code, source_warehouse, "", "")`
     - Append to `required_items` with `is_packaging = 1`, operation `Harvesting`.
4. If no group, append the single resolved `packaging_item` (unchanged behavior).

## Source code

- `erpnext/manufacturing/doctype/work_order/work_order.py`
  - `get_packaging_from_order`
- `erpnext/gp_erp/doctype/part_number_group/part_number_group.json`
- `erpnext/gp_erp/doctype/part_number_table_list/part_number_table_list.json`
- `erpnext/buying/doctype/request_items/request_items.json`
  - `part_number_group` field
- `erpnext/selling/doctype/packaging_list_available/packaging_list_available.json`
  - `part_number_group` field
