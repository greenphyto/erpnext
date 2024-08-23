import frappe
from erpnext.foms.doctype.foms_integration_settings.foms_integration_settings import FomsAPI,is_enable_integration, get_farm_id
from frappe.core.doctype.sync_log.sync_log import get_pending_log
from frappe.utils import cint, flt, cstr, get_time, getdate,add_days
from erpnext.accounts.party import get_party_details
from erpnext.foms.doctype.foms_data_mapping.foms_data_mapping import create_foms_data
from erpnext.manufacturing.doctype.work_order.work_order import make_work_order
from frappe import _
from frappe.core.doctype.sync_log.sync_log import update_success, create_log, delete_log
import json
from erpnext import get_company_currency, get_default_company

"""
Make Supplier from ERP to FOMS
can update or delete
supplierID = foms_id
"""

# VARIABLE
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

# FOMS UOM to ERP UOM
UOM_MAP = {
	"L":"Litre",
	"g":"Gram",
	"kg":"Kg",
	"unit":"Unit",
	"ml":"Millilitre",
}

# see on hooks.py on sync_log_method
METHOD_MAP = {
	"Supplier":1,
	"Customer":2,
	"Warehouse":3,
	"Purchase Receipt":4,
	"Sales Order":5,
	"Stock Reconciliation":6,
	"Scrap Request":7,
	"Department":8,
	"Delivery Note":9,
}

UOM_KG_CONVERTION = {
	"Gram":1000,
	"Litre":1,
	"Millilitre":1000
}

TRANFER_AGAIN = 'Job Card'

def get_uom(uom_foms, default=""):
	uom_foms = uom_foms or default or'kg'
	uom = UOM_MAP.get(uom_foms)

	if not uom:
		uom = frappe.db.exists("Item", uom_foms)
	
	if not uom:
		frappe.throw(_(f"Missing UOM for {uom_foms}"), frappe.DoesNotExistError)
	
	return uom

def convert_uom(uom):
	for key, val in UOM_MAP.items():
		if val == uom:
			return key
	
	return 'kg'

def get_foms_settings(field):
	return frappe.db.get_single_value("FOMS Integration Settings", field)


class GetData():
	def __init__(self, data_type, get_data, get_key_name, post_process, doc_type="", show_progress=False, manual_save_log=False):
		self.data_type = data_type
		self.show_progress = show_progress
		self.get_data = get_data
		self.get_key_name = get_key_name
		self.post_process = post_process
		self.manual_save_log = manual_save_log
		self.doc_type = doc_type or data_type
	
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

		def do_create(i):
			d = frappe._dict(data[i])

			# pull to foms data mapping
			result = self.post_process(self, d)
			if not self.manual_save_log:
				key_name = self.get_key_name(d)
				save_log(self.doc_type, result, key_name, d)

			percent = (i+1)/total_count*100
			if i % 10 == 0:
				show_progress_bar(percent)

		
		total_count = len(data)
		for i in range(total_count):
			do_create(i)

# ###### TOOLS ###### #

# for create one-by-obe log, based on doctype and name
def sync_log(doc, method=""):
	cancel = doc.docstatus == 2

	method_id = METHOD_MAP.get(doc.doctype)

	if not cancel:
		log_name = create_log(doc.doctype, doc.name, method=method_id)

		# start enquee individually, if fail, it will try again with scheduler itself
		frappe.enqueue("erpnext.controllers.foms.start_sync_enquee", log_name=log_name)
		
	else:
		# not yet update to FOMS
		if delete_log(doc.doctype, doc.name):
			return
		# yet updated to FOMS
		else:
			# [unfinish] create cancel transaction when alr submit receipt item
			# quick check on foms when allow/disallow to cancel
			# and really prohibit the user if really cannot cancelling
			pass

def start_sync_enquee(log_name):
	log = frappe.get_doc("Sync Log", log_name)
	log.sync()

def sync_controller(doctype, controller):
	if not is_enable_integration():
			return 
		
	api = FomsAPI()

	logs = get_pending_log({"doctype": doctype})
	count = len(logs)
	i = 0
	for log in logs:
		# create new if not have
		if log.update_type == "Update":
			controller(log, api=None)
		
		show_progress(i, count)
		i+=1
	show_progress(i, count)

