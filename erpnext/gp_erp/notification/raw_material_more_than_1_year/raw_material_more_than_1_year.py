import frappe
from frappe.utils import add_days, today


def get_context(context):
	pass


def notify_raw_material_more_than_1_year():
	one_year_ago = add_days(today(), -365)

	batches = frappe.get_all(
		"Batch",
		filters={
			"item_group": "Raw Material",
			"batch_qty": [">", 0],
			"manufacturing_date": ["<=", one_year_ago],
			"disabled": 0,
		},
		fields=["name", "item", "item_name", "item_group", "manufacturing_date", "batch_qty", "stock_uom"],
		order_by="manufacturing_date asc",
	)

	if not batches:
		return

	doc_notif = frappe.get_doc("Notification", "Raw Material more than 1 year")
	doc = frappe._dict({
		"doc_list": batches
	})
	doc_notif.send(doc)
