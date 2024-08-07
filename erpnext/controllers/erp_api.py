import frappe, json
from six import string_types
from frappe.utils import flt, now_datetime, cint, getdate, cstr
from erpnext.controllers.foms import (
    create_bom_products, 
    get_bom_for_work_order, 
	get_foms_settings,
	create_work_order as _create_work_order,
	OPERATION_MAP_NAME,
	get_raw_item_foms,
	get_uom,
	create_raw_material as _create_raw_material,
	create_products as _create_products,
	create_delivery_order as _create_delivery_order,
	get_operation_map_name,
	create_finish_goods_stock as _create_finish_goods_stock,
	create_packaging, update_so_working
)
from frappe import _
from erpnext.manufacturing.doctype.job_card.job_card import make_stock_entry as make_stock_entry_jc, make_time_log
from erpnext.manufacturing.doctype.work_order.work_order import make_stock_entry as make_stock_entry_wo
from erpnext.stock.doctype.purchase_receipt.purchase_receipt import make_purchase_return
from frappe.model.workflow import apply_workflow
from erpnext.stock.doctype.stock_entry.stock_entry_utils import make_stock_entry


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
def create_work_order(FomsWorkOrderID, FomsLotID, productID, SalesOrderNo, qty, uom, submit=False):
	submit = get_foms_settings("auto_submit_work_order") or submit
	item_code = frappe.get_value("Item", {"foms_product_id":productID})
	if not item_code or productID==0:
		frappe.throw(_(f"Missing Item with Product ID {productID}"), frappe.DoesNotExistError)

	bom_no = get_bom_for_work_order(item_code)
	if not bom_no:
		frappe.throw(_(f"Missing BOM for {item_code}"), frappe.DoesNotExistError)
		
	qty = flt(qty) or 1
	log = frappe._dict({
		"workOrderNo":FomsWorkOrderID,
		"lotId":FomsLotID,
		"sales_order_no":SalesOrderNo
	})
	doc = _create_work_order(log, item_code, bom_no, qty, submit, return_doc=1)
	seeding_jc = frappe.get_value("Job Card", {"work_order":doc.name, "status":"Open", "operation":OPERATION_MAP_NAME.get(1)})
	transplanting_jc = frappe.get_value("Job Card", {"work_order":doc.name, "status":"Open", "operation":OPERATION_MAP_NAME.get(2)})
	harvesting_jc = frappe.get_value("Job Card", {"work_order":doc.name, "status":"Open", "operation":OPERATION_MAP_NAME.get(3)})
	res = {
		"ERPWorkOrderID":doc.name,
		"ERPBOMId":doc.bom_no
	}

	return res

@frappe.whitelist()
def start_work_order(ERPWorkOrderID):
	work_order_name = frappe.db.get_value("Work Order", ERPWorkOrderID)

	if not work_order_name:
		frappe.throw(_(f"Work Order {ERPWorkOrderID} not found!"), frappe.DoesNotExistError)

	doc = frappe.get_doc("Work Order", work_order_name)

	transfer_material = doc.qty - doc.material_transferred_for_manufacturing
	if transfer_material:
		se_doc = make_stock_entry_wo(doc.name, 'Material Transfer for Manufacture', transfer_material)
		se_doc.submit()	

@frappe.whitelist()
def update_work_order_operation_status(ERPWorkOrderID, operationNo, percentage=0):
	operationName = OPERATION_MAP_NAME.get( cint(operationNo) )
	work_order_name, transfer_material = frappe.db.get_value("Work Order", ERPWorkOrderID, ['name', 'material_transferred_for_manufacturing']) or ("", 0)
	
	if not transfer_material:
		frappe.throw(_(f"Raw Material reserve not found for Work Order {ERPWorkOrderID}, please make Material Reserve first!"), frappe.ValidationError)
	
	operation_name = frappe.db.get_value("Job Card", {
		"work_order":work_order_name,
		"operation": operationName,
		"docstatus":0
	})

	if not operation_name:
		frappe.throw(_(f"Missing Operation {operationName} for Work Order {ERPWorkOrderID}"), frappe.DoesNotExistError)
	
	transferred_qty, job_card_name = frappe.db.get_value("Job Card", operation_name, ["transferred_qty", "name"]) or (0, "")

	# temporary stock entry is created based on work order (stright flow)
	if not transferred_qty and not transfer_material:
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


	return {
		"result": True,
		"percentage": percentage
	}

