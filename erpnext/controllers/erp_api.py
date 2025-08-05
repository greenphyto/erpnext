import frappe, json, erpnext
from six import string_types
from frappe.utils import flt, now_datetime, cint, getdate, cstr, get_datetime, add_days
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
	create_packaging, update_so_working, create_do_based_on_work_order,
	get_cost_center, get_default_expense_production_account, 
	get_previous_operation
)
from frappe import _
from erpnext.manufacturing.doctype.job_card.job_card import make_stock_entry as make_stock_entry_jc, make_time_log
from erpnext.manufacturing.doctype.work_order.work_order import make_stock_entry as make_stock_entry_wo, create_job_card
from erpnext.stock.doctype.purchase_receipt.purchase_receipt import make_purchase_return
from frappe.model.workflow import apply_workflow
from erpnext.stock.doctype.batch.batch import get_batch_no, get_available_batch
from erpnext.stock.doctype.stock_entry.stock_entry_utils import make_stock_entry
from frappe.utils.file_manager import save_file, save_url
from erpnext.foms.doctype.foms_data_mapping.foms_data_mapping import create_foms_data, update_data_result, make_in_progress
from datetime import datetime, timedelta

PRECISION_FACTOR = 4

def get_data(data):
	if isinstance(data, string_types):
		data = json.loads(data)
	data = frappe._dict(data)

	return data

def save_log(doctype, data_name, raw_data, reopen=False, now=False):
	return frappe.enqueue("erpnext.foms.doctype.foms_data_mapping.foms_data_mapping.create_foms_data",
		data_type=doctype, 
		data_name=data_name,
		raw=raw_data,
		reopen=reopen,
		now=now,
	)

def update_log(doctype, data_name, result_doctype, result, now=False, name_id=None):
	if now:
		update_data_result(
			data_type=doctype, 
			data_name=data_name,
			result_name=result,
			result_doctype=result_doctype,
			name_id=name_id
		)
	else:
		return frappe.enqueue("erpnext.foms.doctype.foms_data_mapping.foms_data_mapping.update_data_result",
			data_type=doctype, 
			data_name=data_name,
			result_name=result,
			result_doctype=result_doctype,
			name_id=name_id
		)

@frappe.whitelist()
def ping_data(data):
	print(data)
	data = get_data(data)
	if data.create_log == 1:
		save_log("TEST", "test", data)
		update_log("TEST", "test", "DOC TEST", "oke")

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
	update_log("BOM", data_name, "BOM", result)
	return {"ERPBomId":result}

@frappe.whitelist()
def create_work_order(fomsWorkOrderID, fomsLotID, productID, salesOrderNo, qty, gross_weight, uom, submit=False):

	data_name = f"Work Order {fomsLotID}"
	save_log("Work Order", data_name, {
		"fomsWorkOrderID":fomsWorkOrderID, 
		"fomsLotID":fomsLotID, 
		"productID":productID, 
		"salesOrderNo":salesOrderNo, 
		"qty":qty, 
		"uom":uom, 
		"gross_weight":gross_weight,
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
		"workOrderNo":fomsWorkOrderID,
		"lotId":fomsLotID,
		"sales_order_no":salesOrderNo
	})

	doc = _create_work_order(log, item_code, bom_no, qty, gross_weight, submit, return_doc=1, args={
		"use_rate_from_bom":1
	})
	# seeding_jc = frappe.get_value("Job Card", {"work_order":doc.name, "status":"Open", "operation":OPERATION_MAP_NAME.get(1)})
	# transplanting_jc = frappe.get_value("Job Card", {"work_order":doc.name, "status":"Open", "operation":OPERATION_MAP_NAME.get(2)})
	# harvesting_jc = frappe.get_value("Job Card", {"work_order":doc.name, "status":"Open", "operation":OPERATION_MAP_NAME.get(3)})
	
	res = {
		"ERPWorkOrderID":doc.name,
		"ERPBOMId":doc.bom_no
	}

	update_log("Work Order", data_name, "Work Order", doc.name)

	return res

