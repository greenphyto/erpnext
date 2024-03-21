import frappe, json
from six import string_types
from frappe.utils import flt, now_datetime, cint, getdate, cstr
from erpnext.controllers.foms import (
    create_bom_products, 
    get_bom_for_work_order2, 
	get_foms_settings,
	create_work_order as _create_work_order,
	OPERATION_MAP_NAME,
	get_item_foms,
	get_uom
)
from frappe import _
from erpnext.manufacturing.doctype.job_card.job_card import make_stock_entry as make_stock_entry_jc, make_time_log
from erpnext.manufacturing.doctype.work_order.work_order import make_stock_entry as make_stock_entry_wo

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
	submit = get_foms_settings("auto_submit_bom")
	result = create_bom_products(data, product_id, submit=submit)
	
	return {"ERPBomId":result}

@frappe.whitelist()
def create_work_order(FomsWorkOrderID, FomsLotID, productID, qty, uom):
	submit = get_foms_settings("auto_submit_work_order")
	item_code = frappe.get_value("Item", {"foms_id":productID})
	if not item_code or productID==0:
		frappe.throw(_(f"Missing Item with Product ID {productID}"), frappe.DoesNotExistError)

	bom_no = get_bom_for_work_order2(item_code)
	if not bom_no:
		frappe.throw(_(f"Missing BOM for {item_code}"), frappe.DoesNotExistError)
		
	qty = flt(qty) or 1
	log = frappe._dict({
		"workOrderNo":FomsWorkOrderID,
		"FomsLotID":FomsLotID,
	})
	result = _create_work_order(log, item_code, bom_no, qty, submit)

	return {"ERPWorkOrderID":result}

@frappe.whitelist()
def update_work_order_operation_status(ERPWorkOrderID, operationNo, percentage=0):
	operationName = OPERATION_MAP_NAME.get( cint(operationNo) )
	work_order_name = frappe.db.get_value("Work Order", ERPWorkOrderID)

	if not work_order_name:
		frappe.throw(_(f"Work Order {ERPWorkOrderID} not found!"), frappe.DoesNotExistError)
	
	operation_name = frappe.db.get_value("Job Card", {
		"work_order":work_order_name,
		"operation": operationName,
		"docstatus":0
	})

	if not operation_name:
		frappe.throw(_(f"Missing Operation {operationName} for Work Order {ERPWorkOrderID}"), frappe.DoesNotExistError)
	
	transferred_qty, job_card_name = frappe.db.get_value("Job Card", operation_name, ["transferred_qty", "name"]) or (0, "")

	# temporary stock entry is created based on work order (stright flow)
	if not transferred_qty:
		se_doc = make_stock_entry_jc(job_card_name)
		se_doc.save()
		se_doc.submit()

	job_card = frappe.get_doc("Job Card", job_card_name)
	# start job card
	if not job_card.job_started:
		employee = frappe.get_value("Employee")
		args = frappe._dict({
			"job_card_id": job_card.name,
			"start_time": now_datetime(),
			# "employees": [{"name":employee}],
			# "status": status
		})
		job_card.validate_sequence_id()
		job_card.add_time_log(args)
		job_card.started_time = now_datetime()
		job_card.job_started = 1

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
	else:
		job_card.save()


	return True

@frappe.whitelist()
def submit_work_order_finish_goods(ERPWorkOrderID, qty):
	work_order_name = frappe.db.get_value("Work Order", ERPWorkOrderID)

	if not work_order_name:
		frappe.throw(_(f"Work Order {ERPWorkOrderID} not found!"), frappe.DoesNotExistError)
	
	se_doc = make_stock_entry_wo(work_order_name,"Manufacture", qty, return_doc=1)
	se_doc.save()
	se_doc.submit()

	return {
		"ERPStockEntry":se_doc.name
	}

# Create Material Reserve
@frappe.whitelist()
def create_raw_material_reserve(ERPWorkOrderID, status, items):
	work_order_name, qty, source_warehouse = frappe.get_value("Work Order", ERPWorkOrderID, ["name", "qty", "source_warehouse"]) or ("", 1, "")
	if not work_order_name:
		frappe.throw(_(f"Work Order {ERPWorkOrderID} not found!"), frappe.DoesNotExistError)
	
	se_doc = make_stock_entry_wo(work_order_name, "Material Transfer for Manufacture", qty, return_doc=1)
	
	# overide items as request
	se_doc.items = []
	se_doc.from_warehouse = source_warehouse
	for d in items:
		d = frappe._dict(d)
		row = se_doc.append("items")
		row.item_code = get_item_foms(d.rawMaterialId, d.rawMaterialRefNo)
		row.batch_no = d.rawMaterialBatchRefNo
		row.qty = d.qtyReserve
		row.uom = get_uom(d.uom)

	se_doc.save()
	se_doc.submit()

	return {
		"ERPStockEntry":se_doc.name
	}

# Create Material Request 
@frappe.whitelist()
def create_material_request(
		transactionDate,
		requiredBy,
		requestedBy,
		items=[],
		cancel=False,
	):

	# find draft
	doc_name = frappe.get_value("Material Request", {"requested_by":requestedBy, "workflow_state":"Draft"})
	if doc_name:
		doc = frappe.get_doc("Material Request", doc_name)
	else:
		# create material request
		doc = frappe.new_doc("Material Request")
		doc.transaction_date = getdate(transactionDate)
		doc.requiredBy = getdate(requiredBy)
		doc.requested_by = requestedBy

	for d in items:
		d = frappe._dict(d)
		row = doc.get("items", {"foms_request_id": cstr(d.id) })
		if row:
			row = row[0]
		else:
			row = doc.append("items")

		row.foms_request_id = d.id
		row.item_code = d.rawMaterialRefNo
		row.qty = d.qtyRequest
		row.uom = get_uom(d.uom)
	
	doc.flags.ignore_mandatory = 1
	doc.save()

	return {
		"materialRequestNo": doc.name
	}







# Call Raw Material Receipt (refer to GetPurchaseReceiptFromERP)

# Create Raw Material Return (Purchase Receiot return)