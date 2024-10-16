import frappe, json
from frappe.utils import datetime, now, get_datetime, flt, getdate, format_datetime, format_date
from erpnext.foms.doctype.foms_integration_settings.foms_integration_settings import FomsAPI,is_enable_integration, get_farm_id

LOG_DATA_NAME = "Batch FOMS All Data"

@frappe.whitelist()
def get_data(update=False):
	api = FomsAPI()

	log_name = frappe.db.exists("FOMS Data Mapping", {"data_name":LOG_DATA_NAME})
	if not log_name:
		log = frappe.new_doc("FOMS Data Mapping")
		log.data_type = "Batch"
		log.data_name = LOG_DATA_NAME
		log.status = "Mapped"
		log.doc_type = "Batch"
		log.doc_name = "All Batch"
		raw_data = api.get_all_batch()
		log.raw_data = json.dumps(raw_data)
		log.insert()
	else:
		log = frappe.get_doc("FOMS Data Mapping", log_name)
	
	if not update and log_name:
		raw_data = log.get_data()
	else:
		log = frappe.get_doc("FOMS Data Mapping", log_name)
		raw_data = api.get_all_batch()
		log.raw_data = json.dumps(raw_data)
		log.last_sync = now()
		log.save()

	erp_batch_all = frappe.db.get_all("Batch", limit=99999, fields=['name', 'batch_qty', 'expiry_date'])
	erp_batch = {}
	for d in erp_batch_all:
		erp_batch[d.name] = d.batch_qty

	data = []

	for d in raw_data.get("items") or []:
		d = frappe._dict(d)
		d.foms_qty = d.qtyLeft
		d.foms_exp = format_date(d.expiryDate)
		d.batch_no = d.batchRefNo
		if d.batch_no in erp_batch:
			d.erp_batch_missing = False
			d.erp_qty = 0
			d.erp_exp = ""
		else:
			d.erp_batch_missing = True
			d.erp_qty = flt(erp_batch.get(d.batch_no))
			d.erp_exp = format_date(d.expiry_date)
		data.append(d)
	
	stock_recon = ""

	result = {
		"data":data,
		"last_fetch": format_datetime(log.last_sync),
		"stock_recon":stock_recon
	}
	return result