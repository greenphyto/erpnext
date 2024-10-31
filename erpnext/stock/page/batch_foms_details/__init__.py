import frappe, json
from frappe.utils import datetime, now, get_datetime, flt, getdate, format_datetime, format_date, cint
from erpnext.foms.doctype.foms_integration_settings.foms_integration_settings import FomsAPI,is_enable_integration, get_farm_id
from erpnext.controllers.foms import update_foms_batch as _update_foms_batch
LOG_DATA_NAME = "Batch FOMS All Data"
REFF_ID = "FOMS Batch for ERP"

@frappe.whitelist()
def get_data(update=False, filters={}):
	api = FomsAPI()
	filters = frappe._dict( json.loads(filters) )

	log_name = frappe.db.exists("FOMS Data Mapping", {"data_name":LOG_DATA_NAME})
	non_stock_item = [ d.foms_raw_id for d in frappe.db.get_all("Item", {"is_stock_item":0}, ['foms_raw_id']) ]
	if filters.hide_expired:
		non_expired_batch_only = 1
	else:
		non_expired_batch_only = 0

	if not log_name:
		log = frappe.new_doc("FOMS Data Mapping")
		log.data_type = "Batch"
		log.data_name = LOG_DATA_NAME
		log.status = "Mapped"
		log.doc_type = "Batch"
		log.doc_name = "All Batch"
		raw_data = api.get_all_batch(active_batch_only=non_expired_batch_only)
		log.raw_data = json.dumps(raw_data)
		log.insert()
	else:
		log = frappe.get_doc("FOMS Data Mapping", log_name)
	
	if not cint(update) and log_name:
		raw_data = log.get_data()
	else:
		log = frappe.get_doc("FOMS Data Mapping", log_name)
		raw_data = api.get_all_batch(active_batch_only=non_expired_batch_only)
		log.raw_data = json.dumps(raw_data)
		log.last_sync = now()
		log.save()

	erp_batch_all = frappe.db.get_all("Batch", limit=99999, fields=['name', 'batch_qty', 'expiry_date'])
	erp_batch = {}
	for d in erp_batch_all:
		erp_batch[d.name] = d

	data = []

	for d in raw_data.get("items") or []:
		d = frappe._dict(d)
		d.foms_qty = d.qtyLeft
		d.foms_exp = format_date(d.expiryDate)
		d.batch_no = d.batchRefNo
		if not d.rawMaterialId:
			continue 

		if filters.get('hide_empty') and d.foms_qty == 0:
			continue

		if filters.get('batch_no') and filters.batch_no.lower() not in d.batchRefNo.lower() :
			continue

		if cint(d.rawMaterialId) in non_stock_item:
			continue

		if d.batch_no in erp_batch:
			d.erp_batch_missing = False
			batch = erp_batch.get(d.batch_no)
			d.erp_qty = batch.batch_qty
			d.erp_exp = format_date(batch.expiry_date)
		else:
			d.erp_batch_missing = True
			d.erp_qty = ""
			d.erp_exp = ""
		data.append(d)
	
	stock_recon = frappe.get_value("Stock Reconciliation", {"reff_id":REFF_ID, "docstatus":0})

	result = {
		"data":data,
		"last_fetch": format_datetime(log.last_sync),
		"stock_recon":stock_recon
	}
	return result

@frappe.whitelist()
def update_foms_batch(batch_no, batch_id, warehouseID, qty):
	item_code = frappe.get_value("Batch", batch_no, "item")
	if item_code:
		res = _update_foms_batch(batch_id, item_code, warehouseID, qty)
		return res

@frappe.whitelist()
def update_erp_batch(batch_no,batch_id="",item_id="",warehouseID="",qty=0,expired_date="", stock_recon="",exp=""):
	# create batch
	# add batch
	if expired_date:
		expired_date = getdate(expired_date)
	
	exists = stock_recon or frappe.get_value("Stock Reconciliation", {"reff_id":REFF_ID, "docstatus":0})
	if not exists:
		doc = frappe.new_doc("Stock Reconciliation")
	else:
		doc = frappe.get_doc("Stock Reconciliation", exists)

	item_code = frappe.get_value("Batch", batch_no, "item")
	if not item_code:
		item_code = frappe.get_value("Item", {"foms_raw_id":item_id})
		if not item_code:
			return {"error":f"Missing Raw material with FOMS ID {item_id}"}
		
		batch = frappe.new_doc("Batch")
		batch.item = item_code
		batch.batch_id = batch_no
		batch.foms_id = batch_id
		batch.expired_date = expired_date
		batch.insert()
		# can create new batch if item are exists
	
	row_exists = doc.get("items", {"batch_no":batch_no})
	if row_exists:
		row = row_exists[0]
	else:
		row = doc.append("items")

	warehouse = frappe.get_value("Warehouse",{"foms_id": warehouseID})

	if not warehouse:
		return {"error":f"Missing warehouse with FOMS ID {warehouseID}"}

	row.batch_no = batch_no
	row.item_code = item_code
	row.warehouse = warehouse
	row.qty = qty
	doc.reff_id = REFF_ID
	doc.purpose = "Stock Reconciliation"
	doc.save()

	return {
		"stock_recon":doc.name,
		"batchRefNo":batch_no,
		"qty":qty,
		"id":batch_id,
		"expired_date":expired_date
	}

	