def update_reff_id(res, doc, key_name):
	if res and 'id' in res:
		doc.db_set("foms_id", res['id'])
		doc.db_set("foms_name", res.get(key_name))

def save_log(doc_type, data_name, key_name, data):
	if doc_type == "Item":
		p+=1
	map_doc = create_foms_data(doc_type, key_name, data)
	map_doc.doc_type = doc_type
	map_doc.doc_name = data_name
	map_doc.save()

def show_progress(current=0, total=100):
	if not current:
		return
	
	percent = current/total*100
	frappe.publish_progress(percent, title="Sync FOMS data..")
	frappe.publish_realtime(
		event="foms_sync_progress",
		message={
			"percent":percent
		}
	)


# ###### ***** ##### #


# RAW MATERIAL (GET)
def get_raw_material(show_progress=False, reff_no=""):
	def get_data(gd):
		raw = gd.api.get_raw_material(gd.farm_id, reff_no=reff_no)
		data = raw.get("items")
		return data

	def post_process(gd, log):
		result = create_raw_material(log) 
		return result

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
def get_recipe(show_progress=False, item_code=""):
	submit = get_foms_settings("auto_submit_bom")

	def get_data(gd):
		if not item_code:
			data = gd.api.get_product_list_for_recipe(gd.farm_id)
		else:
			product_id = frappe.get_value("Item", item_code, "foms_product_id")
			data = [frappe._dict({'id':product_id})]
		
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
	

# WAREHOUSE
def update_warehouse():
	sync_controller("Warehouse", _update_warehouse)

def _update_warehouse(log, api=None):
	if not api:
		api = FomsAPI()

	farm_id = get_foms_settings("farm_id")
	doc = frappe.get_doc("Warehouse", log.docname)
	wh_id = doc.name[:12]
	# wh_id = doc.name
	data = {
		"farmId": farm_id,
		"warehouseID": wh_id,
		"warehouseName": doc.warehouse_name,
		"countryCode": "SG", # not yet
		"capacity": 0,
		"uom": "Kg", # not yet
		"address": "",
		"noRackRow": cint(doc.row_no),
		"noRackLevel": cint(doc.level_no),
		"noOfLane": cint(doc.lane_no),
		"isFromERP": True
	}

	if doc.foms_id:
		data["id"] = doc.foms_id

	api.log = log
	res = api.update_warehouse(data)
	update_reff_id(res, doc, "warehouseID")
	return res

def sync_all_warehouse(show_progress=False):
	# foms to erp
	foms_all_warehouses()

	# find not exist foms id 
	docs = frappe.db.get_all("Warehouse", {"foms_id": ['is', 'not set']})
	for d in docs:
		# generate log
		create_log("Warehouse", d.name, method=METHOD_MAP.get("Warehouse"))

	# from erp to foms
	update_warehouse()

	return True

def foms_all_warehouses():
	farm_id = get_farm_id()
	api = FomsAPI()
	data = api.get_all_warehouse(farm_id)
	for d in data.get("items", []):
		# not yet finish
		wh_name = d.get("warehouseName")
		frappe.db.set_value("Warehouse", {"warehouse_name": wh_name}, "foms_id", d['id'])
		frappe.db.set_value("Warehouse", {"warehouse_name": wh_name}, "foms_name", d['warehouseID'])

# RAW MATERIAL RECEIPT
def update_stock_recipe():
	sync_controller("Purchase Receipt", _update_stock_recipe)

def _update_stock_recipe(log, api=None):
	if not api:
		api = FomsAPI()

	doc = frappe.get_doc("Purchase Receipt", log.docname)
	for d in doc.get("items"):
		expiry_date = frappe.get_value("Batch", d.batch_no, "expiry_date")
		warehouse_id = frappe.get_value("Warehouse", d.warehouse, "foms_id")
		supplier_id = frappe.get_value("Supplier", doc.supplier, "foms_id")
		raw_id = frappe.get_value("Item", d.item_code, "foms_raw_id")
		# need convert current PR receive to item default
		data = {
			"id": 0,
			"rawMaterialId": raw_id,
			"batchRefNo": d.batch_no,
			"dateOfCreation": doc.creation,
			"expiryDate": expiry_date,
			"warehouseId": warehouse_id,
			"supplierId": supplier_id,
			"quantity": d.qty
		}

		api.log = log  # working with log
		res = api.update_raw_material_receipt(data)
		if res:
			frappe.db.set_value("Batch", d.batch_no, "foms_id", res.get('id'))
			frappe.db.set_value("Batch", d.batch_no, "foms_name", res.get('batchRefNo'))