@frappe.whitelist()
def submit_work_order_finish_goods(ERPWorkOrderID, qty):
	work_order_name, so_sub_id, lot_id = frappe.db.get_value("Work Order", ERPWorkOrderID, ['name', 'sub_sales_order', 'foms_lot_id']) or ("", "", "")

	if not work_order_name:
		frappe.throw(_(f"Work Order {ERPWorkOrderID} not found!"), frappe.DoesNotExistError)
	
	
	se_doc = make_stock_entry_wo(work_order_name,"Manufacture", qty, return_doc=1)
	se_doc.save()
	se_doc.submit()

	update_so_working(so_sub_id, lot_id)

	return {
		"ERPStockEntry":se_doc.name
	}

# Create Material Reserve
@frappe.whitelist()
def create_raw_material_reserve(ERPWorkOrderID, items):
	work_order_name, qty, source_warehouse = frappe.get_value("Work Order", ERPWorkOrderID, ["name", "qty", "source_warehouse"]) or ("", 1, "")
	if not work_order_name:
		frappe.throw(_(f"Work Order {ERPWorkOrderID} not found!"), frappe.DoesNotExistError)
	
	se_doc = make_stock_entry_wo(work_order_name, "Material Transfer for Manufacture", qty, return_doc=1)
	
	# overide items as request
	se_doc.items = []
	se_doc.from_warehouse = source_warehouse
	for d in items:
		d = frappe._dict(d)
		item_code = get_raw_item_foms(d.rawMaterialId, d.rawMaterialRefNo)
		if not item_code:
			continue

		is_stock_item = frappe.get_value("Item", item_code, "is_stock_item")
		if not is_stock_item:
			continue
		
		row = se_doc.append("items")
		src_warehouse = frappe.get_value("Warehouse", {"foms_id":d.sourceWarehouseId})
		row.s_warehouse = src_warehouse or source_warehouse
		row.item_code = item_code
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
	print(204)
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
		row.schedule_date = getdate(d.requestDate)
	
	doc.flags.ignore_mandatory = 1
	doc.save()

	# apply_workflow(doc, "Submit")

	return {
		"materialRequestNo": doc.name
	}

# Create Material Request 
@frappe.whitelist()
def create_material_return(data):
	# create purchase receipt return
	data = frappe._dict(data)
	return_against = frappe.db.get_value("Purchase Receipt", data.return_against)
	if not return_against:
		frappe.throw(_(f"Purchase receipt {data.return_against} not found"), frappe.DoesNotExistError)

	doc = frappe.get_doc(make_purchase_return(return_against))

	select_items = []
	for d in data.get("items") or []:
		d = frappe._dict(d)
		
		item = None
		for row in doc.get("items"):
			if row.item_code == d.item_code and row.uom == get_uom(d.uom) and cstr(d.batch_no)==cstr(row.batch_no):
				item = row
				break

		if item:
			select_items.append(item)
			item.qty = flt(d.return_qty) * -1
			item.received_qty = item.qty

		if not item:
			frappe.throw(_(f"Selected item is not found ({d.item_code})"))
	
	for row in doc.get("items"):
		if row not in select_items:
			doc.remove(row)

	doc.save()

	return {
		"purchaseReturnNo":doc.name
	}
	
@frappe.whitelist()
def create_update_packaging(data):
	data = frappe._dict(data)
	item = frappe.get_value("Item", data.itemCode)
	if not item:
		frappe.throw(_(f"Missing Item with ID {data.itemCode}"))
	doc = frappe.get_doc("Item", item)
	pack_name = create_packaging(data)
	row = doc.get("packaging", {"packaging":data.packageName})
	if not row:
		row = doc.append("packaging")
		row.packaging = pack_name
		doc.save()

	return {
		"PackageID":pack_name
	}


@frappe.whitelist()
def create_raw_material(data):
	res = _create_raw_material(data)
	
	return {
		"rawMaterialNo":res
	}

