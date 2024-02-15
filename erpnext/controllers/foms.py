import frappe
from erpnext.foms.doctype.foms_integration_settings.foms_integration_settings import FomsAPI,is_enable_integration, get_farm_id
from frappe.core.doctype.sync_log.sync_log import get_pending_log
from frappe.utils import cint
from erpnext.accounts.party import get_party_details
from erpnext.foms.doctype.foms_data_mapping.foms_data_mapping import create_foms_data

"""
Make Supplier from ERP to FOMS
can update or delete
supplierID = foms_id
"""

# VARIABLE
# mapping uom FOMS to ERP
UOM_MAPPING = {
	"g":"gram",
	"L":"Litre",
	"ml":"Millilitre",
}

OPERATION_MAP = {
	"Nursery":1,
	"Transfer + Growth":2,
	"Harvesting":3,
}

OPERATION_MAP_NAME = {
	1:"Seeding",
	2:"Transplanting",
	3:"Harvesting"
}

# SUPPLIER (POST)
def update_foms_supplier():
	if not is_enable_integration():
		return 
	
	logs = get_pending_log({"doctype":"Supplier"})
	api = FomsAPI()
	for log in logs:
		# create new supplier if not have
		if log.update_type == "Update":
			_update_foms_supplier(api, log) 

# CUSTOMER (POST)
def update_foms_customer():
	if not is_enable_integration():
		return 
	
	logs = get_pending_log({"doctype":"Customer"})
	api = FomsAPI()
	for log in logs:
		if log.update_type == "Update":
			_update_foms_customer(api, log) 

class GetData():
	def __init__(self, data_type, get_data, get_key_name, post_process, doc_type="Item", show_progress=False):
		self.data_type = data_type
		self.show_progress = show_progress
		self.get_data = get_data
		self.get_key_name = get_key_name
		self.post_process = post_process
		self.doc_type = doc_type
	
	def setup(self):
		self.api = FomsAPI()
		self.farm_id = get_farm_id()

	def run(self):
		self.setup()
		title = f"Get FOMS {self.data_type}..."
		def show_progress_bar(percent):
			if self.show_progress:
				frappe.publish_realtime("progress_foms_download", {
					"percent":percent,
					"title":title
				})

		data = self.get_data(self)

		
		total_count = len(data)
		for i in range(total_count):
			d = data[i]

			# pull to foms data mapping
			key_name = self.get_key_name(d)
			map_doc = create_foms_data(self.data_type, key_name, d)
			result = self.post_process(self, d)
			map_doc.doc_type = self.doc_type
			map_doc.doc_name = result
			map_doc.save()

			percent = (i+1)/total_count*100
			if i % 10 == 0:
				show_progress_bar(percent)


# RAW MATERIAL (GET)
def get_raw_material(show_progress=False):
	def get_data(gd):
		raw = gd.api.get_raw_material(gd.farm_id)
		data = raw.get("items")
		return data

	def post_process(gd, log):
		return create_raw_material(log) 

	def get_key_name(log):
		return log.get("rawMaterialRefNo")
	
	GetData(
		data_type = "Raw Material",
		get_data=get_data,
		get_key_name = get_key_name,
		post_process=post_process,
		show_progress=show_progress
	).run()


# PRODUCTS (GET)
def get_products(show_progress=False):
	def get_data(gd):
		raw = gd.api.get_products(gd.farm_id)
		data = raw.get("items")
		return data

	def post_process(gd, log):
		return create_products(log) 

	def get_key_name(log):
		return log.get("productID")
	
	GetData(
		data_type = "Product",
		get_data=get_data,
		get_key_name = get_key_name,
		post_process=post_process,
		show_progress=show_progress
	).run()


# EQUIPTMENT (GET)
# Pending

# RECIPE (GET)
def get_recipe(show_progress=False):
	def get_data(gd):
		data = gd.api.get_product_list_for_recipe(gd.farm_id)
		return data

	def post_process(gd, log):
		product_id =  log.get("id")
		raw = gd.api.get_product_process(gd.farm_id, product_id)
		return create_bom_products(raw, product_id)

	def get_key_name(log):
		return log.get("productId")
	
	GetData(
		data_type = "Recipe",
		doc_type="BOM",
		get_data=get_data,
		get_key_name = get_key_name,
		post_process=post_process,
		show_progress=show_progress
	).run()
	
# WORK ORDER
# FINISH PRODUCTS
		

def _update_foms_supplier(api, log):
	supplier = frappe.get_doc("Supplier", log.name)
	details = get_party_details(supplier.name, party_type="Supplier")
	farm_id = get_farm_id()
	data = {
		"farmId": farm_id,
		"supplierID": supplier.foms_id,
		"supplierRefNo": supplier.name,
		"supplierName": supplier.supplier_name,
		"address": details.address_display or details.company_address_display or "",
		"contact": supplier.mobile_no or  details.contact_mobile or "",
		"email": supplier.email_id or details.contact_email or "user@example.com",
		"creditLimit": 0,
		"creditTermID": 0,
		"contactPerson": details.contact_person,
		"countryCode": frappe.db.get_single_value('FOMS Integration Settings', "country_id"),
		"rmDeviceIds": "",
		"rmDeviceId":  [],
	}
	res = api.create_or_update_supplier(data)
	if 'supplierID' in res:
		supplier.db_set("foms_id", res['supplierID'])

