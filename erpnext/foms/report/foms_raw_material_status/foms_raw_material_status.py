# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
import json
from datetime import datetime
from frappe.utils.file_manager import save_file
from erpnext.foms.doctype.foms_integration_settings.foms_integration_settings import FomsAPI, get_farm_id
from frappe.utils import cint, flt, get_datetime
"""
https://foms-api.greenphyto.com/api/userportal/RawMaterialUP/SearchRawMaterialReservedOrIssued?keyword=RM-SD-DRE&status=Reserved&rowsPerTable=10&page=0&farmId=15&skipCount=0&maxResultCount=10
https://foms-api.greenphyto.com/api/userportal/RawMaterialUP/SearchRawMaterialReservedOrIssued?keyword=RM-SD-DRE&rowsPerTable=10&page=0&farmId=15&skipCount=0&maxResultCount=10
https://foms-api.greenphyto.com/api/userportal/RawMaterialUP/SearchRawMaterialReturn?keyword=RM-SD-DRE&rowsPerTable=10&page=0&farmId=15&skipCount=0&maxResultCount=10
"""

def execute(filters=None):
	return Report(filters).execute()

class Report():
	def __init__(self, filters):
		self.filters = filters
		self.data = []


	def setup_condition(self):
		self.cond = ""

	def setup_column(self):
		# Define report columns using Frappe dict format, aligned to example_field
		self.columns = [
			{"fieldname": "work_order_number", 			"label": "Work Order", 			"fieldtype": "Data", 		"width": 140},
			{"fieldname": "raw_material_ref_no", 		"label": "Raw Material Ref No", "fieldtype": "Data", 		"width": 150},
			{"fieldname": "raw_material_name", 			"label": "Raw Material Name", 	"fieldtype": "Data", 		"width": 180},
			# {"fieldname": "raw_material_batch_ref_no", 	"label": "Batch", 				"fieldtype": "Data", 		"width": 120},
			# {"fieldname": "location", 					"label": "Source Warehouse", 	"fieldtype": "Data", 		"width": 160},
			{"fieldname": "uom", 						"label": "UOM", 				"fieldtype": "Data", 		"width": 80},
			{"fieldname": "foms_status", 				"label": "FOMS Status", 				"fieldtype": "Data", 		"width": 110},
			{"fieldname": "erp_status", 				"label": "ERP Status", 				"fieldtype": "Data", 		"width": 110},
			{"fieldname": "foms_used", 					"label": "FOMS Use", 		"fieldtype": "Float", 		"width": 120, "precision":4},
			{"fieldname": "erp_used", 					"label": "ERP Use", 		"fieldtype": "Float", 		"width": 120, "precision":4},
			{"fieldname": "diff", 						"label": "Diff", 		"fieldtype": "Float", 		"width": 120},
			{"fieldname": "acc_diff", 					"label": "Diff Total", 		"fieldtype": "Float", 		"width": 120},
			# {"fieldname": "current_qty", 				"label": "Current Qty", 		"fieldtype": "Float", 		"width": 120},
			{"fieldname": "reserve_date", 				"label": "Reserve Date", 		"fieldtype": "Date", 		"width": 120},
			{"fieldname": "issued_timestamp", 			"label": "Issued Time", 		"fieldtype": "Datetime", 	"width": 160},
			{"fieldname": "lot_id", 					"label": "Lot ID", 				"fieldtype": "Data", 		"width": 110},
			# {"fieldname": "reserve_by_user_name", 		"label": "Reserved By", 		"fieldtype": "Data", 		"width": 140},
			{"fieldname": "product_ref_no", 			"label": "Product Ref No", 		"fieldtype": "Data", 		"width": 130},
			{"fieldname": "product_name", 				"label": "Product Name", 		"fieldtype": "Data", 		"width": 160},
			# {"fieldname": "product_name", 				"label": "Product Name", 		"fieldtype": "Data", 		"width": 160},
		]
	
	def get_erp_data(self):
		data = frappe.db.sql("""
			SELECT
				sle.name AS sle_name,
				sle.item_code,
				sle.posting_date,
				sle.actual_qty,
				sle.voucher_type,
				sle.voucher_no,
				se.name AS stock_entry,
				se.work_order,
				se.company,
				se.posting_date AS se_posting_date,
				SUBSTRING_INDEX(wo.name, '-', 2) as lot_id,
				wo.name AS work_order_no,
				wo.production_item,
				wo.qty AS wo_qty,
				wo.status AS wo_status
			FROM
				`tabStock Ledger Entry` sle
			LEFT JOIN `tabStock Entry` se
				ON sle.voucher_type = 'Stock Entry'
				AND sle.voucher_no = se.name
			LEFT JOIN `tabWork Order` wo
				ON se.work_order = wo.name
			WHERE
				sle.is_cancelled = 0
				AND se.docstatus = 1
				AND sle.item_code = %s
				AND se.purpose = "Material Transfer for Manufacture"
				AND sle.warehouse = %s
			ORDER BY
				se.work_order asc, sle.actual_qty desc
		""", (self.filters.item_code, self.filters.warehouse), as_dict=1)
		self.erp_data = {}
		for d in data:
			if d.lot_id not in self.erp_data:
				self.erp_data[d.lot_id]=[]
			self.erp_data[d.lot_id].append(d)
	
	def get_data(self):
		self.raw_data = []
		if self.filters.status in ['Reserved', 'Issued']:
			
			self.raw_data = fetch_data_foms(self.filters.item_code, self.filters.status)
		else:
			self.raw_data  = fetch_data_foms(self.filters.item_code,self.fetch_data("Reserved"))
			self.raw_data += fetch_data_foms(self.filters.item_code, "Issued")

		self.raw_data_map = {}
		for d in self.raw_data:
			lot_id = d.get("lotId")
			if lot_id not in self.raw_data_map:
				self.raw_data_map[lot_id] = []
			self.raw_data_map[lot_id].append(d)

	def process_data(self):
		self.get_erp_data()
		orders = {}
		acc_diff = 0
		for lot_id, val in self.raw_data_map.items():
			raw_data = sorted(
				val or [],
				key=lambda d: (
					get_datetime((d or {}).get("reserveDate")) or "",
					flt(d.get("qtyReserve"))
				)
			)
			for d in raw_data:
				lot_id = d.get("lotId")
				idx = cint(orders.get(lot_id))
				orders[lot_id] = idx + 1
				temp = self.erp_data.get(lot_id)
				if temp and len(temp) > idx:
					erp_data = temp[idx]
				else:
					erp_data = {}
				
				erp_used = abs(flt(erp_data.get("actual_qty")))
				diff = flt(d.get("qtyReserve")) - erp_used
				acc_diff += diff
				row = {
					"work_order_number": d.get("workOrderNumber"),
					"raw_material_ref_no": d.get("rawMaterialRefNo"),
					"raw_material_name": d.get("rawMaterialName"),
					"raw_material_batch_ref_no": d.get("rawMaterialBatchRefNo"),
					"location": d.get("location"),
					"uom": d.get("uom"),
					"foms_used": d.get("qtyReserve"),
					"erp_used": erp_used,
					"diff": diff,
					"acc_diff": acc_diff,
					"current_qty": d.get("currentQty"),
					"foms_status": d.get("status"),
					"erp_status": "Issued" if erp_data else "Not Found",
					"reserve_date": d.get("reserveDate"),
					"issued_timestamp": d.get("issuedTimeStamp"),
					"lot_id": d.get("lotId"),
					"reserve_by_user_name": d.get("reserveByUserName"),
					"product_ref_no": d.get("productRefNo"),
					"product_name": d.get("productName"),
				}
				self.data.append(row)
	def execute(self):
		self.setup_condition()
		self.setup_column()
		self.get_data()
		self.process_data()

		return self.columns, self.data

