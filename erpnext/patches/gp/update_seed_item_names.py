import frappe

ITEM_NAMES = {
	"RM-SD-KOM": "F1 Komatsuna Seeds",
	"RM-SD-SPC": "Small Size Pak Choy Seeds",
	"RM-SD-SUN": "Red Crystal Lettuce (Sungari RZ) Seeds",
	"RM-SD-SCA": "Red Crystal Lettuce (Scamander RZ) Seeds",
	"RM-SD-SAT": "Red Leaf Lettuce (Satine RZ) Seeds",
	"RM-SD-GAL": "Multi-leaf Lettuce (Galley RZ) Seeds",
	"RM-SD-LIZ": "Spinach (Lizard RZ F1) Seeds",
}


def execute():
	for item_code, item_name in ITEM_NAMES.items():
		if frappe.db.exists("Item", item_code):
			frappe.db.set_value("Item", item_code, "item_name", item_name, update_modified=1)
