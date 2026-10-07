import frappe

# item_code disesuaikan dengan item Products yang sesuai
DATA = {
	"PR-LV-MSH": {"electricity": 1.6077, "manpower": 2.27},  # Oak (Shepard) ?
	"PR-LV-MNA": {"electricity": 1.8073, "manpower": 2.27},  # Romaine (Napa) ?
	"PR-LV-MEX": {"electricity": 2.1702, "manpower": 2.27},  # Incised (Exmond) 
	"PR-LV-MBE": {"electricity": 1.9546, "manpower": 2.27},  # Butterhead (Bernoulli)
	"PR-LV-TCC": {"electricity": 1.8811, "manpower": 3.41},  # Teen Red Coco
	"PR-AV-SP": {"electricity": 3.4256, "manpower": 4.55},  # Baby Pak Choy
	"PR-LV-BAN": {"electricity": 5.8304, "manpower": 4.55},  # Spinach
	"PR-LV-BAR": {"electricity": 5.2595, "manpower": 4.55},  # Arugula
	"PR-LV-LI": {"electricity": 1.6806, "manpower": 2.27},  # Mambo
	"PR-LV-CO": {"electricity": 1.7522, "manpower": 2.27},  # Coco
	"PR-LV-CR": {"electricity": 1.6211, "manpower": 2.27},  # Crystal
	"PR-AV-KL": {"electricity": 2.2573, "manpower": 2.27},  # Kailan
	"PR-AV-KOM": {"electricity": 1.6716, "manpower": 2.27},  # Koma
	"JTO": {"electricity": 3.7474, "manpower": 3.41},  # JTO (item_code belum ada)
	"PR-AV-NB": {"electricity": 2.0311, "manpower": 2.27},  # Nai Bai
	"PR-AV-PC": {"electricity": 2.2841, "manpower": 2.27},  # Red Summer Pak Choy
}

"""
bench --site test6 execute erpnext.patches.gp.create_rate_card_for_cogs.execute
"""
def execute():
	company = frappe.defaults.get_global_default("company")

	for item_code, rates in DATA.items():
		if not frappe.db.exists("Item", item_code):
			frappe.logger(__name__).warning(
				"Rate Card patch: item not found {0}".format(item_code)
			)
			continue

		if frappe.db.get_value("Item", item_code, "rate_card"):
			continue

		doc = frappe.get_doc(
			{
				"doctype": "Rate Card",
				"company": company,
				"title": "Rate Card - {0}".format(item_code),
				"rates": [
					{
						"operation": "Harvesting",
						"electricity": rates["electricity"],
						"manpower": rates["manpower"],
						"machinery": 0,
						"consumable": 0,
					}
				],
			}
		).insert(ignore_permissions=True)

		frappe.db.set_value("Item", item_code, "rate_card", doc.name, update_modified=False)

	frappe.db.commit()
