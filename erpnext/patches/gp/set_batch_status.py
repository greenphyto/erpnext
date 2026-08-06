import frappe


def execute():
	frappe.reload_doc("stock", "doctype", "batch")
	batches = frappe.get_all("Batch", filters={"status": ["in", ["", None]]}, pluck="name")
	for batch in batches:
		frappe.db.set_value("Batch", batch, "status", "Active", update_modified=False)
