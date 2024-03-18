import frappe, json
from six import string_types
from erpnext.controllers.foms import create_bom_products


@frappe.whitelist()
def ping_data(data):
	print("GET DATA", data)
	return data

@frappe.whitelist()
def create_bom(data):
	print(12, data)
	if isinstance(data, string_types):
		data = json.loads(data)
		
	data = frappe._dict(data)
	product_id = data.get("productID")
	
	create_bom_products(data, product_id )
	
	return product_id