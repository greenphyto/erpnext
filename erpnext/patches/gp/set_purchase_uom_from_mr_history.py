import frappe

# bench --site erp-prod execute erpnext.patches.gp.set_purchase_uom_from_mr_history.execute
def execute():
	item_purchase_uom = {
		"RM-ZOT-32": "1500 m",
		"RM-ZOT-24": "1500 m",
		"RM-ZOT-26": "1500 m",
		"RM-ZOT-25": "1500 m",
		"RM-ZOT-27": "1500 m",
		"RM-ZOT-13": "Carton",
		"RM-ZOT-16": "Carton",
		"RM-ZOT-09": "1500 m",
		"RM-ZOT-08": "1500 m",
		"RM-ZOT-10": "1500 m",
		"RM-ZOT-04": "1500 m",
	}

	for item_code, uom in item_purchase_uom.items():
		if not frappe.db.exists("Item", item_code):
			continue

		if not frappe.db.exists(
			"UOM Conversion Detail", {"parent": item_code, "uom": uom}
		):
			continue

		frappe.db.set_value("Item", item_code, "purchase_uom", uom)
