import frappe
from frappe.utils import cint

from erpnext.stock.doctype.item.item import sync_material_group_series

COMPANY = "Greenphyto Pte Ltd"
MATERIAL_GROUP = "Labels"
NUMBER_START = 190000
NUMBER_END = 199999
ACCOUNT = "126000 - Stock - R&D Raw Materials - GPL"

# (item_code, product, weight, pack_type, pack_material_1, pack_material_2,
#  carton_packing, carton_box_type, carton_label_type, impex_label)
LABEL_ROWS = [
	('RM-LB-001', 'Kai Lan', '200g', 'Generic', 'Film Pillow Pack Kai Lan SG', '', '12', 'Ctn Box 1', 'Ctn Label Coloured Kai Lan', ''),
	('RM-LB-002', 'Kai Lan', '200g', 'Msia', 'Film Pillow Pack Kai Lan MY', '', '12', 'Ctn Box 1', 'Ctn Label Coloured Kai Lan', 'Ctn IMPEX Label'),
	('RM-LB-003', 'Komatsuna', '200g', 'Generic', 'Film Pillow Koma SG', '', '12', 'Ctn Box 1', 'Ctn Label Coloured Koma', ''),
	('RM-LB-004', 'Komatsuna', '200g', 'Little Farms', 'Film Pillow Blank', 'Label Little Farm Koma', '12', 'Ctn Box 1', 'Ctn Label Coloured Koma', ''),
	('RM-LB-005', 'Komatsuna', '200g', 'Msia', 'Film Pillow Koma MY', '', '12', 'Ctn Box 1', 'Ctn Label Coloured Koma', 'Ctn IMPEX Label'),
	('RM-LB-006', 'Nai Bai', '200g', 'Generic', 'Standing Pouch Nai Bai SG', '', '12', 'Ctn Box 1', 'Ctn Label Coloured Nai Bai', ''),
	('RM-LB-007', 'Nai Bai', '200g', 'Little Farms', 'Standing Pouch Blank', 'Label Little Farm Nai Bai', '12', 'Ctn Box 1', 'Ctn Label Coloured Nai Bai', ''),
	('RM-LB-008', 'Japanese Tang Oh', '150g', 'Generic', 'Standing Pouch JTO SG', '', '12', 'Ctn Box 1', 'Ctn Label Coloured JTO', ''),
	('RM-LB-009', 'Japanese Tang Oh', '150g', 'Little Farms', 'Standing Pouch Blank', 'Label Little Farm JTO', '12', 'Ctn Box 1', 'Ctn Label Coloured JTO', ''),
	('RM-LB-010', 'Japanese Tang Oh', '150g', 'Msia', 'Standing Pouch JTO MY', '', '12', 'Ctn Box 1', 'Ctn Label Coloured JTO', 'Ctn IMPEX Label'),
	('RM-LB-011', 'Red Summer Pak Choy', '170g', 'Msia', 'Film Pillow Pack RSPC MY', '', '12', 'Ctn Box 1', 'Ctn Label Coloured RSPC', 'Ctn IMPEX Label'),
	('RM-LB-012', 'Coco Lettuce', '100g', 'Generic', 'Standing Pouch Coco SG', '', '12', 'Ctn Box 1', 'Ctn Label Coloured Coco', ''),
	('RM-LB-013', 'Coco Lettuce', '100g', 'Little Farms', 'Standing Pouch Blank', 'Label Little Farm Coco', '12', 'Ctn Box 1', 'Ctn Label Coloured Coco', ''),
	('RM-LB-014', 'Mambo Lettuce', '110g', 'Generic', 'Standing Pouch Mambo SG', '', '12', 'Ctn Box 1', 'Ctn Label Coloured Mambo', ''),
	('RM-LB-015', 'Mambo Lettuce', '110g', 'Little Farms', 'Standing Pouch Blank', 'Label Little Farm Mambo', '12', 'Ctn Box 1', 'Ctn Label Coloured Mambo', ''),
	('RM-LB-016', 'Mambo Lettuce', '140g', 'Msia', 'Standing Pouch Mambo MY', '', '12', 'Ctn Box 1', 'Ctn Label Coloured Mambo', 'Ctn IMPEX Label'),
	('RM-LB-017', 'Kiki Crystal Lettuce', '120g', 'Generic', 'Standing Pouch Kiki SG', '', '12', 'Ctn Box 1', 'Ctn Label Coloured Kiki', ''),
	('RM-LB-018', 'Kiki Crystal Lettuce', '120g', 'Little Farms', 'Standing Pouch Blank', 'Label Little Farm Kiki', '12', 'Ctn Box 1', 'Ctn Label Coloured Kiki', ''),
	('RM-LB-019', 'Kiki Crystal Lettuce', '150g', 'Msia', 'Standing Pouch Kiki MY', '', '12', 'Ctn Box 1', 'Ctn Label Coloured Kiki', 'Ctn IMPEX Label'),
	('RM-LB-020', 'Baby Spinach', '100g', 'Generic', 'Clear Box 1', 'Label Baby Spinach SG', '12', 'Ctn Box 1', 'Ctn Label Coloured BS', ''),
	('RM-LB-021', 'Baby Spinach', '100g', 'Little Farms', 'Clear Box 1', 'Label Little Farm Baby Spinach', '12', 'Ctn Box 1', 'Ctn Label Coloured BS', ''),
	('RM-LB-022', 'Baby Spinach', '100g', 'Msia', 'Clear Box 1', 'Label Baby Spinach MY', '12', 'Ctn Box 1', 'Ctn Label Coloured BS', 'Ctn IMPEX Label'),
	('RM-LB-023', 'Baby Spinach', '100g', 'White Label 1', 'Clear Box 1', '', '12', 'Ctn Box 1', 'Ctn Label Coloured BS', ''),
	('RM-LB-024', 'Baby Spinach', '1 kg', 'Bulk', 'PP Bag 1', 'Bulk Pack Label', '12', 'Ctn Box 1', 'Ctn Label Coloured BS', ''),
	('RM-LB-025', 'Rocco Rocket', '50g', 'Generic', 'Clear Box 2', 'Label Rocco Rocket SG', '24', 'Ctn Box 1', 'Ctn Label Coloured RR', ''),
	('RM-LB-026', 'Rocco Rocket', '50g', 'Little Farms', 'Clear Box 2', 'Label Little Farm Rocco Rocket', '24', 'Ctn Box 1', 'Ctn Label Coloured RR', ''),
	('RM-LB-027', 'Rocco Rocket', '50g', 'Msia', 'Clear Box 2', 'Label Rocco Rocket MY', '12', 'Ctn Box 2', 'Ctn Label Coloured RR', 'Ctn IMPEX Label'),
	('RM-LB-028', 'Rocco Rocket', '50g', 'White Label 1', 'Clear Box 2', '', '12', 'Ctn Box 1', 'Ctn Label Coloured RR', ''),
	('RM-LB-029', 'Mama Mesclun', '80g', 'Generic', 'Clear Tray 1', 'Top Seal Film Mama Mesclun SG', '12', 'Ctn Box 1', 'Ctn Label Coloured Mama S', ''),
	('RM-LB-030', 'Mama Mesclun', '70g', 'Msia', 'Clear Tray 1', 'Top Seal Film Mama Mesclun KL', '12', 'Ctn Box 1', 'Ctn Label Coloured Mama S', 'Ctn IMPEX Label'),
	('RM-LB-031', 'Mama Mesclun', '100g', 'White Label 1', 'Standing Pouch Blank', '', '12', 'Ctn Box 1', 'Ctn Label Coloured Mama S', ''),
]