# SUPPLIER (POST)
def sync_all_supplier(show_progress=False):

	# matching existing first
	foms_all_supplier()
	
	# find not exist foms id 
	suppliers = frappe.db.get_all("Supplier", {"foms_id": ['is', 'not set']})
	for d in suppliers:
		# generate log
		create_log("Supplier", d.name, method=METHOD_MAP.get("Supplier"))

	# push the log
	update_foms_supplier()

	return True

def foms_all_supplier():
	farm_id = get_farm_id()
	api = FomsAPI()
	data = api.get_all_supplier(farm_id)
	for d in data.get("items", []):
		# not yet finish
		name = d.get("supplierName")
		print("Renaming", name, d['id'])
		frappe.db.set_value("Supplier", {"supplier_name": name}, "foms_id", d['id'])
		frappe.db.set_value("Supplier", {"supplier_name": name}, "foms_name", d['supplierRefNo'])

def update_foms_supplier():
	sync_controller("Supplier", _update_foms_supplier)


def _update_foms_supplier(log, api=None):
	if not api:
		api = FomsAPI()
	supplier = frappe.get_doc("Supplier", log.docname)
	details = get_party_details(supplier.name, party_type="Supplier")
	farm_id = get_farm_id()
	data = {
		"farmId": farm_id,
		"id": cint(supplier.foms_id),
		"supplierID": supplier.supplier_code,
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
		"isFromErp": True
	}

	if supplier.foms_id:
		data['Id'] = supplier.foms_id

	api.log = log
	res = api.create_or_update_supplier(data)
	update_reff_id(res, supplier, "supplierID")

# CUSTOMER (POST)
def sync_all_customer(show_progress=False):
	foms_all_customer()

	# find not exist foms id 
	customers = frappe.db.get_all("Customer", {"foms_id": ['is', 'not set']})
	for d in customers:
		# generate log
		create_log("Customer", d.name, method=METHOD_MAP.get("Customer"))

	# push the log
	update_foms_customer()

	return True


def foms_all_customer(show_progress=False):
	farm_id = get_farm_id()
	api = FomsAPI()
	data = api.get_all_customer(farm_id)
	for d in data.get("items", []):
		# not yet finish
		name = d.get("customerName")
		frappe.db.set_value("Customer", {"customer_name": name}, "foms_id", d['id'])
		frappe.db.set_value("Customer", {"customer_name": name}, "foms_name", d['customerRefNo'])

def update_foms_customer():
	sync_controller("Customer", _update_foms_customer)

def _update_foms_customer(log, api=None):
	if not api:
		api = FomsAPI()

	customer = frappe.get_doc("Customer", log.docname)
	details = get_party_details(customer.name, party_type="Customer")
	farm_id = get_farm_id()
	address = details.address_display or details.company_address_display
	shipping_address = details.get("shipping_address") or address

	customer_name = customer.customer_name
	cust_id = customer.customer_code
	if cust_id == "C00008":
		customer_name = "Cash Sales"

	data = {
		"farmId": farm_id,
		"customerRefNo": cust_id,
		"customerName": customer_name,
		"address": address,
		"contact": customer.mobile_no or  details.contact_mobile or "" ,
		"email": customer.email_id or details.contact_email or "user@example.com",
		"creditLimit": 0,
		"creditTermID": 0,
		"contactPerson": details.contact_person or "",
		"countryCode": frappe.db.get_single_value('FOMS Integration Settings', "country_id"),
		"deliveryAddress": shipping_address,
	}

	if customer.foms_id:
		data['Id'] = customer.foms_id

	api.log = log
	res = api.create_or_update_customer(data)
	update_reff_id(res, customer, "customerRefNo" )

