# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from erpnext.foms.doctype.foms_integration_settings.foms_integration_settings import FomsAPI, get_farm_id
from frappe.utils import cint, flt
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
		self.api = FomsAPI()
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
			# {"fieldname": "current_qty", 				"label": "Current Qty", 		"fieldtype": "Float", 		"width": 120},
			{"fieldname": "reserve_date", 				"label": "Reserve Date", 		"fieldtype": "Date", 		"width": 120},
			{"fieldname": "issued_timestamp", 			"label": "Issued Time", 		"fieldtype": "Datetime", 	"width": 160},
			{"fieldname": "lot_id", 					"label": "Lot ID", 				"fieldtype": "Data", 		"width": 110},
			# {"fieldname": "reserve_by_user_name", 		"label": "Reserved By", 		"fieldtype": "Data", 		"width": 140},
			{"fieldname": "product_ref_no", 			"label": "Product Ref No", 		"fieldtype": "Data", 		"width": 130},
			{"fieldname": "product_name", 				"label": "Product Name", 		"fieldtype": "Data", 		"width": 160},
			# {"fieldname": "product_name", 				"label": "Product Name", 		"fieldtype": "Data", 		"width": 160},
		]

	def fetch_data(self, status=""):
		url = build_url(
			"/userportal",
			"/RawMaterialUP/SearchRawMaterialReservedOrIssued",
			keyword=self.filters.item_code,
			rowsPerTable=10,
			page=0,
			farmId=15,
			skipCount=0,
			maxResultCount=10,
			status=status
		)
		self.foms_data = self.api.req("GET", url)
		if "items" in self.foms_data:
			return self.foms_data['items']
		return []
	
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
				se.work_order asc, sle.posting_date asc
		""", (self.filters.item_code, self.filters.warehouse), as_dict=1)
		self.erp_data = {}
		for d in data:
			if d.lot_id not in self.erp_data:
				self.erp_data[d.lot_id]=[]
			self.erp_data[d.lot_id].append(d)
	
	def get_data(self):
		self.raw_data = []
		if self.filters.status in ['Reserved', 'Issued']:
			self.raw_data = self.fetch_data(self.filters.status)
		else:
			self.raw_data  = self.fetch_data("Reserved")
			self.raw_data += self.fetch_data("Issued")

		# Order raw_data by lotId ASC, then reserveDate ASC
		self.raw_data = sorted(
			self.raw_data or [],
			key=lambda d: (
				(d or {}).get("lotId") or "",
				(d or {}).get("reserveDate") or "",
			),
		)

	def process_data(self):
		self.get_erp_data()
		orders = {}
		for d in self.raw_data:
			lot_id = d.get("lotId")
			idx = cint(orders.get(lot_id))
			orders[lot_id] = idx + 1
			temp = self.erp_data.get(lot_id)
			if temp and len(temp) > idx:
				erp_data = temp[idx]
			else:
				erp_data = {}
			

			row = {
				"work_order_number": d.get("workOrderNumber"),
				"raw_material_ref_no": d.get("rawMaterialRefNo"),
				"raw_material_name": d.get("rawMaterialName"),
				"raw_material_batch_ref_no": d.get("rawMaterialBatchRefNo"),
				"location": d.get("location"),
				"uom": d.get("uom"),
				"foms_used": d.get("qtyReserve"),
				"erp_used": abs(erp_data.get("actual_qty")),
				"diff": flt(d.get("qtyReserve")) - abs(erp_data.get("actual_qty")),

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
