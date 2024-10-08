import frappe, json
from six import string_types
from frappe.utils import flt, now_datetime, cint, getdate, cstr, get_datetime
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
	create_packaging, update_so_working, create_do_based_on_work_order
)
from frappe import _
from erpnext.manufacturing.doctype.job_card.job_card import make_stock_entry as make_stock_entry_jc, make_time_log
from erpnext.manufacturing.doctype.work_order.work_order import make_stock_entry as make_stock_entry_wo, create_job_card
from erpnext.stock.doctype.purchase_receipt.purchase_receipt import make_purchase_return
from frappe.model.workflow import apply_workflow
from erpnext.stock.doctype.batch.batch import get_batch_no
from erpnext.stock.doctype.stock_entry.stock_entry_utils import make_stock_entry
from frappe.utils.file_manager import save_file, save_url
from erpnext.foms.doctype.foms_data_mapping.foms_data_mapping import create_foms_data, update_data_result

def get_data(data):
	if isinstance(data, string_types):
		data = json.loads(data)
	data = frappe._dict(data)

	return data

def save_log(doctype, data_name, raw_data):
	frappe.enqueue("erpnext.foms.doctype.foms_data_mapping.foms_data_mapping.create_foms_data",
		data_type=doctype, 
		data_name=data_name,
		raw=raw_data,
	)

def update_log(doctype, data_name, result):
	frappe.enqueue("erpnext.foms.doctype.foms_data_mapping.foms_data_mapping.update_data_result",
		data_type=doctype, 
		data_name=data_name,
		result_name=result,
	)

@frappe.whitelist()
def ping_data(data):
	print(data)
	data = get_data(data)
	if data.create_log == 1:
		save_log("TEST", "test", data)
		update_log("TEST", "test", "oke")

	return data

@frappe.whitelist()
def create_bom(data):
	data = get_data(data)
		
	product_id = data.get("productID")
	submit = get_foms_settings("auto_submit_bom")

	item = frappe.get_value("Item", {"foms_product_id":product_id})
	version = data.get("productVersionName")
	data_name = f"BOM {item} {version}"
	save_log("BOM", data_name, data)
	result = create_bom_products(data, product_id, submit=submit)
	update_log("BOM", data_name, result)
	
	return {"ERPBomId":result}

@frappe.whitelist()
def create_work_order(FomsWorkOrderID, FomsLotID, productID, SalesOrderNo, qty, gross_weight, uom, submit=False):
	data_name = f"Work Order {FomsLotID}"
	save_log("Work Order", data_name, {
		"FomsWorkOrderID":FomsWorkOrderID, 
		"FomsLotID":FomsLotID, 
		"productID":productID, 
		"SalesOrderNo":SalesOrderNo, 
		"qty":qty, 
		"uom":uom, 
		"submit":submit
	})

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

	doc = _create_work_order(log, item_code, bom_no, qty, gross_weight, submit, return_doc=1)
	# seeding_jc = frappe.get_value("Job Card", {"work_order":doc.name, "status":"Open", "operation":OPERATION_MAP_NAME.get(1)})
	# transplanting_jc = frappe.get_value("Job Card", {"work_order":doc.name, "status":"Open", "operation":OPERATION_MAP_NAME.get(2)})
	# harvesting_jc = frappe.get_value("Job Card", {"work_order":doc.name, "status":"Open", "operation":OPERATION_MAP_NAME.get(3)})
	
	res = {
		"ERPWorkOrderID":doc.name,
		"ERPBOMId":doc.bom_no
	}

	update_log("Work Order", data_name, doc.name)

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

def get_item_overide():
	settings = frappe.get_doc("FOMS Integration Settings")
	overide_map = {}
	for d in settings.get("item_conversion"):
		if cint(d.enable):
			overide_map[d.from_item] = {
				"cf":d.conversion_factor,
				"item":d.to_item,
				"uom":d.from_uom
			}
	return overide_map

def get_uom_overide(reverse=False):
	settings = frappe.get_doc("FOMS Integration Settings")
	overide_map = {}
	for d in settings.get("uom_conversion"):
		if cint(d.enable):
			if not reverse:
				overide_map[(d.item_code, d.from_uom)] = {
					"cf":d.conversion_factor,
					"uom":d.to_uom
				}
			else:
				cf = 1/ flt(d.conversion_factor)
				overide_map[(d.item_code, d.to_uom)] = {
					"cf": cf,
					"uom":d.from_uom
				}
	return overide_map