@frappe.whitelist()
def start_work_order(erpWorkOrderID="", ERPWorkOrderID=""):
	erpWorkOrderID = erpWorkOrderID or ERPWorkOrderID
	work_order_name = frappe.db.get_value("Work Order", erpWorkOrderID)

	if not work_order_name:
		frappe.throw(_(f"Work Order {erpWorkOrderID} not found!"), frappe.DoesNotExistError)

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


def make_stock_entry_with_materials(wo_doc, job_card_name, materials, wip_warehouse, operation_name, percentage=100, cur_percent=100, global_percent=100, company=""):
	missing_warehouses = []
	override_items = get_item_overide()
	company = company or erpnext.get_default_company()
	cost_center = get_cost_center(operation_name, company)

	# Create stock entry
	se = make_stock_entry_jc(job_card_name)
	se.stock_entry_type_view = get_stock_entry_type(operation_name)
	se.items = []
	se.fg_completed_qty = wo_doc.qty * flt(cur_percent)/100

	# Load BOM for item costing
	bom = frappe.get_doc("BOM", se.bom_no)

	for d in materials:
		d = frappe._dict(d)
		source_warehouse = frappe.get_value("Warehouse", {"foms_id": cint(d.sourceWarehouseId)}, debug=0)
		if not source_warehouse:
			missing_warehouses.append(d.sourceWarehouseRefNo)
			continue

		item_code = frappe.get_value("Item", {"foms_raw_id": cstr(d.rawMaterialId)}) or d.rawMaterialRefNo
		uom = get_uom(d.uom)
		qty = flt(d.qty)

		# Handle override item
		is_override = False
		original_item = None
		if item_code in override_items:
			is_override = True
			override = override_items[item_code]
			uom = override['uom']
			original_item = item_code
			item_code = override['item']
			qty = qty  # can apply conversion rate here if needed

		# Round qty if needed
		if uom == 'Unit':
			qty = round(qty)
		qty = flt(qty, PRECISION_FACTOR, floor=True)

		# Auto get batch for override items
		batch_no = d.rawMaterialBatchRefNo
		if is_override:
			batch_no = get_batch_no(item_code, source_warehouse, qty)

		# Add item row to stock entry
		row = se.append("items")
		row.item_code = item_code
		row.original_item = original_item if is_override else None
		row.s_warehouse = source_warehouse
		row.t_warehouse = wip_warehouse
		row.qty = qty
		row.uom = uom
		row.batch_no = batch_no
		row.cost_center = cost_center
		row.set_basic_rate_manually = 1

		# Fetch rate from BOM
		row.basic_rate = 0
		for m in bom.get("items"):
			if (m.item_code == item_code or m.item_code == original_item) and m.operation == operation_name:
				row.basic_rate = m.rate
				break

	# Add packaging items if operation is Harvesting
	if se.operation == "Harvesting":
		packaging_cost_center = frappe.get_value("Company", se.company, "cost_center_for_packing")
		for d in wo_doc.required_items:
			if not d.is_packaging:
				continue

			# Find batch with required qty
			batch_info = get_available_batch(d.item_code, d.required_qty)
			if not batch_info:
				continue  # skip if not available

			pack_row = se.append("items")
			pack_row.item_code = d.item_code
			pack_row.s_warehouse = batch_info[0].get("warehouse")
			pack_row.batch_no = batch_info[0].get("batch_id")
			pack_row.t_warehouse = wip_warehouse
			pack_row.cost_center = packaging_cost_center
			pack_row.qty = d.required_qty * global_percent/100
			pack_row.uom = d.uom
			pack_row.basic_rate = d.rate
			pack_row.set_basic_rate_manually = 1

	# Raise error if any warehouse not found
	if missing_warehouses:
		frappe.throw(f"Warehouse not found: {', '.join(set(missing_warehouses))}")

	# Add additional cost (electricity, wages, etc.)
	se.additional_costs = []
	expense_account = get_default_expense_production_account(company)
	cost_fields = ['electrical_cost', 'consumable_cost', 'machinery_cost', 'wages_cost', 'rent_cost']
	descriptions = {
		'electrical_cost': "Electrical Cost",
		'consumable_cost': "Consumable Cost",
		'machinery_cost': "Machinery Cost",
		'wages_cost': "Wages Cost",
		'rent_cost': "Rent Cost"
	}

	operation_costs = wo_doc.get("operations", {"operation": operation_name})
	if operation_costs:
		op_cost = operation_costs[0]
		gross_weight = flt(wo_doc.gross_weight)

		for field in cost_fields:
			amount = op_cost.get(field)
			if amount:
				cost_row = se.append("additional_costs")
				cost_row.expense_account = expense_account
				cost_row.amount = amount * gross_weight
				cost_row.cost_center = frappe.get_value("Company", company, "cost_center_for_packing")
				cost_row.description = descriptions[field]

	se.set_expense_account()
	return se