# PACKAGING (GET)
def get_packaging(show_progress=False):
	api = FomsAPI()
	data = frappe.db.get_all("Item", {"foms_product_id":['!=', 0]}, ['name', 'foms_product_id'])
	for d in data:
		packs = api.get_packaging(d.foms_product_id)
		doc = frappe.get_doc("Item", d.name)
		doc.packaging = []
		for d in packs or []:
			pack_name = create_packaging(d)
			row = doc.append("packaging")
			row.packaging = pack_name

		doc.save()

def create_packaging(log):
	name = frappe.get_value("Packaging", log.get("packageName"))
	log = frappe._dict(log)
	if not name:
		doc = frappe.new_doc("Packaging")
		doc.title = log.packageName[:159]
		doc.description = log.packageName
		doc.package_type = log.packageType
		doc.foms_id = log.id		
	else:
		doc = frappe.get_doc("Packaging", name)
		doc.description = log.packageName

	doc.quantity = log.packageWeight
	doc.uom = get_uom(log.uom, "g")
	factor = UOM_KG_CONVERTION.get(doc.uom) or 1
	doc.total_weight = flt(doc.quantity/factor)

	if doc.is_new():
		doc.insert(ignore_permissions=1)
	else:
		doc.save()

	return doc.name

# BATCH (GET)
def get_batch(show_progress=False):
	def get_data(gd):
		data = gd.api.get_all_batch()
		if "items" in data:
			return data.get("items")
		return {}

	def post_process(gd, log):
		return create_batch(log) 

	def get_key_name(log):
		return log.get("batchRefNo")
	
	GetData(
		data_type = "Batch",
		get_data=get_data,
		get_key_name = get_key_name,
		post_process=post_process,
		show_progress=show_progress
	).run()

def create_batch(log):
	log = frappe._dict(log)
	name = frappe.get_value("Batch", log.batchRefNo)
	if not name:
		doc = frappe.new_doc("Batch")
		doc.batch_id = log.batchRefNo
		item_code = frappe.get_value("Item", {"foms_id": cstr(log.rawMaterialId)})
		if not item_code:
			return ""
		doc.item = item_code
	else:
		doc = frappe.get_doc("Batch", name)
	shelf_life_in_days = frappe.db.get_value(
		"Item", doc.item, ["shelf_life_in_days"]
	) or 0
	doc.manufacturing_date = getdate(log.dateOfCreation) or getdate()
	doc.expiry_date = getdate(log.expiryDate) or add_days(getdate(), shelf_life_in_days)
	doc.foms_id = log.id
	if doc.is_new():
		doc.insert(ignore_permissions=1)
	else:
		doc.save()

	name = doc.name

	return name

# SALES ORDER (POST)
def sync_log_so(doc, method=""):
	if doc.get("non_package_item"):
		return
	else:
		sync_log(doc)
		
def update_foms_sales_order():
	sync_controller("Sales Order", _update_foms_sales_order)

def _update_foms_sales_order(log, api=None):
	if not api:
		api = FomsAPI()

	doc = frappe.get_doc("Sales Order", log.docname)
	customer = frappe.get_doc("Customer", doc.customer)
	farm_id = get_farm_id()

	so_id = cint(doc.get("foms_id"))
	req_id = cint(doc.get("req_id"))

	products = []
	
	for d in doc.get("items"):
		product_id = frappe.get_value("Item", d.item_code, "foms_product_id")
		package_id = frappe.get_value("Packaging", d.uom, "foms_id")
		child_id = cint(d.get("foms_id"))
		item = {
			"isWeightOrder": True if d.weight_order else False,
			"productId": product_id,
			"quantity": d.qty,
			"uom": convert_uom(d.stock_uom),
			"totalNetWeight": d.stock_qty,
			"isRootInclude": "false",
			"unitPrice": d.rate,
			"id":child_id
		}
		if package_id:
			item["packageId"] = cint(package_id)

		products.append(item)

	data = {
		"orderType": "One-off",
		"deliveryDate": getdate(doc.delivery_date),
		"customerId": customer.foms_id or "",
		"purchaseOrderNumber": doc.po_no or "-",
		"saleOrder": {
			"saleOrderNumber":doc.name, 
			"farmId": farm_id,
			"subSaleOrders": products,
			"id": so_id
		},
		"farmId": farm_id,
		"id":req_id
	}

	api.log = log
	res = api.create_customer_order(data)
	if res:
		doc.foms_id = res['saleOrder']['id']
		doc.req_id = res['id']
		for d in res['saleOrder']['subSaleOrders']:
			item_code = frappe.get_value("Item", {"foms_product_id": cstr(d['productId'])})
			packaging = frappe.get_value("Packaging", {"foms_id": cstr(d['packageId'])})
			# key on product id, package id, uom, quantity, unit price
			for row in doc.get("items", {
				"item_code":item_code,
				"uom":packaging
			}):
				row.foms_id = d['id']
				row.db_update()
		doc.db_update()