def get_item_name(row):
	return " - ".join([row[8], row[2], row[3]])


def get_description(row, separator="\n"):
	product, weight, pack_type, pm1, pm2, packing, impex = row[1], row[2], row[3], row[4], row[5], row[6], row[9]
	lines = [
		" - ".join([x for x in (product, weight) if x]),
		pack_type,
		" - ".join([x for x in (pm1, pm2) if x]),
		"Carton size: {} PKT".format(packing) if packing else "",
		impex,
	]
	return separator.join([x for x in lines if x])


def ensure_material_group():
	if frappe.db.exists("Material Group", MATERIAL_GROUP):
		return
	frappe.get_doc(
		{
			"doctype": "Material Group",
			"material_group_name": MATERIAL_GROUP,
			"material_type": MATERIAL_GROUP,
			"shortform": "LB",
			"price_control": "MAP",
			"number_start": NUMBER_START,
			"number_end": NUMBER_END,
		}
	).insert(ignore_permissions=True)


def execute():
	ensure_material_group()

	doc = frappe.get_doc("Part Number Settings", COMPANY)
	label_codes = {row[0] for row in LABEL_ROWS}
	existing = {d.code.strip() for d in doc.data_mapping if d.code}
	used_numbers = {cint(d.part_number) for d in doc.data_mapping if d.part_number}
	group_price = frappe.db.get_value("Material Group", MATERIAL_GROUP, "price_control")

	changed = False
	last_number = 0

	for d in doc.data_mapping:
		if d.code and d.code.strip() in label_codes and d.account_code != ACCOUNT:
			d.account_code = ACCOUNT
			changed = True

	for idx, row in enumerate(LABEL_ROWS):
		code = row[0]
		if code in existing:
			continue
		part_number = NUMBER_START + idx
		if part_number in used_numbers:
			frappe.throw("Part number {} already used in Part Number Settings".format(part_number))
		doc.append(
			"data_mapping",
			{
				"material_group": MATERIAL_GROUP,
				"code": code,
				"title": get_item_name(row),
				"description": get_description(row),
				"part_number": part_number,
				"price": group_price or "MAP",
				"account_code": ACCOUNT,
				"company": COMPANY,
			},
		)
		last_number = max(last_number, part_number)
		changed = True

	if changed:
		doc.save(ignore_permissions=True)
		if last_number:
			sync_material_group_series(MATERIAL_GROUP, last_number)

	reorder_by_part_number()


def reorder_by_part_number():
	rows = frappe.db.get_all(
		"Part Number Details",
		filters={"parent": COMPANY, "parenttype": "Part Number Settings", "parentfield": "data_mapping"},
		fields=["name", "idx", "part_number"],
		order_by="part_number asc, name asc",
	)
	for idx, row in enumerate(rows, start=1):
		if row.idx != idx:
			frappe.db.set_value("Part Number Details", row.name, "idx", idx, update_modified=False)