def make_stock_entry_with_materials(source_name, materials, wip_warehouse, operation_name, work_order_name):
	se = make_stock_entry_jc(source_name)
	se.items = []
	missing_warehouse = []

	overide_item = get_item_overide()

	for d in materials:
		d = frappe._dict(d)
		row = se.append("items")
		warehouse = frappe.get_value("Warehouse", {"foms_id": cint(d.sourceWarehouseId)}, debug=0)
		if not warehouse:
			missing_warehouse.append(d.sourceWarehouseRefNo)
		item_code = frappe.get_value("Item", {"foms_raw_id": cstr(d.rawMaterialId)}) or d.rawMaterialRefNo
		row.s_warehouse = warehouse
		row.t_warehouse = wip_warehouse
		uom = get_uom(d.uom)
		qty = flt(d.qty)
		batch_no = d.rawMaterialBatchRefNo

		# Overide Item
		qty_conversion = 1
		is_overide_item = False
		original_item = None
		if item_code in overide_item:
			is_overide_item = True
			# qty_conversion = overide_item[item_code]['cf']
			uom = overide_item[item_code]['uom']
			original_item = cstr(item_code)
			item_code = overide_item[item_code]['item']

		qty = qty * qty_conversion
		if uom in ['Unit']:
			qty = round(qty)

		qty = flt(qty, 7)
		
		if is_overide_item:
			# get batch automaticly
			row.original_item = original_item
			batch_no = get_batch_no(item_code, warehouse, qty)

		row.item_code = item_code
		row.qty = qty
		row.uom = uom
		row.batch_no = batch_no
	
	if missing_warehouse:
		warn = ", ".join(list(set(missing_warehouse)))
		frappe.throw(f"Warehouse not found: {warn}")
	
	# additional cost
	expense_account = frappe.db.get_single_value("Manufacturing Settings", "default_expense_account")
	if not expense_account:
		frappe.throw(_("Please set Default Expense Account in Manufacturing Settings"))
	
	wo_doc = frappe.get_doc("Work Order", work_order_name)
	se.wip_additional_costs = []
	cost_ref = wo_doc.get("operations", {"operation":operation_name})
	cost_fields = ['electrical_cost', 'consumable_cost', 'machinery_cost', 'wages_cost', 'rent_cost']
	descriptions = {
		'electrical_cost':"Electrical Cost", 
		'consumable_cost':"Consumable Cost", 
		'machinery_cost': "Machinery Cost", 
		'wages_cost': 'Wages Cost', 
		'rent_cost': "Rent Cost"
	}
	if cost_ref:
		# currently cost calculation is takne from gross weight from Work Order
		gross_weight = flt(wo_doc.gross_weight)
		cost_ref = cost_ref[0]
		for field in cost_fields:
			amount = cost_ref.get(field)
			if amount:
				row = se.append("wip_additional_costs")
				row.expense_account = expense_account
				row.amount = amount * gross_weight
				row.description = descriptions[field]
	return se

def get_stock_entry_type(operation):
	if operation == "Seeding":
		return "Seeding Transfer"
	elif operation == "Transplanting":
		return "Transplanting Transfer"
	else:
		return "Harvesting Finished Goods"



