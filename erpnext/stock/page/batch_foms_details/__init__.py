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
	print("filters", filters)
	print("Find exist", log_name)
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
	
	print(26, update, log_name)
	if not cint(update) and log_name:
		print("Refresh only")
		raw_data = log.get_data()
	else:
		print("Fetch new data")
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
		if filters.get('hide_empty') and d.foms_qty == 0:
			continue

		if filters.get('batch_no') and filters.batch_no.lower() not in d.batchRefNo.lower() :
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
	
	stock_recon = "MAT-RECO-2024-00028"

	result = {
		"data":data,
		"last_fetch": format_datetime(log.last_sync),
		"stock_recon":stock_recon
	}
	return result

@frappe.whitelist()
def update_foms_batch(batch_no, batch_id, warehouseID, qty):
	# return {
	# 	"rawMaterialId": 51,
	# 	"batchRefNo": "RM-LS-TENBN00001",
	# 	"dateOfCreation": "2024-10-30T11:19:48.890584",
	# 	"qtyAdd": 27,
	# 	"qtyUsed": 0,
	# 	"qtyReconcilled": 0,
	# 	"qtyLeft": 0,
	# 	"unitCost": 0,
	# 	"quantityUOM": None,
	# 	"totalCost": 0,
	# 	"expiryDate": "2025-08-23T00:00:00",
	# 	"lossRatePercent": 0,
	# 	"rackNumbers": None,
	# 	"warehouseName": None,
	# 	"warehouseId": 37,
	# 	"warehouseRefId": None,
	# 	"supplierId": 0,
	# 	"supplierName": None,
	# 	"supplierRefId": None,
	# 	"status": None,
	# 	"isSeed": False,
	# 	"id": 287
	# }
	item_code = frappe.get_value("Batch", batch_no, "item")
	if item_code:
		res = _update_foms_batch(batch_id, item_code, warehouseID, qty)
		return res

@frappe.whitelist()
def update_erp_batch(batch_no,warehouse,qty,stock_recon="",exp=""):
	# create batch
	# add batch
	exists = stock_recon or frappe.get_value("Stock Reconcilliation", {"reff_id":REFF_ID, "docstatus":0})
	if not exists:
		doc = frappe.new_doc("Stock Reconcilliation")
	else:
		doc = frappe.get_doc("Stock Reconcilliation", exists)

	item_code = frappe.get_value("Batch", batch_no, "item")
	if not item_code:
		# can create new batch if item are exists
		return

	
	row_exists = doc.get("items", {"batch_no":batch_no})
	if row_exists:
		row = row_exists[0]
	else:
		row = doc.append("items")

	row.batch_no = batch_no
	row.item_code = item_code
	row.warehouse = warehouse
	row.qty = qty
	doc.save()

	return True

	