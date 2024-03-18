import frappe, json
from six import string_types
from frappe.utils import flt
from erpnext.controllers.foms import (
    create_bom_products, 
    get_bom_for_work_order2, 
	get_foms_settings,
	create_work_order as _create_work_order
)
from frappe import _

def get_data(data):
	if isinstance(data, string_types):
		data = json.loads(data)
	data = frappe._dict(data)

	return data

@frappe.whitelist()
def ping_data(data):
	return data

@frappe.whitelist()
def create_bom(data):
	data = get_data(data)
		
	product_id = data.get("productID")
	
	result = create_bom_products(data, product_id )
	
	return {"bomId":result}

@frappe.whitelist()
def create_work_order(workOrderID, lotID, productID, qty, uom):
	submit = get_foms_settings("auto_submit_work_order")
	item_code = frappe.get_value("Item", {"foms_id":productID})
	if not item_code or productID==0:
		frappe.throw(_(f"Missing Item with Product ID {productID}"), frappe.DoesNotExistError)

	bom_no = get_bom_for_work_order2(item_code)
	if not bom_no:
		frappe.throw(_(f"Missing BOM for {item_code}"), frappe.DoesNotExistError)
		
	qty = flt(qty) or 1
	log = frappe._dict({
		"workOrderNo":workOrderID,
		"lotID":lotID,
	})
	result = _create_work_order(log, item_code, bom_no, qty, submit)

	return {"workOrderId":result}

