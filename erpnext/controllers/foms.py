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

# RAW MATERIAL (GET)
def get_raw_material(show_progress=False):
	title = "Get FOMS raw material.."
	api = FomsAPI()
	farm_id = get_farm_id()
	def show_progress_bar(percent):
		if show_progress:
			frappe.publish_realtime("progress_foms_download", {
				"percent":percent,
				"title":title
			})
		  
	raw = api.get_raw_material(farm_id)
	data = raw.get("items")
	
	total_count = len(data)
	for i in range(total_count):
		d = data[i]

		# pull to foms data mapping
		map_doc = create_foms_data("Raw Material", d.get("rawMaterialRefNo"), d)
		result = create_raw_material(d)
		map_doc.doc_type = "Item"
		map_doc.doc_name = result
		map_doc.save()

		percent = (i+1)/total_count*100
		if i % 10 == 0:
			show_progress_bar(percent)

		

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
	exists = frappe.get_value("Item", log.get("rawMaterialRefNo"))
	return exists