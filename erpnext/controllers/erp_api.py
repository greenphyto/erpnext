import frappe, json, erpnext
from six import string_types
from frappe.utils import flt, now_datetime, cint, getdate, cstr, get_datetime, add_days, nowtime, today
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
from erpnext.stock.stock_ledger import get_valuation_rate
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
from erpnext.stock.utils import get_default_warehouse
from erpnext.stock.stock_ledger import get_valuation_rate

PRECISION_FACTOR = 4

def get_data(data):
	if isinstance(data, string_types):
		data = json.loads(data)

	if type(data) == dict:
		data = frappe._dict(data)

	return data

@frappe.whitelist()
def update_item_safety_stock(item_code: str, safety_stock, company):
	"""Update Item.safety_stock given `item_code` and `safety_stock`.

	Args:
		item_code (str): The Item code (Item name).
		safety_stock (Any): New safety stock value (number-like).

	Returns:
		Dict with updated values.
	"""
	if not item_code:
		frappe.throw("item_code is required")

	if not frappe.db.exists("Item", item_code):
		frappe.throw(_(f"Item {item_code} not found"), frappe.DoesNotExistError)

	# coerce to float and validate non-negative
	try:
		new_val = flt(safety_stock)
	except Exception:
		frappe.throw("safety_stock must be a number")

	# Update the field
	frappe.db.set_value("Item", item_code, "safety_stock", new_val)

	# Also sync with reorder system:
	# - If Item has any reorder rows, update their reorder level to match safety stock
	# - If no reorder rows exist, set minimum order qty to 100
	reorder_rows = frappe.get_all(
		"Item Reorder",
		filters={"parent": item_code, "material_request_type":"Purchase"},
		pluck="name",
	)

	if reorder_rows:
		for row_name in reorder_rows:
			frappe.db.set_value("Item Reorder", row_name, "warehouse_reorder_level", new_val)
			break

		result = {
			"item_code": item_code,
			"safety_stock": new_val,
			"reorder_row_created": False,
			"updated": True,
		}
	else:
		data = frappe.db.sql("""
			SELECT
				sle.posting_date,
				sle.posting_time,
				sle.item_code,
				sle.warehouse,
				sle.actual_qty AS qty_in,
				sle.qty_after_transaction AS balance_after,
				sle.voucher_no AS purchase_receipt,
				pr.supplier,
				pr.supplier_name
			FROM
				`tabStock Ledger Entry` sle
			JOIN
				`tabPurchase Receipt` pr
					ON sle.voucher_type = 'Purchase Receipt'
					AND sle.voucher_no = pr.name
			WHERE
				sle.item_code = %s
				AND pr.company = %s
				AND sle.actual_qty > 0
				AND sle.voucher_type = 'Purchase Receipt'
			ORDER BY
				sle.posting_date DESC,
				sle.posting_time DESC
			LIMIT 1
		""", (item_code, company), as_dict=1)
		if data:
			data = data[0]
		else:
			data = {}

		item_doc = frappe.get_doc("Item", item_code)
		warehouse = data.get("warehouse")
		if not warehouse:
			warehouse = get_default_warehouse(item_code, company)
		
		pic = frappe.db.get_value("Part Number Details", {"code":item_code}, "pic")
		if not pic:
			pic = frappe.db.get_value("Part Number Details", {
				"material_group":item_doc.material_group, "pic": ['is', 'Set']
			}, "pic")

		if not pic or not warehouse:
			frappe.throw("PIC or Warehouse is missing")  

		else:
			# Create a default reorder row with reorder level and qty
			item_doc.append("reorder_levels", {
				"warehouse": warehouse,
				"warehouse_reorder_level": new_val,
				"warehouse_reorder_qty": flt(data.get("qty_in")) or new_val*2, # default 2 times from stock level
				"material_request_type": "Purchase",
				"pic": pic
			})
			item_doc.save()
			result = {
				"item_code": item_code,
				"safety_stock": new_val,
				"reorder_row_created": True,
				"reorder_qty": 100,
				"updated": True,
			}

	return result

