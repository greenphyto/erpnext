import frappe
import csv 
from pathlib import Path
from frappe.utils import cint, cstr
"""
bench --site test2 execute erpnext.patches.v14_0.fix_asset.run_update_asset_name
"""

def execute():
	pass

def run_update_asset_name():
	file = Path(__file__).parent / "asset_name.csv"
	print("Path", file)
	with file.open("r", encoding="utf-8") as data_file:
		csv_data = csv.reader(data_file)
		# print("Get data length:", len(list(csv_data)))
	
		id_col = 0
		item_name_col = 1
		asset_name_col = 2
		csv_data = csv.reader(data_file)
		for d in list(csv_data):
			# add item code if missing
			# add new asset
			# generate qr

			item = ' '.join(d[id_col].splitlines())
			# print(asset)
			asset_id = frappe.get_value("Asset",{"item_code":item})

			if not asset_id:
				print("Skip for this asset:", item)
				continue
			
			print("Renaming", item)
			if d[item_name_col]:
				new_item_name = d[item_name_col].strip()
				brand = get_brand(new_item_name)
				frappe.db.set_value("Asset", asset_id, "brand", brand)
				frappe.db.set_value("Item", item, "brand", brand)

			if d[asset_name_col]:
				new_asset_name = d[asset_name_col].strip()
				frappe.db.set_value("Asset", asset_id, "asset_name", new_asset_name)

def get_brand(brand):
	exist = frappe.get_value("Brand", brand)
	if not exist:
		doc = frappe.new_doc("Brand")
		doc.brand = brand
		doc.insert()
		return doc.name
	return exist

"""
bench --site test3 execute erpnext.patches.v14_0.fix_asset.insert_new_asset
"""
def insert_new_asset():
	file = Path(__file__).parent / "new_asset2.csv"
	print("Path", file)
	global COL_IDX
	COL_IDX = 0
	def get_col_index():
		global COL_IDX
		COL_IDX += 1
		return COL_IDX
	
	with file.open("r", encoding="utf-8") as data_file:
		csv_data = csv.reader(data_file)
		# print("Get data length:", len(list(csv_data)))

		# re-arrange col idx here
		ITEM_CODE = get_col_index()
		BRAND = get_col_index()
		ASSET_NAME = get_col_index()
		ASSET_CATEGORY = get_col_index()
		EQUIPMENT_CODE = get_col_index()
		EQUIPMENT_TYPE = get_col_index()
		ASSET_TAG_ID = get_col_index()
		ASSET_NUMBER = get_col_index()
		LOCATION = get_col_index()
		LOCATION_CODE = get_col_index()
		SERIAL_NUMBER = get_col_index()
		PRODUCT_WARRANTY = get_col_index()
		START_DATE = get_col_index()
		PRODUCT_WARRANTY = get_col_index()
		END_DAY = get_col_index()

		csv_data = csv.reader(data_file, delimiter=";")
		for d in list(csv_data):
			if d[ITEM_CODE] == "ITEM CODE":
				continue

			# print(d)
			item_code = d[ASSET_NAME].replace('\n', ' ').replace('\r', '')
			item_name = d[ASSET_NAME].replace('\n', ' ').replace('\r', '')
			location = d[LOCATION]
			location_code = d[LOCATION_CODE]
			
			# create item 
			brand = get_brand(d[BRAND])
			it_exist = create_item(frappe._dict({
				"item_code":item_code,
				"item_name":item_name,
				"brand": brand
			}))

			location = create_asset_location(location, location_code)

			# create asset
			res = create_asset(frappe._dict({
				"item_code":item_code,
				"asset_name": item_name,
				"equipment_type": d[EQUIPMENT_TYPE],
				"equipment_code": d[EQUIPMENT_CODE],
				"location_code": location_code,
				"location": location,
				"serial_number": d[SERIAL_NUMBER],
				"asset_number":d[ASSET_NUMBER]
			}))

			# if res:
			# 	break

def create_item(data):
	exists = frappe.get_value("Item", {"item_code":data.item_code})
	if exists:
		return exists
	
	doc = frappe.new_doc("Item")
	doc.item_code = data.item_code
	doc.item_name = data.item_name
	doc.asset_category = "Navix"
	doc.is_fixed_asset = 1
	doc.stock_uom = "Unit"
	doc.item_group = "Navix"
	doc.is_stock_item = 0
	doc.brand = data.brand
	doc.insert(ignore_permissions=1)

	return doc.name

def create_asset(data):
	exists = frappe.get_value("Asset", {"item_code":data.item_code, "docstatus":1})
	if exists:
		print("Skip Asset", exists)
		return 

	doc = frappe.new_doc("Asset")
	if data.asset_number:
		an = cint(data.asset_number)
		asset_number = cstr( an + 1000)[1:]
		series = f"GPYTO-SG2Ka1-1-{data.equipment_code}-{data.location_code}-"
		doc.__newname = series + asset_number
		update_series(series, an)
	else:
		doc.naming_series = "GPYTO-SG2Ka1-1-.{equipment_code}.-.{location_code}.-.###"
	doc.item_code = data.item_code
	doc.asset_name = data.asset_name
	doc.is_existing_asset = 1
	doc.asset_category = "Navix"
	doc.equipment_type = data.equipment_type
	doc.equipment_code = data.equipment_code
	doc.location_code = data.location_code
	doc.location = data.location
	doc.serial_number = data.serial_number
	doc.maintenance_required = 1
	doc.insert(ignore_permissions=1)
	doc.submit()

	return doc.name

def create_asset_location(location, location_code):
	exists = frappe.db.exists("Location", location)

	if not exists:
		doc = frappe.get_doc({
			"doctype": "Location", 
			"location_name": location,
			"location_code": location_code,
		}).insert()
		return doc.name
	else:
		return exists

def update_series(series, number):
	temp = frappe.db.sql("select current, name from `tabSeries` where name like %s", ("%%"+series+"%%"), as_dict=1)
	cur_value = 0
	if temp:
		temp = temp[0]
		cur_value = temp.get("current")
	if not temp:
		Series = frappe.qb.DocType("Series")
		frappe.qb.into(Series).insert(series, number).columns("name", "current").run(debug=1)
	elif cint(number) > cint(cur_value):
		frappe.db.sql('update `tabSeries` set current = %s where name = %s', (number, temp.get("name")), debug=1)
	