@frappe.whitelist()
def update_work_order_operation_status(operationNo, percentage=0, rawMaterials=[], ERPWorkOrderID="", erpWorkOrderID=""):
	ERPWorkOrderID = ERPWorkOrderID or erpWorkOrderID
	data_name = f"Operation {operationNo} Work Order {ERPWorkOrderID}"
	save_log("Work Order", data_name, {
		"ERPWorkOrderID":ERPWorkOrderID, 
		"operationNo":operationNo, 
		"percentage":percentage, 
		"rawMaterials":rawMaterials, 
	})
	operationName = OPERATION_MAP_NAME.get( cint(operationNo) )
	work_order_name = frappe.db.get_value("Work Order", ERPWorkOrderID)
	if not work_order_name:
		frappe.throw(_(f"Missing Work Order no {ERPWorkOrderID}"))
		
	temp = frappe.db.get_value("Job Card", {
		"work_order":work_order_name,
		"operation": operationName,
		"docstatus":["!=", 2]
	}, ['name', 'docstatus'], as_dict=1) or {}

	operation_name = temp.get("name")

	if temp.get("docstatus") == 1:
		return {
			"result": False,
			"percentage": percentage,
			"message": "Already updated"
		}

	if not operation_name:
		# create
		wo_doc = frappe.get_doc("Work Order", work_order_name)
		for d in wo_doc.operations:
			if d.operation == operationName:
				row = d.as_dict()
				row.job_card_qty = wo_doc.qty
				jc_doc = create_job_card(wo_doc, row, False, True)
				operation_name = jc_doc.name
	
	job_card_name = frappe.db.get_value("Job Card", operation_name)

	wip_warehouse = frappe.get_value("Job Card", job_card_name, "wip_warehouse")

	# create stock entry
	if rawMaterials:
		se_doc = make_stock_entry_with_materials(job_card_name, rawMaterials, wip_warehouse, operationName, work_order_name)
		se_doc.stock_entry_type_view = get_stock_entry_type(operationName)
		se_doc.insert(ignore_permissions=1)
		# for d in se_doc.items:
		# 	print(311, d.item_code, d.original_item, d.qty,d.transfer_qty, d.conversion_factor, d.uom, d.stock_uom)
		se_doc.submit()

	job_card = frappe.get_doc("Job Card", job_card_name)

	# start job card
	if not job_card.job_started:
		employee = frappe.get_value("Employee")
		args = frappe._dict({
			"job_card_id": job_card.name,
			"start_time": now_datetime()
		})
		job_card.validate_sequence_id()
		job_card.add_time_log(args)
		job_card.started_time = now_datetime()
		job_card.job_started = 1

	if percentage > 0 and percentage < 100:
		job_card.percentage = percentage
		job_card.save()
	elif percentage == 100:
		args = frappe._dict({
			"job_card_id": job_card.name,
			"complete_time": now_datetime(),
			"completed_qty": job_card.for_quantity # temporary like job card settings
		})
		job_card.validate_sequence_id()
		job_card.add_time_log(args)
		job_card.save()
		job_card.submit()
	else:
		job_card.save()

	frappe.db.commit()

	update_log("Work Order", data_name, job_card_name)

	return {
		"result": True,
		"percentage": percentage
	}

@frappe.whitelist()
def submit_work_order_finish_goods(ERPWorkOrderID, qty, expiryDate=""):
	data_name = f"Finish Work Order {ERPWorkOrderID}"
	save_log("Work Order", data_name, {
		"ERPWorkOrderID":ERPWorkOrderID, 
		"qty":qty
	})
	work_order_name, lot_id = frappe.db.get_value("Work Order", ERPWorkOrderID, ['name', 'foms_lot_id']) or ("", "", "")

	if not work_order_name:
		frappe.throw(_(f"Work Order {ERPWorkOrderID} not found!"), frappe.DoesNotExistError)
	
	
	se_doc = make_stock_entry_wo(work_order_name,"Manufacture", qty, return_doc=1)
	se_doc.stock_entry_type_view = get_stock_entry_type("Harvesting")
	
	se_doc.save()
	se_doc.submit()

	# debug
	for d in se_doc.items:
		if d.is_finished_item and expiryDate:
			frappe.db.set_value("Batch", d.batch_no, "expiry_date", getdate(expiryDate))

	for d in se_doc.get("items"):
		if d.is_finished_item:
			create_do_based_on_work_order(se_doc.work_order, d.qty, d.t_warehouse, d.batch_no)

	# update_so_working(so_sub_id, lot_id)
	update_log("Work Order", data_name, work_order_name)
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
	item_str = ", ".join([d.get("rawMaterialRefNo") for d in items])
	data_name = f"Create Material Request {item_str}"
	save_log("Material Request", data_name, {
		"transactionDate":transactionDate, 
		"requiredBy":requiredBy, 
		"requestedBy":requestedBy, 
		"items":items, 
		"cancel":cancel, 
	})
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

	overide_map = get_item_overide()

	for d in items:
		d = frappe._dict(d)
		row = doc.get("items", {"foms_request_id": cstr(d.id) })
		if row:
			row = row[0]
		else:
			row = doc.append("items")

		item_code = d.rawMaterialRefNo
		qty = d.qtyRequest

		qty_conversion = 1
		overide_item = False
		if item_code in overide_map:
			overide_item = True
			qty_conversion = overide_map[item_code]['cf']
			item_code = overide_map[item_code]['item']

		row.foms_request_id = d.id
		row.item_code = item_code
		row.qty = qty * qty_conversion
		row.uom = get_uom(d.uom)
		row.schedule_date = getdate(d.requestDate)
	
	doc.flags.ignore_mandatory = 1
	doc.save()
	apply_workflow(doc, "Submit")

	update_log("Material Request", data_name, doc.name)

	return {
		"materialRequestNo": doc.name
	}