def get_foms_format(date):
	return getdate(date).strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'

def update_foms_delivery():
	sync_controller("Delivery Note", _sync_delivery_note)

def _sync_delivery_note(log, api=None):
	if not api:
		api = FomsAPI()

	doc = frappe.get_doc("Delivery Note", log.docname)
	customer = frappe.get_doc("Customer", doc.customer)
	farm_id = get_farm_id()

	data = frappe._dict({
		"farmId": 0,
		"deliveryOrderRefNo": doc.name,
		"erpDeliveryOrderId": doc.name,
		"erpSaleOrderNo": "",
		"customer": doc.customer,
		"customerAddress": doc.address_display,
		"remarks": doc.instructions,
		"deliveryOrderDetails": [],
		"id": 0
	})

	for d in doc.get("items"):
		data.deliveryOrderDetails.append({
			"itemCode": d.item_code,
			"itemName": d.item_name,
			"qty": d.qty,
			"uom": d.uom,
			"remarks": d.description,
			"warehouse": d.warehouse,
			"batchNo": d.batch_no,
			"id": 0
		})

	api.log = log
	res = api.create_delivery_note(data)

# SCRAP REQUEST
def update_foms_scrap_request():
	sync_controller("Scrap Request", _update_foms_scrap_request)

def _update_foms_scrap_request(log, api=None):
	if not api:
		api = FomsAPI()

	doc = frappe.get_doc("Scrap Request", log.docname)
	api.log = log
	for d in doc.get("items"):
		batch_id = frappe.get_value("Batch", d.batch, "foms_id")
		data = {
			"RawMaterialBatchID": cint(batch_id)
		}
		res = api.post_scrap_issue(data)

# DEPARTMENT
def update_foms_department():
	sync_controller("Department", _update_foms_department)

def _update_foms_department(log, api=None):
	if not api:
		api = FomsAPI()

	doc = frappe.get_doc("Department", log.docname)
	api.log = log
	data = {
		"name": doc.name,
		"departmentName": doc.department_name,
		"parentDepartment": doc.parent_department,
		"company": doc.company,
		"id": cint(doc.foms_id)
	}
	res = api.update_foms_department(data)

	id = res.get("id")
	doc.db_set("foms_id", cint(id))

# SALES RECONCILLIATION (POST)
def update_foms_stock_recon():
	sync_controller("Stock Reconciliation", _update_foms_stock_recon)

def _update_foms_stock_recon(log, api=None):
	if not api:
		api = FomsAPI()

	doc = frappe.get_doc("Stock Reconciliation", log.docname)
	farm_id = get_farm_id()

	success = 0
	for d in doc.get("items"):
		if cint(d.foms_sync):
			success += 1
			continue

		item_id = frappe.get_value("Item", d.item_code, "foms_id")
		warehouse_id = frappe.get_value("Warehouse", d.warehouse, "foms_id")
		batch_id = frappe.get_value("Batch", d.batch_no, "foms_id")
		data = {
			"rawMaterialId": item_id,
			"batchRefNo": d.batch_no,
			"warehouseId": warehouse_id,
			"quantity": flt(d.qty),
			"FarmId": farm_id,
			"id": cint(batch_id)
		}
		api.log = log
		try:
			res = api.update_raw_material_batch_qty(data)
			if res:
				d.foms_sync = 1
				success += 1
				d.db_update()
		except:
			pass
	
	doc.sync_percent = success/len(doc.get("items"))*100
	doc.db_update()