def get_stock_entry_type(operation):
	if operation == "Seeding":
		return "Seeding Transfer"
	elif operation == "Transplanting":
		return "Transplanting Transfer"
	elif operation == "Harvesting":
		return "Harvesting Transfer"
	else:
		return "Harvesting Finished Goods"

@frappe.whitelist()
def update_work_order_operation_status(operationNo, percentage=0, rawMaterials=[], ERPWorkOrderID="", erpWorkOrderID="", now=False):
	ERPWorkOrderID = ERPWorkOrderID or erpWorkOrderID
	data_name = f"Operation {operationNo} Work Order {ERPWorkOrderID}"
	log_res = save_log("Work Order", data_name, {
		"ERPWorkOrderID":ERPWorkOrderID, 
		"operationNo":operationNo, 
		"percentage":percentage, 
		"rawMaterials":rawMaterials, 
		"now":now
	}, now=1)

	if log_res.status != "Unknown":
		return
	
	if cint(get_foms_settings("disable_woirk_order_operation_update")):
		return {
			"result": False,
			"percentage": 0,
			"message":"Temporary disabled"
		}
	
	data_name = f"Operation {operationNo} Work Order {ERPWorkOrderID}"
	operationName = OPERATION_MAP_NAME.get( cint(operationNo) )
	work_order_name = frappe.db.get_value("Work Order", ERPWorkOrderID)
	if not work_order_name:
		frappe.throw(_(f"Missing Work Order no {ERPWorkOrderID}"))
		
	temp = frappe.db.get_value("Job Card", {
		"work_order":work_order_name,
		"operation": operationName,
		"docstatus":["!=", 2]
	}, ['name', 'docstatus'], cache=False , as_dict=1) or {}

	job_card_name = temp.get("name")

	if temp.get("docstatus") == 1:
		update_log("Work Order", data_name, "Job Card", temp.get("name"))
		return {
			"result": False,
			"percentage": percentage,
			"message": "Already updated"
		}
	
	wip_warehouse = frappe.get_value("Job Card", job_card_name, "wip_warehouse")

	# create stock entry
	if job_card_name and frappe.db.get_value("Stock Entry", {"job_card": job_card_name, "docstatus":1}, cache=False, debug=0):
		update_log("Work Order", data_name, "Job Card", temp.get("name"))
		return {
			"result": False,
			"percentage": percentage,
			"message": "Already updated (se)"
		}

	if cint(operationNo) == 3 and not now:
		return {
			"result":"Scheduled"
		}
	else:
		return _update_work_order_operation_status(log_res.name, ERPWorkOrderID, operationNo, percentage, rawMaterials)