def _update_foms_customer(api, log):
	customer = frappe.get_doc("Customer", log.name)
	details = get_party_details(customer.name, party_type="Customer")
	# print(details)
	farm_id = get_farm_id()
	address = details.address_display or details.company_address_display
	shipping_address = details.get("shipping_address") or address

	data = {
		"farmId": farm_id,
		"customerRefNo": customer.name,
		"customerName": customer.customer_name,
		"address": address,
		"contact": customer.mobile_no or  details.contact_mobile or "" ,
		"email": customer.email_id or details.contact_email or "user@example.com",
		"creditLimit": 0,
		"creditTermID": 0,
		"contactPerson": details.contact_person or "",
		"countryCode": frappe.db.get_single_value('FOMS Integration Settings', "country_id"),
		"deliveryAddress": shipping_address,
	}
	res = api.create_or_update_customer(data)
	if 'customerRefNo' in res:
		customer.db_set("foms_id", res['customerRefNo'])

def create_raw_material(log):
	name = frappe.get_value("Item", log.get("rawMaterialRefNo"))
	types = "Raw Material"
	log = frappe._dict(log)

	if not name:
		doc = frappe.new_doc("Item")
		doc.item_code = log.rawMaterialRefNo
		doc.item_name = log.rawMaterialName
		doc.description = log.rawMaterialDescription
		doc.stock_uom = convert_uom(log.unitOfMeasurement)
		doc.item_group = types
		doc.safety_stock = log.safetyLevel
		doc.foms_id = log.id
		doc.insert()
		name = doc.name
	else:
		doc = frappe.get_doc("Item", name)
		doc.item_name = log.productName
		doc.description = log.productDesc or log.productDetail or log.productName
		doc.item_group = types
		doc.foms_id = log.id
		doc.db_update()

	return name

def convert_uom(foms_uom):
	return UOM_MAPPING.get(foms_uom) or foms_uom

def get_foms_settings(field):
	return frappe.db.get_single_value("FOMS Integration Settings", field)

def create_products(log):
	name = frappe.get_value("Item", log.get("productID"))
	types = "Products"
	log = frappe._dict(log)
	if not name:
		doc = frappe.new_doc("Item")
		doc.item_code = log.productID
		doc.item_name = log.productName
		doc.description = log.productDesc or log.productDetail or log.productName
		doc.stock_uom = get_foms_settings("product_uom")
		doc.item_group = types
		doc.foms_id = log.id
		doc.insert()
		name = doc.name
	else:
		doc = frappe.get_doc("Item", name)
		doc.item_name = log.productName
		doc.description = log.productDesc or log.productDetail or log.productName
		doc.item_group = types
		doc.foms_id = log.id
		doc.db_update()

	return name

def get_operation_no(operation):
	return OPERATION_MAP.get(operation) or 1

def create_bom_products(log, product_id):
	log = frappe._dict(log)
	item_name = frappe.get_value("Item", {"foms_id":product_id})
	# find existing
	name = find_existing_bom(item_name, log.productVersionName)
	if not name and item_name:
		for op in log.preHarvestProcess:
			op = frappe._dict(op)
			bom = frappe.new_doc("BOM")
			bom.item = item_name
			bom.operation_no = get_operation_no(op.processName)
			bom.foms_recipe_version = log.productVersionName

			bom.with_operations = 1
			bom.routing = get_routing_name(op.processName)

			bom.transfer_material_against = 'Work Order'

			if not op.productRawMaterial:
				continue

			for rm in op.productRawMaterial:
				rm = frappe._dict(rm)
				row = bom.append("items")
				row.item_code = rm.rawMaterialRefNo
				row.uom = convert_uom(rm.uomrm)
				row.qty = rm.qtyrm

			bom.insert()
			name = bom.name
	
	return name

def find_existing_bom(item, foms_version):
	return frappe.get_value("BOM", {"item":item, "foms_recipe_version":foms_version})

def get_operation_map_name(operation):
	op_no = get_operation_no(operation)
	return OPERATION_MAP_NAME.get(op_no or 1)

def get_routing_name(operation):
	operation_name = get_operation_map_name(operation)
	routing_name = operation_name
	name = frappe.get_value("Routing", routing_name)
	if not name:
		doc = frappe.new_doc("Routing")
		doc.routing_name = routing_name
		row = doc.append("operations")
		row.operation = get_operation_name(operation)
		row.operation_time = get_foms_settings("operation_time")
		doc.insert(ignore_permissions=1)
		name = doc.name

	return name

def get_operation_name(operation):
	operation_name = get_operation_map_name(operation)
	name = frappe.get_value("Operation", operation_name)
	if not name:
		doc = frappe.new_doc("Operation")
		doc.__newname = operation_name
		doc.description = operation_name
		doc.insert(ignore_permissions=1)
		name = doc.name
	
	return name
	
# WORK ORDER (GET)
def get_work_order(show_progress=False):
	def get_data(gd):
		data = gd.api.get_work_order_list(gd.farm_id)
		return data

	def post_process(gd, log):
		for d in log.get("products"):
			item_code = d.get("productRefNo")
			bom_no = frappe.db.get_value("Item", item_code, "default_bom")
			qty = 1
			create_work_order(item_code, bom_no, qty)

	def get_key_name(log):
		return log.get("workOrderNo")
	
	GetData(
		data_type = "Work Order",
		doc_type="Work Order",
		get_data=get_data,
		get_key_name = get_key_name,
		post_process=post_process,
		show_progress=show_progress
	).run()

def create_work_order(item_code, bom_no, qty=1):
	doc = frappe.new_doc("Work Order")
	doc.production_item = item_code
	doc.bom_no = bom_no
	doc.qty = qty
	doc.insert()

	return doc.name