import frappe, json
from six import string_types
from frappe.utils import flt, now_datetime
from erpnext.controllers.foms import (
    create_bom_products, 
    get_bom_for_work_order2, 
	get_foms_settings,
	create_work_order as _create_work_order
)
from frappe import _
from erpnext.manufacturing.doctype.job_card.job_card import make_stock_entry, make_time_log
from erpnext.manufacturing.doctype.work_order.work_order import make_stock_entry

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

@frappe.whitelist()
def update_work_order_operation_status(workOrderID, lotID, operationName, percentage=0):
	work_order_name = frappe.db.get_value("Work Order", {
		"foms_work_order": workOrderID,
		"foms_lot_id": lotID
	})

	if not work_order_name:
		frappe.throw(_(f"Missing Work Order with LotID {lotID}"), frappe.DoesNotExistError)
	
	operation_name = frappe.db.get_value("Job Card", {
		"work_order":work_order_name,
		"operation": operationName,
		"docstatus":0
	})

	if not operation_name:
		frappe.throw(_(f"Missing Operation {operationName} for Work Order {workOrderID}"), frappe.DoesNotExistError)
	
	job_card = frappe.get_doc("Job Card", operation_name)

	# temporary stock entry is created based on work order (stright flow)
	if not job_card.transferred_qty:
		se_doc = make_stock_entry(job_card.name)
		se_doc.save()
		se_doc.submit()

	# start job card
	if not job_card.job_started:
		employee = frappe.get_value("Employee")
		args = frappe._dict({
			"job_card_id": job_card.name,
			"start_time": now_datetime(),
			"employees": [employee],
			# "status": status
		})
		job_card.validate_sequence_id()
		job_card.add_time_log(args)
		job_card.started_time = now_datetime()
		job_card.job_started = 1
		job_card.save()

	if percentage > 0 and percentage < 100:
		job_card.percentage = percentage
		job_card.save()
	elif percentage == 100:
		# complete
		args = frappe._dict({
			"job_card_id": job_card.name,
			"complete_time": now_datetime(),
			# "status": status,
			"completed_qty": job_card.for_quantity # temporary like job card settings
		})
		job_card.validate_sequence_id()
		job_card.add_time_log(args)
		job_card.save()
		job_card.submit()

	return True

@frappe.whitelist()
def submit_work_order_finish_goods(workOrderID, lotID, qty):
	work_order_name = frappe.db.get_value("Work Order", {
		"foms_work_order": workOrderID,
		"foms_lot_id": lotID
	})

	if not work_order_name:
		frappe.throw(_(f"Missing Work Order with LotID {lotID}"), frappe.DoesNotExistError)
	
	se_doc = make_stock_entry(work_order_name,"Manufacture", qty, return_doc=1)
	se_doc.save()
	se_doc.submit()

	return {
		"stockEntry":se_doc.name
	}