from erpnext.manufacturing.doctype.work_order.work_order import close_work_order, make_scrap_materials
def _update_work_order_operation_status(log_name, ERPWorkOrderID, operationNo, percentage, rawMaterials):
	operationNo = cint(operationNo)
	operationName = OPERATION_MAP_NAME.get(operationNo)
	work_order_name = frappe.db.get_value("Work Order", ERPWorkOrderID)
	data_name = f"Operation {operationNo} Work Order {ERPWorkOrderID}"
	log = frappe.get_doc("FOMS Data Mapping", log_name)

	# Check if a job card has been created
	existing_jc = frappe.db.get_value("Job Card", {
		"work_order": work_order_name,
		"operation": operationName,
		"docstatus": 1
	}, ["name"], as_dict=1)

	if existing_jc:
		update_log("Work Order", data_name, "Job Card", existing_jc.name)
		return {
			"result": False,
			"percentage": percentage,
			"message": "Already updated (se)"
		}

	# Skip if the mapping status is not Unknown
	if log.status != "Unknown":
		return

	make_in_progress(log.name, commit=1)

	# Handle full cancellation (100% scrap)
	if percentage == 0:
		close_work_order(work_order=work_order_name, status="Closed")
		se = make_scrap_materials(work_order_name, 100)
		se.save()
		se.submit()
		update_log("Work Order", data_name, "Stock Entry", se.name)
		update_log("Work Order", f"Cancel Operation {operationNo} Work Order {ERPWorkOrderID}", "Stock Entry", se.name)
		return {
			"result": True,
			"percentage": percentage,
			"close": 1
		}

	# Get the work order document
	wo_doc = frappe.get_doc("Work Order", work_order_name)
	prev_qty = get_previous_qty(work_order_name, operationName)
	global_percent = prev_qty/wo_doc.qty * 100 * percentage/100

	# Create a job card
	for d in wo_doc.operations:
		if d.operation == operationName:
			operation_row = d.as_dict()
			operation_row.job_card_qty = wo_doc.qty
			job_card_doc = create_job_card(wo_doc, operation_row, False, True)
			break
	else:
		frappe.throw(f"Operation {operationName} not found in Work Order.")

	# Scrap material for the remainder (if <100%)
	if percentage < 100:
		scrap_doc = make_scrap_materials(work_order_name, percentage=(100 - percentage))
		scrap_doc.save()
		scrap_doc.submit()

	job_card_name = job_card_doc.name
	wip_warehouse = job_card_doc.wip_warehouse

	# Make stock entry according to percentage
	se_doc = make_stock_entry_with_materials(
		wo_doc, 
		job_card_name,
		rawMaterials,
		wip_warehouse,
		operationName,
		percentage=100,
		cur_percent=percentage,
		global_percent=global_percent
	)
	se_doc.save()
	se_doc.submit()

	# Start and complete job cards if necessary.
	job_card = frappe.get_doc("Job Card", job_card_name)
	job_card.for_quantity = wo_doc.qty * flt(global_percent)/100

	if not job_card.job_started:
		start_args = frappe._dict({
			"job_card_id": job_card.name,
			"start_time": now_datetime()
		})
		job_card.validate_sequence_id()
		job_card.add_time_log(start_args)
		job_card.started_time = now_datetime()
		job_card.job_started = 1

	complete_args = frappe._dict({
		"job_card_id": job_card.name,
		"complete_time": now_datetime(),
		"completed_qty": job_card.for_quantity
	})
	job_card.validate_sequence_id()
	job_card.add_time_log(complete_args)
	job_card.save()
	job_card.submit()

	update_log("Work Order", data_name, "Job Card", job_card.name, name_id=log_name)

	return {
		"result": True,
		"percentage": percentage
	}

def get_previous_qty(work_order, cur_operation):
	# get valid qty after do partially etc
	# if not any previous, so use WO qty itself
	prev_opr = get_previous_operation(cur_operation)
	temp = frappe.db.sql("""
		SELECT 
			se.purpose,
			SUM(se.fg_completed_qty) AS qty,
			wo.qty AS wo_qty,
			se.is_return,
			se.operation
		FROM
			`tabWork Order` wo
				LEFT JOIN
			`tabStock Entry` se ON se.work_order = wo.name
				AND se.docstatus = 1
				AND se.is_return = 0
				AND IFNULL(se.operation, '') = %s
				AND se.purpose = 'Material Transfer for Manufacture'
		WHERE
			wo.name = %s
	""",(prev_opr, work_order), as_dict=1)
	if temp:
		return temp[0].qty or temp[0].wo_qty
	else:
		return 0