def create_raw_material(log):
	name = frappe.get_value("Item", log.get("rawMaterialRefNo"))
	types = "Raw Material"
	log = frappe._dict(log)
	
	if not name:
		doc = frappe.new_doc("Item")
		doc.item_code = log.rawMaterialRefNo
		doc.item_name = log.rawMaterialName
		doc.description = log.rawMaterialDescription
		doc.stock_uom = get_uom(log.unitOfMeasurement)
		doc.item_group = types
		doc.is_purchase_item = 1
		doc.is_sales_item = 0
		doc.is_stock_item = 1
		doc.has_expiry_date = 1
		doc.has_batch_no = 1
		doc.create_new_batch = 1
		doc.batch_number_series = doc.item_code + "-" + "BN.#####"

		doc.lead_time_days = cint(log.RequestLeadTime)
		doc.min_order_qty = flt(log.MinimumOrderQuantity)
		doc.safety_stock = log.safetyLevel
		doc.shelf_life_in_days = 365
		doc.valuation_method = "FIFO"
		doc.foms_raw_id = log.id
		doc.get_item_material_group(set_data=1)
		doc.insert(ignore_permissions=1)
		name = doc.name
	else:
		# validate_id
		exists_id = frappe.db.get_value("Item", {"item_code":['!=', log.rawMaterialRefNo], "foms_raw_id":cstr(log.id)}, "name")
		if exists_id:
			frappe.throw(_(f"ID {log.id} already use by another item ({exists_id})!"))
		doc = frappe.get_doc("Item", name)
		doc.item_name = log.productName
		doc.description = log.productDesc or log.productDetail or log.productName
		doc.item_group = types
		doc.lead_time_days = cint(log.RequestLeadTime)
		doc.min_order_qty = flt(log.MinimumOrderQuantity)
		doc.safety_stock = log.safetyLevel
		doc.shelf_life_in_days = 365
		doc.is_stock_item = 1
		if not doc.foms_raw_id:
			doc.foms_raw_id = log.id
		doc.save()

	return name

def create_products(log):
	name = frappe.get_value("Item", log.get("productID"))
	types = "Products"
	log = frappe._dict(log)
	if not name:
		doc = frappe.new_doc("Item")
		doc.item_code = log.productID
		doc.item_name = log.productName
		doc.description = log.productDesc or log.productDetail or log.productName
		doc.stock_uom = get_uom(log.unitOfMeasurement)
		doc.foms_product_id = log.id
		doc.is_stock_item = 1
		doc.valuation_method = "FIFO"
		doc.batch_number_series = doc.item_code + "-" + "BN.#####"
		name = doc.name
	else:
		doc = frappe.get_doc("Item", name)
		doc.item_name = log.productName
		doc.description = log.productDesc or log.productDetail or log.productName
		doc.is_stock_item = 1
		if not doc.foms_product_id:
			doc.foms_product_id = log.id

	doc.item_group = types
	doc.shelf_life_in_days = 365
	doc.has_expiry_date = 1
	doc.has_batch_no = 1
	doc.create_new_batch = 1
	doc.batch_number_series = doc.item_code + "-" + "BN.#####"
	doc.get_item_material_group(set_data=1)
	doc.weight_per_unit = 1
	doc.weight_uom = "Kg"


	if doc.is_new():
		doc.insert(ignore_permissions=1)
	else:
		doc.save()

	create_workstation_process(doc.item_code)

	return name

def create_workstation_process(item_code):
	default = get_foms_settings("workstation")
	for i,operation in OPERATION_MAP_NAME.items():
		exists = get_workstation_name(item_code, operation)
		if not exists or exists == default:
			doc = frappe.new_doc("Workstation")
			doc.item_code = item_code
			doc.operation = operation
			doc.calculation_type = "Per KG"
			doc.insert(ignore_permissions=1)

def get_operation_no(operation):
	return OPERATION_MAP.get(operation) or 1

def create_bom_products(log, product_id, submit=False, force_new=False):
	return create_bom_products_version_2(log, product_id, submit, force_new)

