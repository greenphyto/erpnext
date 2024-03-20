import frappe
from erpnext.foms.doctype.foms_integration_settings.foms_integration_settings import FomsAPI,is_enable_integration, get_farm_id
from frappe.core.doctype.sync_log.sync_log import get_pending_log
from frappe.utils import cint
from erpnext.accounts.party import get_party_details
from erpnext.foms.doctype.foms_data_mapping.foms_data_mapping import create_foms_data
from erpnext.manufacturing.doctype.work_order.work_order import make_work_order
from frappe import _

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
	"Seeding":1,
	"Transfer + Growth":2,
	"Harvesting":3,
	"Packaging":3
}

OPERATION_MAP_NAME = {
	1:"Seeding",
	2:"Transplanting",
	3:"Harvesting",
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
			d = frappe._dict(data[i])

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
	submit = get_foms_settings("auto_submit_bom")

	def get_data(gd):
		data = gd.api.get_product_list_for_recipe(gd.farm_id)
		return data

	def post_process(gd, log):
		product_id =  log.get("id")
		raw = gd.api.get_product_process(gd.farm_id, product_id)
		return create_bom_products(raw, product_id, submit)

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

def create_bom_products(log, product_id, submit=False, force_new=False):
	return create_bom_products_version_2(log, product_id, submit, force_new)

# bom created based on 1 operation 1 work order
# so it will cause 1 operation 1 bom
# https://b83cw27ro1.larksuite.com/docx/FhH4dGmEZor3z2xQouEuNG9GsKp?from=from_copylink
def create_bom_products_version_1(log, product_id, submit=False):
	log = frappe._dict(log)
	item_name = frappe.get_value("Item", {"foms_id":product_id})
	name = None
	bom_map = {}
	# find existing
	if item_name:
		# # Pre Harvest Process
		# if item_name != "PR-AV-GN":
		# 	return name
		
		# join process Preharvest and PostHarvest
		print(303, log)
		if "process" in log:
			all_process = log.process
		else:
			all_process = log.preHarvestProcess + log.postHarvestProcess
		
		for op in all_process:
			op = frappe._dict(op)
			operation_no = get_operation_no(op.processName)
			bom = None
			if operation_no in bom_map:
				bom = bom_map[operation_no]
				name = bom.name
				status = bom.docstatus
			else:
				name, status = find_existing_bom(item_name, log.productVersionName, operation_no) 

			if not name:
				bom = frappe.new_doc("BOM")
				bom.item = item_name
				bom.operation_no = operation_no
				bom.foms_recipe_version = log.productVersionName

				bom.with_operations = 1
				bom.routing = get_routing_name(op.processName)

				if bom.operation_no == 1:
					bom.is_default = 1
				else:
					bom.is_default = 0

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
			
			else:
				if not bom:
					bom = frappe.get_doc("BOM", name)

				if bom.operation_no == 1:
					bom.is_default = 1
				else:
					bom.is_default = 0

				for rm in op.productRawMaterial:
					rm = frappe._dict(rm)
					row = bom.append("items")
					row.item_code = rm.rawMaterialRefNo
					row.uom = convert_uom(rm.uomrm)
					row.qty = rm.qtyrm

				bom.save()
			
			bom_map[operation_no] = bom

		if submit:
			for operation_no, bom in bom_map.items():
				if bom.docstatus == 0:
					bom.submit()
	
	return name

# this is 1 BOM can have 3 operation (multiple operation in 1 bom)
# so the work order will be just 1 and has 3 job card
# each job card will be finish each operation one-by-one
def create_bom_products_version_2(log, product_id, submit=False, force_new=False):
	log = frappe._dict(log)
	if not product_id:
		frappe.throw(_(f"Missing Item with Product ID {product_id}"), frappe.DoesNotExistError)
	item_name = frappe.get_value("Item", {"foms_id":product_id})

	name = None
	bom = None

	if item_name:
		
		# join process Preharvest and PostHarvest
		if "process" in log:
			all_process = log.process
		else:
			all_process = log.preHarvestProcess + log.postHarvestProcess
		
		name, status = find_existing_bom2(item_name, log.productVersionName) 

		if not name or force_new:
			operation_map = {}
			bom = frappe.new_doc("BOM")
			bom.item = item_name
			bom.foms_recipe_version = log.productVersionName
			bom.with_operations = 1
			bom.transfer_material_against = 'Job Card'
						
			for op in all_process:
				op = frappe._dict(op)
				operation_name = get_operation_map_name(op.processName)

				if not operation_name in operation_map:
					op_row = bom.append("operations")
					op_row.operation = operation_name
					op_row.time_in_mins = get_foms_settings("operation_time") or 60*24 #(24 hours)
					op_row.workstation = get_foms_settings("workstation")
					op_row.fixed_time = 1
					op_row.description = operation_name
					operation_map[operation_name] = op_row

				if op.productRawMaterial:
					for rm in op.productRawMaterial:
						rm = frappe._dict(rm)
						row = bom.append("items")
						row.item_code = rm.rawMaterialRefNo
						row.uom = convert_uom(rm.uomrm)
						row.qty = rm.qtyrm
						row.operation = operation_name
			bom.save()
			name = bom.name
		else:
			if not bom:
				bom = frappe.get_doc("BOM", name)
			bom.save()

		if submit and bom:
			if bom.docstatus == 0:
				bom.submit()
	
	return name

def find_existing_bom(item, foms_version, operation_no):
	return frappe.get_value("BOM", {
		"item":item, 
		"foms_recipe_version":foms_version,
		"operation_no": operation_no,
		"docstatus":["!=", 2]
	}, ["name", "docstatus"]) or (None, None)

def find_existing_bom2(item, foms_version):
	return frappe.get_value("BOM", {
		"item":item, 
		"foms_recipe_version":foms_version,
		"operation_no": "",
		"docstatus":["!=", 2]
	}, ["name", "docstatus"]) or (None, None)

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
		row.operation_time = get_foms_settings("operation_time") or 60
		row.workstation = get_foms_settings("workstation")
		row.fixed_time = 1
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

def get_bom_for_work_order(item_code):
	return frappe.get_value("BOM", {
		"item":item_code,
		"operation_no":1,
		"docstatus":1
	}, "name", order_by="foms_recipe_version")

def get_bom_for_work_order2(item_code):
	return frappe.get_value("BOM", {
		"item":item_code,
		"operation_no":"",
		"docstatus":1
	}, "name", order_by="foms_recipe_version")
	
# WORK ORDER (GET)
def get_work_order(show_progress=False, work_order=""):
	def get_data(gd):
		data = gd.api.get_work_order_list(gd.farm_id, work_order=work_order)
		return data

	def post_process(gd, log):
		submit = get_foms_settings("auto_submit_work_order")
		for d in log.get("products"):
			item_code = d.get("productRefNo")
			bom_no = get_bom_for_work_order(item_code)
			qty = 1

			create_work_order(log, item_code, bom_no, qty, submit)

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

def create_work_order(log, item_code, bom_no, qty=1, submit=False):
	
	doc = make_work_order(bom_no, item_code, qty)
	doc.foms_work_order = log.workOrderNo
	doc.foms_lot_id = log.lotID
	doc.insert()

	if submit:
		doc.submit()

	return doc.name