def run_pending_harvesting_transfer():
	now_time = get_datetime()
	end_range = now_time - timedelta(minutes=5)

	for d in frappe.db.sql("select name,data_name, raw_data from `tabFOMS Data Mapping` where status = 'Unknown' and data_type = 'Work Order' and created_on < %s ", (end_range), as_dict=1):
		print(d)
		data = json.loads(d.raw_data)

		if not data.get('ERPWorkOrderID'):
			continue

		if "Operation 3" in d.data_name:
			_update_work_order_operation_status(
				log_name=d.name,
				ERPWorkOrderID=data.get('ERPWorkOrderID'), 
				operationNo=flt(data.get('operationNo')), 
				percentage=flt(data.get('percentage')), 
				rawMaterials=data.get('rawMaterials'),
			)

@frappe.whitelist()
def submit_work_order_finish_goods(erpWorkOrderID, packets=0, qty=0, expiryDate="", draft=False, now=False):
	data_name = f"Finish Work Order {erpWorkOrderID}"
	if not packets and not qty:
		frappe.throw("Number of Packets or Qty must be set")

	# overwrite expiry date +1 as FOMS still using when batch written to the date but erp expired at the date
	expiryDate = add_days( getdate(expiryDate), 1)

	log_data = {
		"erpWorkOrderID": erpWorkOrderID,
		"qty": qty,
		"packets": packets,
		"expiryDate": expiryDate,
		"draft":draft
	}

	if now:
		log_data['now'] = now

	save_log("Work Order", data_name, log_data, reopen=1)

	if cint(now):
		return _submit_work_order_finish_goods(
			erpWorkOrderID = erpWorkOrderID, 
			packets = packets, 
			qty = qty, 
			expiryDate = expiryDate, 
			draft = draft
		)
	else:
		return {
			"result":"Scheduled"
		}

def _submit_work_order_finish_goods(erpWorkOrderID, packets=0, qty=0, expiryDate="", draft=False, log_name=None):
	ERPWorkOrderID = erpWorkOrderID
	data_name = f"Finish Work Order {ERPWorkOrderID}"

	if get_foms_settings("disable_woirk_order_operation_update"):
		return {
			"ERPStockEntry": "Temporary disabled"
		}
	
	work_order_name, lot_id, status,packet_size,conversion_factor  = frappe.db.get_value("Work Order", ERPWorkOrderID, ['name', 'foms_lot_id', 'status', 'packet_size', 'conversion_factor']) or ("", "", "", '', '')
	qty_from_packet = flt(conversion_factor) * flt(packets)
	qty = qty or qty_from_packet
	
	# skip before operation 3 has done
	operation_3_status = frappe.db.get_value("Stock Entry", {
		"work_order":work_order_name,
		"operation": OPERATION_MAP_NAME.get(3),
		"docstatus":1
	})
	if not operation_3_status:
		return {
			"result":"Operation 3 should be complete first."
		}

	if status == "Completed":
		update_log("Work Order", data_name, "Work Order", work_order_name)
		return {
			"result":"Already complete"
		}
	
	if not work_order_name:
		frappe.throw(_(f"Work Order {ERPWorkOrderID} not found!"), frappe.DoesNotExistError)
	
	se_doc = make_stock_entry_wo(work_order_name,"Manufacture", qty, return_doc=1)

	se_doc.stock_entry_type_view = get_stock_entry_type("Harvesting Finish")

	# get rate from incoming rate from prev process, and get prorate until near prev amount 109.5
	rate_map = se_doc.get_previous_rate()
	for row in se_doc.get("items"):
		if row.s_warehouse:
			row.basic_rate = flt(rate_map.get(row.batch_no), 8)
			row.valuation_rate = row.basic_rate
			row.set_basic_rate_manually = 1

	se_doc.set_expense_account()
	se_doc.flags.ignore_double_entries = 1

	if not draft:
		se_doc.save()
		se_doc.submit()
	else:
		se_doc.flags.ignore_validate = 1
		se_doc.flags.ignore_mandatory = 1
		se_doc.flags.ignore_permissions = 1
		se_doc.save()

	# Create Draft Delivery Note
	for d in se_doc.get("items"):
		if d.is_finished_item:
			frappe.db.set_value("Batch", d.batch_no, "expiry_date", getdate(expiryDate))
			create_do_based_on_work_order(se_doc.work_order, d.qty, d.t_warehouse, d.batch_no)

	update_log("Work Order", data_name, "Work Order", work_order_name, name_id=log_name)

	return {
		"ERPStockEntry":se_doc.name
	}