@frappe.whitelist()
def create_product(data):
	res = _create_products(data)
	return {
		"ProductNo":res
	}

@frappe.whitelist()
def create_delivery_order(data):
	res = _create_delivery_order(data)
	return {
		"DeliveryOrderNo":res
	}

@frappe.whitelist()
def create_stock_issue(data):
	return _create_stock_entry(data)

def _create_stock_entry(data):
	data = frappe._dict(data)
	args = data
	if not args.purpose:
		args.purpose = "Material Issue"
	args.do_not_save = 1
	args.do_not_submit = 1
	for d in args.get("items"):
		d = frappe._dict(d)
		args.qty = d.qty
		args.item = d.item
		args.uom = d.uom
		args.serial_no = d.serial_no
		args.batch_no = d.batch_no
		args.rate = d.rate
		break
	
	doc = make_stock_entry(**args)
	doc.work_order = args.work_order
	doc.job_card = args.job_card
	if not args.cost_center:
		args.cost_center = frappe.get_value("Company", args.company, "cost_center")
	
	if not args.expense_account and args.is_opening == "No":
		args.expense_account = frappe.get_value("Company", args.company, "stock_adjustment_account")

	idx = 0
	if len(args.get("items")) > 1:
		for d in args.get("items"):
			idx += 1
			if idx == 1:
				continue

			d = frappe._dict(d)
			row = doc.append("items")
			row.update({
				"item_code": d.item,
				"s_warehouse": args.source,
				"t_warehouse": args.target,
				"qty": d.qty,
				"basic_rate": d.rate or d.basic_rate,
				"conversion_factor": d.conversion_factor or 1.0,
				"transfer_qty": flt(d.qty) * (flt(d.conversion_factor) or 1.0),
				"serial_no": d.serial_no,
				"batch_no": d.batch_no,
				"cost_center": args.cost_center,
				"expense_account": d.expense_account,
			})

	doc.save()

	return {
		"StockEntryNo":doc.name
	}

@frappe.whitelist()
def remove_expired_stock(data):
	data = frappe._dict(data)
	# mandatory batch no
	for d in data.get("items"):
		if not d.batch_no:
			frappe.throw(_(f"Missing batch no for item {d.item}"), frappe.DoesNotExistError)

	_create_stock_entry(data)

@frappe.whitelist()
def create_material_consume(data):
	data = frappe._dict(data)
	# mandatory batch no
	if not data.work_order:
		frappe.throw(_(f"Work Order must be set!"), frappe.DoesNotExistError)
	if not data.operation_no:
		frappe.throw(_(f"Operation No must be set!"), frappe.DoesNotExistError)
	
	work_order = frappe.get_value("Work Order", data.work_order)
	if not work_order:
		frappe.throw(_(f"Work Order {data.work_order} is not exists"), frappe.DoesNotExistError)

	operation_name = get_operation_map_name(cint(data.operation_no))
	job_card = frappe.get_value("Job Card", {"operation":operation_name, "work_order":work_order})

	result = None
	if not job_card:
		frappe.msgprint("Job Card did not exists")
	else:
		data.purpose = "Material Transfer for Manufacture"
		data.job_card = job_card
		_create_stock_entry(data)

	
	return {
		"StockEntryNo":result
	}

from erpnext.buying.doctype.request.request import create_request_form as _create_request_form, update_request
@frappe.whitelist()
def create_request_form(data):
	"""
		data = {
			"department": "",
			"postingDate":"",
			"deliveryDate":"",
			"FOMSOrderID:"",
			"items":[
				{
					"itemCode":"",
					"qty":1,
					"uom":"",
					"packaging":"",
					"rate":"",
					"unitUOM":"",
					"unitWeight":1,
					"weight":1
				}
			]
		}	
	"""
	data = frappe._dict(data)
	result = _create_request_form(data)
	return {
		"RequestNo": result
	}

@frappe.whitelist()
def create_finish_goods_stock(data):
	return _create_finish_goods_stock(data)

@frappe.whitelist()
def update_request_data(data):
	return update_request(data.get("request_no"), data.get("items"), data.get("delivery_date"))