from urllib.parse import urlencode
def build_url(base, path, **params):
    query = urlencode({k: v for k, v in params.items() if v is not None})
    return f"{base.rstrip('/')}/{path.lstrip('/')}?{query}" if query else f"{base.rstrip('/')}/{path.lstrip('/')}"

@frappe.whitelist()
def fetch_data_foms(item_code, status):
	api = FomsAPI()
	url = build_url(
		"/userportal",
		"/RawMaterialUP/SearchRawMaterialReservedOrIssued",
		keyword=item_code,
		rowsPerTable=10,
		page=0,
		farmId=15,
		skipCount=0,
		maxResultCount=200,
		status=status
	)

	# Caching: use File doctype with name FOMS_fetch_ddmmyy.json
	date = datetime.now().strftime("%d%m%y")
	item = item_code
	file_prefix = f"FOMS_fetch_{date}_{item}"
	cached_doc = None
	cached = None
	try:
		latest = frappe.get_all(
			"File",
			filters={"file_name": ("like", f"{file_prefix}%")},
			fields=["name", "file_name", "creation"],
			order_by="creation desc",
			limit=1,
		)
		if latest:
			cached_doc = frappe.get_doc("File", latest[0].name)
			content = cached_doc.get_content()
			cached = json.loads(content) if content else None
	except Exception:
		cached = None

	# If cache exists and has this status, return from cache
	if isinstance(cached, dict):
		if status and cached.get(status):
			cached_result = cached.get(status) or {}
			if isinstance(cached_result, dict) and "items" in cached_result:
				return cached_result.get("items") or []
			elif isinstance(cached_result, list):
				return cached_result

	# Otherwise, fetch and then save/merge to cache
	foms_data = api.req("GET", url) or {}
	items = []
	if isinstance(foms_data, dict) and "items" in foms_data:
		items = foms_data.get("items") or []

	# Merge into cache structure by status
	cache_blob = cached if isinstance(cached, dict) else {}
	if status:
		cache_blob[status] = foms_data
	else:
		cache_blob["data"] = foms_data

	# Save as a new File record; pick latest by creation next time
	try:
		file_name = f"{file_prefix}.json"
		save_file(file_name, json.dumps(cache_blob), None, None, is_private=1)
		frappe.db.commit()
	except Exception:
		pass

	return items