def save_log(doctype, data_name, raw_data, reopen=False, now=False, endpoint=""):
	if frappe.conf.testing_site:
		now = 1
		
	return frappe.enqueue("erpnext.foms.doctype.foms_data_mapping.foms_data_mapping.create_foms_data",
		data_type=doctype, 
		data_name=data_name,
		raw=raw_data,
		reopen=reopen,
		now=now,
		endpoint=endpoint
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
		save_log("TEST", "test", data, endpoint="ping_data")
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
	save_log("BOM", data_name, {"data":data}, endpoint="create_bom")
	result = create_bom_products(data, product_id, submit=submit)
	update_log("BOM", data_name, "BOM", result)
	return {"ERPBomId":result}

@frappe.whitelist()
def create_work_order(fomsWorkOrderID, fomsLotID, productID, salesOrderNo, qty, gross_weight, uom, submit=False, company=""):
	if not company:
		company = erpnext.get_default_company()

	data_name = f"Work Order {fomsLotID}"
	save_log("Work Order", data_name, {
		"fomsWorkOrderID":fomsWorkOrderID, 
		"fomsLotID":fomsLotID, 
		"productID":productID, 
		"salesOrderNo":salesOrderNo, 
		"qty":qty, 
		"uom":uom, 
		"gross_weight":gross_weight,
		"submit":submit,
		"company":company
	}, endpoint="create_work_order")

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
	}, company=company)
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
def update_qty_after_finish(erpWorkOrderID, batch_id, new_qty, submit=1, posting_date="", posting_time="", remark=""):
	# warehouse finish goods
	company = frappe.get_value("Work Order", erpWorkOrderID, "company")
	wh_name = frappe.db.get_single_value("Manufacturing Settings", "default_fg_warehouse")
	item = frappe.get_value("Batch", batch_id, "item")
	posting_date = posting_date or today()
	posting_time = posting_time or nowtime()
	if not item:
		return {"result": False, "error": "Batch ID Not Found!"}
	
	# Siapkan dokumen utama
	sr = frappe.get_doc({
		"doctype": "Stock Reconciliation",
		"company": company,
		"posting_date": posting_date,
		"posting_time": posting_time,
		"purpose": "Stock Reconciliation",
		"remarks": remark or "Auto Stock Reconciliation via custom script",
	})

	# Tambahkan baris items
	child = sr.append("items", {})
	child.item_code = item
	child.warehouse = wh_name
	child.qty = new_qty
	child.batch_no = batch_id
	sr.reff_id = erpWorkOrderID

	# Simpan & submit
	sr.insert(ignore_permissions=True)

	if submit:
		sr.submit()

	return {"result":True}

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
	se.fg_completed_qty = wo_doc.qty * flt(global_percent)/100

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
		for m in wo_doc.get("required_items"):
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
			pack_row.qty = cint(d.required_qty * global_percent/100)
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
	percentage = flt(percentage)
	rawMaterials = get_data(rawMaterials)
	data_name = f"Operation {operationNo} Work Order {ERPWorkOrderID}"
	log_res = save_log("Work Order", data_name, {
		"ERPWorkOrderID":ERPWorkOrderID, 
		"operationNo":operationNo, 
		"percentage":percentage, 
		"rawMaterials":rawMaterials, 
		"now": cint(now)
	}, now=1, endpoint="update_work_order_operation_status")

	if log_res.status != "Unknown":
		return
	
	if cint(get_foms_settings("disable_woirk_order_operation_update")):
		return {
			"result": False,
			"percentage": 0,
			"error":"Temporary disabled"
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
			"result": True,
			"percentage": percentage,
			"message": "Already updated"
		}
	
	wip_warehouse = frappe.get_value("Job Card", job_card_name, "wip_warehouse")

	# create stock entry
	if job_card_name and frappe.db.get_value("Stock Entry", {"job_card": job_card_name, "docstatus":1}, cache=False, debug=0):
		update_log("Work Order", data_name, "Job Card", temp.get("name"))
		return {
			"result": True,
			"percentage": percentage,
			"message": "Already updated (se)"
		}

	if cint(operationNo) == 3 and not now:
		return {
			"result":True,
			"message":"Scheduled"
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
			"result": True,
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

	update_log("Work Order", data_name, "Job Card", job_card.name, log_name)

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
		"draft":cint(draft),
		"now":cint(draft),
	}

	if now:
		log_data['now'] = now

	save_log("Work Order", data_name, log_data, reopen=1, now=now, endpoint="submit_work_order_finish_goods")

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
			"result": True,
			"message":"Scheduled"
		}