# bom created based on 1 operation 1 work order
# so it will cause 1 operation 1 bom
# https://b83cw27ro1.larksuite.com/docx/FhH4dGmEZor3z2xQouEuNG9GsKp?from=from_copylink
def create_bom_products_version_1(log, product_id, submit=False):
	log = frappe._dict(log)
	item_name = frappe.get_value("Item", {"foms_product_id":product_id})
	name = None
	bom_map = {}
	# find existing
	if item_name:
		# # Pre Harvest Process
		# if item_name != "PR-AV-GN":
		# 	return name
		
		# join process Preharvest and PostHarvest
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

				bom.transfer_material_against = TRANSFER_AGAIN

				if not op.productRawMaterial:
					continue

				for rm in op.productRawMaterial:
					rm = frappe._dict(rm)
					row = bom.append("items")
					row.item_code = rm.rawMaterialRefNo
					row.uom = get_uom(rm.uomrm)
					row.qty = rm.qtyrmInKg

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
					row.uom = get_uom(rm.uomrm)
					row.qty = rm.qtyrmInKg

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
	item_name = frappe.get_value("Item", {"foms_product_id":product_id})

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
			bom.transfer_material_against = TRANFER_AGAIN
						
			for op in all_process:
				op = frappe._dict(op)
				operation_name = get_operation_map_name(op.processName)

				if not operation_name in operation_map:
					op_row = bom.append("operations")
					op_row.operation = operation_name
					op_row.time_in_mins = 60
					op_row.workstation = get_workstation_name(item_name, operation_name)
					op_row.description = operation_name
					operation_map[operation_name] = op_row

				if op.productRawMaterial:
					for rm in op.productRawMaterial:
						rm = frappe._dict(rm)
						item_name = frappe.get_value("Item", rm.rawMaterialRefNo)
						if not item_name:
							continue

						row = bom.append("items")
						row.item_code = rm.rawMaterialRefNo
						row.uom = get_uom(rm.uomrm)
						if row.uom in ['Unit']:
							row.qty = cint(rm.qtyrmInKg)
						else:
							row.qty = rm.qtyrmInKg
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

def get_workstation_name(item_name, operation_name):
	name = frappe.get_value("Workstation", {"item_code":item_name, "operation": operation_name})
	if name:
		return name
	else:
		return get_foms_settings("workstation")

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

def get_bom_for_work_order2(item_code):
	return frappe.get_value("BOM", {
		"item":item_code,
		"operation_no":1,
		"docstatus":1
	}, "name", order_by="foms_recipe_version")

def get_bom_for_work_order(item_code):
	return frappe.get_value("BOM", {
		"item":item_code,
		"docstatus":1,
		"is_default":1
	}, "name", order_by="foms_recipe_version")
	
# WORK ORDER (GET)
def get_work_order(show_progress=False, work_order=""):
	def get_data(gd):
		data = gd.api.get_work_order_list(gd.farm_id, work_order=work_order)
		return data

	def post_process(gd, log):
		detail_log = gd.api.get_work_order_detail(gd.farm_id, work_order=log.id)
		if not detail_log:
			return

		
		submit = get_foms_settings("auto_submit_work_order")
		for d in detail_log:
			d = frappe._dict(d)
			# update data
			d.workOrderNo = log.get("workOrderNo")
			d.id = log.get("id")

			item_code = d.get("productRefNo")
			bom_no = get_bom_for_work_order(item_code)
			qty = 1

			result = None
			try:
				if bom_no:
					result = create_work_order(d, item_code, bom_no, qty, submit)
				
				save_log("Work Order", result, d.get("lotId"), log)
			except Exception as e:
				print("error with ",item_code, d.workOrderNo, d.id)
				continue

	def get_key_name(log):
		return log.get("workOrderNo")
	
	GetData(
		data_type = "Work Order",
		doc_type="Work Order",
		get_data=get_data,
		get_key_name = get_key_name,
		post_process=post_process,
		show_progress=show_progress,
		manual_save_log=1
	).run()

def create_work_order(log, item_code, bom_no, qty=1, submit=False, return_doc=False):
	doc = make_work_order(bom_no, item_code, qty)
	validate_operation(doc)
	doc.foms_work_order = log.workOrderNo
	doc.foms_lot_id = log.id
	doc.foms_lot_name = log.lotId
	doc.sales_order_no = ", ".join(log.sales_order_no or [])
	doc.use_multi_level_bom = 0 #if use multi level bom it will use exploed items as raw material, but if not it will use bom items
	doc.insert()

	if submit:
		doc.submit()

	if return_doc:
		return doc
	return doc.name