# Create Material Request 
@frappe.whitelist()
def create_material_return(data):
	# logger
	data = frappe._dict(data)
	data_name = f"Material Return {data.return_against}"
	save_log("Material Request", data_name, data)
	# create purchase receipt return
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

	update_log("Material Return", data_name, doc.name)

	return {
		"purchaseReturnNo":doc.name
	}
	
@frappe.whitelist()
def create_update_packaging(data):
	# logger
	data = frappe._dict(data)
	data_name = f"Packaging {data.packageName}"
	save_log("Packaging", data_name, data)

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

	update_log("Packaging", data_name, pack_name)

	return {
		"PackageID":pack_name
	}

@frappe.whitelist()
def update_delivery_note_signature(data):
	# logger
	"""
	doNumber:"",
	attachments: [base64image, base64image],
	signature:"base64image"
	"""
	data = frappe._dict(data)

	data_name = f"Update DO Signature {data.doNumber}"
	save_log("Delivery Note", data_name, data)

	do_number = frappe.get_value("Delivery Note", data.doNumber)
	if not do_number:
		frappe.throw(_(f"Missing Delivery Note with ID {data.doNumber}"))
	
	doc = frappe.get_doc("Delivery Note", data.doNumber)
	# convert base64 image from json to data

	for d in data.get("attachments") or []:
		file_name = d.get("filename")
		encoded_content = d.get("image")
		image_url = d.get("imageUrl")
		if not encoded_content and not image_url:
			frappe.throw(_("Attachment must have content value"))

		folder = "Home/Attachments"
		if encoded_content:
			# doc.db
			file_save = save_file(
				file_name,
				encoded_content,
				"Delivery Note",
				do_number,
				folder=folder,
				decode=True,
				is_private=1,
				df="attachment",
			)
			doc.db_set("attachment", file_save.file_url)
		else:
			file_save = save_url(
				image_url,
				file_name,
				"Delivery Note",
				do_number,
				folder,
				True,
				"attachment"
			)
			doc.db_set("attachment", file_save.file_url)		

	# signature
	if "image/png" not in data.signature:
		signature = "data:image/png;base64,"+cstr(data.signature)
	else:
		signature  = data.signature

	doc.db_set("signature", signature)
	doc.db_set("signature_by", data.signature_by)
	doc.db_set("delivery_completed_at", get_datetime(data.completed_at))
	doc.db_set("delivery_completed_by", data.completed_by)
	doc.db_set("taken_at", get_datetime(data.taken_at))

	update_log("Delivery Note", data_name, doc.name)

	return True


@frappe.whitelist()
def create_raw_material(data):
	data = frappe._dict(data)
	# logger
	name = data.get("rawMaterialRefNo")
	data_name = f"Create Raw Material {name}"
	save_log("Raw Material", data_name, data)

	res = _create_raw_material(data)

	update_log("Raw Material", data_name, res)
	
	return {
		"rawMaterialNo":res
	}

@frappe.whitelist()
def create_product(data):
	# logger
	res = _create_products(data)
	return {
		"ProductNo":res
	}

@frappe.whitelist()
def create_delivery_order(data):
	# logger
	res = _create_delivery_order(data)
	return {
		"DeliveryOrderNo":res
	}

@frappe.whitelist()
def create_stock_issue(data):
	# logger
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
	# logger
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

@frappe.whitelist(methods='DELETE')
def delete_item(itemCode):
	from frappe.model.delete_doc import check_if_doc_is_linked
	item_code_name = frappe.db.exists("Item", {"item_code":itemCode})
	if not item_code_name:
		return True
	
	doc = frappe.get_doc("Item", item_code_name)
	doc.flags.allow_delete = True

	if check_if_doc_is_linked(doc, "Delete", True):
		doc.delete()
		return True
	else:
		doc.db_set("disabled", 1)
		return False