from erpnext.controllers.erp import detect_work_order_different
def _submit_work_order_finish_goods(erpWorkOrderID, packets=0, qty=0, expiryDate="", draft=False, log_name=None):
	ERPWorkOrderID = erpWorkOrderID
	data_name = f"Finish Work Order {ERPWorkOrderID}"

	if get_foms_settings("disable_woirk_order_operation_update"):
		return {
			"ERPStockEntry": "Temporary disabled"
		}
	
	wo_doc = frappe.get_doc("Work Order", ERPWorkOrderID)
	work_order_name = wo_doc.name
	status = wo_doc.status
	conversion_factor = wo_doc.conversion_factor
	producted_qty = wo_doc.qty
	qty_from_packet = flt(conversion_factor) * flt(packets)
	qty = cint(qty) or qty_from_packet
	
	# skip before operation 3 has done
	operation_3_status = frappe.db.get_value("Stock Entry", {
		"work_order":work_order_name,
		"operation": OPERATION_MAP_NAME.get(3),
		"docstatus":1
	})
	if not operation_3_status:
		return {
			"result":False,
			"error":"Operation 3 should be complete first."
		}

	if status == "Completed":
		update_log("Work Order", data_name, "Work Order", work_order_name)
		return {
			"result":True,
			"message":"Already complete"
		}
	
	if not work_order_name:
		frappe.throw(_(f"Work Order {ERPWorkOrderID} not found!"), frappe.DoesNotExistError)
	
	se_doc = make_stock_entry_wo(work_order_name,"Manufacture", qty, return_doc=1)

	se_doc.stock_entry_type_view = get_stock_entry_type("Harvesting Finish")
	se_doc.expense_loss_account = frappe.get_value("Company", se_doc.company , "production_loss_account")
	enable_excess_qty = frappe.db.get_single_value("Manufacturing Settings", "enable_attrition_qty")
	finish_uom, finish_item_code = None, None

	# get rate from incoming rate from prev process, and get prorate until near prev amount 109.5
	rate_map = se_doc.get_previous_rate()
	for row in se_doc.get("items"):
		if row.s_warehouse:
			row.basic_rate = flt(rate_map.get(row.batch_no), 8)
			row.rate_map = row.basic_rate
			row.valuation_rate = row.basic_rate
			row.set_basic_rate_manually = 1
		if enable_excess_qty:
			# attrition_qty = self.
			if row.t_warehouse:
				row.qty = qty
				row.amount = qty * flt(row.basic_rate)
				finish_uom =  row.uom
				finish_item_code = row.item_code

	# add fake item
	child = se_doc.append("items")
	child.qty = producted_qty - qty
	child.uom = finish_uom
	child.item_code = finish_item_code
	child.t_warehouse = frappe.db.get_single_value("Manufacturing Settings", "default_scrap_warehouse")
	child.is_process_loss = 1
	child.expense_account = se_doc.expense_loss_account

	se_doc.set_expense_account()
	se_doc.flags.ignore_double_entries = 1

	if not draft:
		se_doc.save()
		se_doc.submit()
		detect_work_order_different(se_doc)
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
		company=""
	):
	if not company:
		company = erpnext.get_default_company()

	item_str = ", ".join([d.get("rawMaterialRefNo") for d in items])
	data_name = f"Create Material Request {item_str}"
	save_log("Material Request", data_name, {
		"transactionDate":transactionDate, 
		"requiredBy":requiredBy, 
		"requestedBy":requestedBy, 
		"items":items, 
		"company":company,
		"cancel":cancel
	}, endpoint="create_material_request" )
	# find draft
	doc_name = frappe.get_value("Material Request", {"requested_by":requestedBy, "workflow_state":"Draft"})
	if doc_name:
		doc = frappe.get_doc("Material Request", doc_name)
	else:
		# create material request
		doc = frappe.new_doc("Material Request")
		doc.company = company
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
	save_log("Material Request", data_name, data, endpoint="create_material_return")
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
	save_log("Packaging", data_name, data, endpoint="create_update_packaging")

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
	save_log("Delivery Note", data_name, data, endpoint="update_delivery_note_signature")

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
	save_log("Raw Material", data_name, data, endpoint="create_raw_material")

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
		