def update_so_working(sub_so_id, lot_id):
	parent = frappe.get_value("Sales Order Item", {"foms_id":cstr(sub_so_id)})
	if not parent:
		return
	
	doc = frappe.get_doc("Sales Order", parent)
	for d in doc.get("items"):
		if d.foms_id == cstr(sub_so_id):
			d.db_set("lot_id", lot_id)
	doc.db_update()


def validate_operation(doc):
	# use default
	workstation_warehouse = get_foms_settings("workstation")
	for d in doc.operations:
		if not d.get("workstation"):
			d.workstation = workstation_warehouse

def get_raw_item_foms(item_id="", item_code=""):
	if item_id:
		item = frappe.get_value("Item", {"foms_raw_id":item_id})
	
	if not item and item_code:
		item = frappe.get_value("Item", item_code)
	
	return item

def create_delivery_order(log):
	# need to add foms id
	log = frappe._dict(log)
	doc = frappe.new_doc("Delivery Note")
	exists = frappe.get_value("Delivery Note", {"foms_id":cstr(log.id)})
	if exists:
		return exists
	
	doc.foms_id = log.id

	doc.customer = log.CustomerName
	for d in log.get("items") or []:
		d = frappe._dict(d)
		row = doc.append("items")
		row.item_code = d.Product_Id
		row.uom = d.uom
		row.qty = d.DONumberOfPacket
		row.rate = d.Price
		row.against_sales_order = d.SOnumber
	
	doc.save()

	return doc.name

def create_finish_goods_stock(data):
	"""
	reff:
	https://docs.erpnext.com/docs/user/manual/en/manufacturing-without-creating-bom

	question:
	- how to select account no when add cost

	data = {
		"material_reff":"",
		"posting_date":"2024-01-12 08:12:32",
		"company":"", // opt
		"bom":"",
		"id":"",
		"item_code":"",
		"qty":"",
		"uom":"",
		"batch":"",
		"batch_exp":"", // opt if not set, it will created from erp
		"batch_mfg":"", // opt
		"work_order_id":"",
		"lot_id":"",
		"rack_no":"",
		"customer_order_no:":"",
		"warehouse":""
		"materials":[{  // material consumed at end of process
			"item_code":"",
			"qty":"",
			"uom":"",
			"batch":"",
			"warehouse":""
		}],
		"additional_cost":[{
			"expense_account":"",
			"description":"",
			"amount":0
		}]
	}
	"""
	data = frappe._dict(data)

	# optional if find exist 

	doc = frappe.new_doc("Stock Entry")
	doc.foms_id = data.id
	# doc.material_reff = data.material_reff
	doc.posting_date = getdate(data.posting_date)
	doc.posting_time = get_time(data.posting_date)
	doc.stock_entry_type = "Manufacture"
	doc.company = get_default_company()
	doc.work_order_id = data.work_order_id
	doc.lot_id = data.lot_id
	doc.rack_no = data.rack_no
	doc.customer_order_no = data.customer_order_no
	if data.bom:
		doc.from_bom = 1
	if not "optional" in data.bom:
		doc.bom_no = data.bom

	# default_expense = frappe.db.get_single_value("Manufacturing Settings", "default_expense_account") 
	# if not default_expense:
	# 	frappe.throw(_("Please set <b>Default Expense Account</b> on Manufacturing Settings!"))

	# material issue
	for d in data.get("materials") or []:
		d = frappe._dict(d)
		row = doc.append("items")
		row.item_code = d.item_code
		row.qty = d.qty
		row.uom = d.uom
		row.s_warehouse = d.warehouse

	# finish goods
	row = doc.append("items")
	row.item_code = data.item_code
	row.qty = data.qty
	row.uom = data.uom
	row.t_warehouse = data.warehouse
	row.is_finished_item = 1

	# add cost
	for d in data.get("additional_cost") or []:
		row = doc.append("additional_costs")
		row.update(d)
		# row.expense_account = default_expense

	# temporary
	doc.flags.ignore_validate = 1
	doc.flags.ignore_mandatory = 1

	doc.insert(ignore_permissions=1)
	doc.submit()

	return {
		"StockEntryNo":doc.name
	}