def run_pending_harvesting():
	now_time = get_datetime()
	end_range = now_time - timedelta(minutes=10)

	for d in frappe.db.sql("select name, raw_data, data_name from `tabFOMS Data Mapping` where status = 'Unknown' and created_on < %s ", (end_range), as_dict=1):
		data = json.loads(d.raw_data)
		if "ERPWorkOrderID" in data:
			data['erpWorkOrderID'] = cstr(data['ERPWorkOrderID'])
			del data['ERPWorkOrderID']

		if not data.get('erpWorkOrderID'):
			continue
		
		if "Finish Work Order" in d.data_name:
			_submit_work_order_finish_goods(
				erpWorkOrderID=data.get('erpWorkOrderID'), 
				packets=flt(data.get('packets')), 
				qty=flt(data.get('qty')), 
				expiryDate=data.get('expiryDate'), 
				draft=cint(data.get('draft')),
				log_name=d.name
			)

def add_wip_additional_cost(stock_entry, work_order):
	# get all additional from transfer material
	data = frappe.db.sql("""
		SELECT 
			c.expense_account,
			c.exchange_rate,
			c.account_currency,
			c.description,
			c.amount,
			c.base_amount
		FROM
			`tabLanded Cost Taxes and Charges` c
				LEFT JOIN
			`tabStock Entry` s ON s.name = c.parent
		WHERE
			c.parentfield = 'additional_costs'
				AND c.parenttype = 'Stock Entry'
				AND s.work_order = %s
				AND s.purpose = 'Material Transfer for Manufacture'
				AND s.docstatus = 1
	""", (work_order), as_dict=1, debug=0)
	data_map = {}
	for d in data:
		key = (d.expense_account, d.description)
		if key in data_map:
			data_map[key].amount = data_map[key].amount + d.amount
			data_map[key].base_amount = data_map[key].base_amount + d.base_amount
		else:
			data_map[key] = d
		
	
	for key, d in data_map.items():
		row = stock_entry.append("additional_costs")
		row.update(d)

	return stock_entry

# Create Material Reserve
@frappe.whitelist()
def create_raw_material_reserve(items, erpWorkOrderID="", ERPWorkOrderID=""):
	ERPWorkOrderID = erpWorkOrderID or ERPWorkOrderID
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

	update_log("Material Request", data_name, "Material Request", doc.name)

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

	update_log("Material Return", data_name, "Purchase Receipt", doc.name)

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

	update_log("Packaging", data_name,"Packaging",  pack_name)

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

	image_urls = []
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
			image_urls.append(file_save.file_url)
		else:
			image_urls.append(image_url)

	path_src = ";".join(image_urls)
	doc.db_set("attachment", path_src)	

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

	update_log("Delivery Note", data_name, "Delivery Note", doc.name)

	return True


@frappe.whitelist()
def create_raw_material(data):
	data = frappe._dict(data)
	# logger
	name = data.get("rawMaterialRefNo")
	data_name = f"Create Raw Material {name}"
	save_log("Raw Material", data_name, data)

	res = _create_raw_material(data)

	update_log("Raw Material", data_name, "Item", res)
	
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