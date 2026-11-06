import frappe

from erpnext.patches.gp.setup_label_part_number_settings import (
	LABEL_ROWS,
	MATERIAL_GROUP,
	get_description,
	get_item_name,
)

ITEM_GROUP = "Raw Material"
STOCK_UOM = "Nos"
SHELF_LIFE_DAYS = 365
VALUATION_METHOD = "FIFO"
VALUATION_RATE = 1


def get_batch_fields(code):
	return {
		"has_batch_no": 1,
		"create_new_batch": 1,
		"batch_number_series": "{}-BN.#####".format(code),
		"has_expiry_date": 1,
		"shelf_life_in_days": SHELF_LIFE_DAYS,
		"valuation_method": VALUATION_METHOD,
		"is_sales_item": 0,
		"valuation_rate": VALUATION_RATE,
	}


def execute():
	for row in LABEL_ROWS:
		code = row[0]
		fields = get_batch_fields(code)
		fields["description"] = get_description(row, "<br>")

		if frappe.db.exists("Item", code):
			current = frappe.db.get_value("Item", code, list(fields), as_dict=True)
			diff = {k: v for k, v in fields.items() if current.get(k) != v}
			if diff:
				frappe.db.set_value("Item", code, diff)
			continue

		item = frappe.new_doc("Item")
		item.item_code = code
		item.item_name = get_item_name(row)
		item.item_group = ITEM_GROUP
		item.stock_uom = STOCK_UOM
		item.is_stock_item = 1
		item.material_group = MATERIAL_GROUP
		item.update(fields)
		item.insert(ignore_permissions=True)