@frappe.whitelist()
def get_document_lotid(lotid=""):
	# 1. Validation for empty parameter
	if not lotid:
		frappe.throw(_("The parameter 'lotid' is required."), frappe.ValidationError)
	
	data = {"transactions": []}

	# 2. Fetch Batch details
	batch = frappe.db.get_value("Batch", {"foms_lot_id": lotid}, "*", as_dict=1)
	
	# 3. Check if Batch exists, if not throw 404
	if not batch:
		frappe.throw(
			msg=_("Batch with Lot ID '{0}' not found.").format(lotid), 
			exc=frappe.DoesNotExistError
		)

	# Batch
	data['batch'] = batch

	# get ledger
	sle = frappe.db.sql("""
		SELECT 
			sle.posting_date,
			sle.warehouse,
			sle.voucher_type,
			sle.voucher_no,
			sle.actual_qty
		FROM
			`tabStock Ledger Entry` sle
		WHERE
			sle.batch_no = %s
		ORDER BY sle.posting_date DESC, sle.posting_time DESC, sle.name DESC
		LIMIT 10
	""", (data['batch'].name), as_dict=1)
	for d in sle:
		doc = frappe.get_doc(d.voucher_type, d.voucher_no)
		data["transactions"].append(doc.as_dict())
		if doc.doctype == "Stock Entry" and doc.purpose == "Manufacture":
			data['batch']['work_order'] = doc.work_order

	return data

@frappe.whitelist()
def get_delivery_by_lotid(lotid=None, delivery_date=""):
	if isinstance(lotid, str):
		lotid = json.loads(lotid)
	lotid = lotid or []

	use_delivery_date = cstr(getdate(delivery_date))
	dn_list = []
	data = {}
	for lot in lotid:
		data['batch'] = {}
		batch = frappe.db.get_value("Batch", {"foms_lot_id": lot}, "*", as_dict=1)
		if not batch:
			continue

		data['batch'][lot] = batch

	cond = " AND dn.delivery_date = %(delivery_date)s "
	filters = {
		"delivery_date": use_delivery_date
	}
	if lotid:
		cond += " AND dni.foms_lot_name in %(lots)s "
		filters['lots'] = lotid
	# Get Delivery Note Items for the batch on the specified delivery date
	dn_items = frappe.db.sql("""
		SELECT 
			dn.name AS delivery_note,
			dni.item_code,
			dni.qty,
			dni.batch_no,
			dn.posting_date
		FROM
			`tabDelivery Note Item` dni
				JOIN
			`tabDelivery Note` dn ON dn.name = dni.parent
		WHERE
			dn.docstatus != 2
			{}
		ORDER BY dn.delivery_date DESC
	""".format(cond), filters, as_dict=1, debug=0)

	data['transactions'] = []
	for d in dn_items:
		dn_list.append(d)
		doc = frappe.get_doc("Delivery Note", d.delivery_note)
		data['transactions'].append(doc.as_dict())

	return data