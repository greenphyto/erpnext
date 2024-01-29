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
	"g":"gram"
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
	def __init__(self, data_type, get_data, get_key_name, post_process, show_progress=False):
		self.data_type = data_type
		self.show_progress = show_progress
		self.get_data = get_data
		self.get_key_name = get_key_name
		self.post_process = post_process
	
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
			
		raw = self.api.get_raw_material(self.farm_id)
		data = raw.get("items")

		data = self.get_data(self)

		
		total_count = len(data)
		for i in range(total_count):
			d = data[i]

			# pull to foms data mapping
			key_name = self.get_key_name(d)
			map_doc = create_foms_data("Raw Material", key_name, d)
			result = self.post_process(d)
			map_doc.doc_type = "Item"
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

	def post_process(log):
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

	def post_process(log):
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
# RECIPE (GET)
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

	if not name:
		log = frappe._dict(log)
		doc = frappe.new_doc("Item")
		doc.item_code = log.rawMaterialRefNo
		doc.item_name = log.rawMaterialName
		doc.description = log.rawMaterialDescription
		doc.stock_uom = convert_uom(log.unitOfMeasurement)
		doc.item_group = "Raw Material"
		doc.safety_stock = log.safetyLevel
		doc.insert()
		name = doc.name

	return name

def convert_uom(foms_uom):
	return UOM_MAPPING.get(foms_uom) or foms_uom

def get_foms_settings(field):
	return frappe.db.get_single_value("FOMS Integration Settings", field)

def create_products(log):
	name = frappe.get_value("Item", log.get("productID"))

	if not name:
		log = frappe._dict(log)
		doc = frappe.new_doc("Item")
		doc.item_code = log.productID
		doc.item_name = log.productName
		doc.description = log.productDesc or log.productDetail or log.productName
		doc.stock_uom = get_foms_settings("product_uom")
		doc.item_group = "Products"
		doc.insert()
		name = doc.name

	return name