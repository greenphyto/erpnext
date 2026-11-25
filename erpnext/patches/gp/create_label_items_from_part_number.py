import frappe
from frappe.utils import cstr

from erpnext.stock.doctype.item.item import sync_material_group_series

ITEMS = [
	('Labels', 'RM-LB-033', 'Label Little Farm Koma', '', 190032),
	('Labels', 'RM-LB-034', 'Label Little Farm Nai Bai', '', 190033),
	('Labels', 'RM-LB-035', 'Label Little Farm JTO', '', 190034),
	('Labels', 'RM-LB-036', 'Label Little Farm Coco', '', 190035),
	('Labels', 'RM-LB-037', 'Label Little Farm Mambo', '', 190036),
	('Labels', 'RM-LB-038', 'Label Little Farm Kiki', '', 190037),
	('Labels', 'RM-LB-039', 'Label Baby Spinach SG', '', 190038),
	('Labels', 'RM-LB-040', 'Label Little Farm Baby Spinach', '', 190039),
	('Labels', 'RM-LB-041', 'Label Baby Spinach MY', '', 190040),
	('Labels', 'RM-LB-042', 'Bulk Pack Label', '', 190041),
	('Labels', 'RM-LB-043', 'Label Rocco Rocket SG', '', 190042),
	('Labels', 'RM-LB-044', 'Label Little Farm Rocco Rocket', '', 190043),
	('Labels', 'RM-LB-045', 'Label Rocco Rocket MY', '', 190044),
	('Labels', 'RM-LB-046', 'Top Seal Film Mama Mesclun SG', '', 190045),
	('Labels', 'RM-LB-047', 'Top Seal Film Mama Mesclun KL', '', 190046),
]

"""
bench --site erp-prod execute erpnext.patches.gp.create_label_items_from_part_number.execute
"""


def execute():
	print(f"Total items: {len(ITEMS)}")

	created = 0
	skipped = 0
	for material_group, code, title, description, part_number in ITEMS:
		if create_item(material_group, code, title, description, part_number):
			created += 1
		else:
			skipped += 1

	print(f"Done. Created: {created}, Skipped: {skipped}")


def create_item(material_group, code, title, description, part_number):
	if frappe.db.exists("Item", code):
		print(f"SKIP   {code}: item already exists")
		return False

	part_number = cstr(part_number)

	item = frappe.new_doc("Item")
	item.item_code = code
	item.item_name = title
	item.description = description or title
	item.item_group = "Raw Material"
	item.stock_uom = "Nos"
	item.is_stock_item = 1
	item.has_batch_no = 1
	item.material_group = material_group
	item.material_number = part_number
	item.insert(ignore_permissions=True)

	sync_material_group_series(material_group, part_number)
	print(f"CREATE {code}: {title} ({material_group} / {part_number})")
	return True
