# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from erpnext.foms.doctype.foms_integration_settings.foms_integration_settings import FomsAPI, get_farm_id
 
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
			{"fieldname": "qty_reserve", 				"label": "Reserved Qty", 		"fieldtype": "Float", 		"width": 120},
			{"fieldname": "current_qty", 				"label": "Current Qty", 		"fieldtype": "Float", 		"width": 120},
			{"fieldname": "status", 					"label": "Status", 				"fieldtype": "Data", 		"width": 110},
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
	
	def get_data(self):
		self.raw_data = []
		if self.filters.status in ['Reserved', 'Issued']:
			self.raw_data = self.fetch_data(self.filters.status)
		else:
			self.raw_data  = self.fetch_data("Reserved")
			self.raw_data += self.fetch_data("Issued")

	def process_data(self):
		for d in self.raw_data:
			row = {
				"work_order_number": d.get("workOrderNumber"),
				"raw_material_ref_no": d.get("rawMaterialRefNo"),
				"raw_material_name": d.get("rawMaterialName"),
				"raw_material_batch_ref_no": d.get("rawMaterialBatchRefNo"),
				"location": d.get("location"),
				"uom": d.get("uom"),
				"qty_reserve": d.get("qtyReserve"),
				"current_qty": d.get("currentQty"),
				"status": d.get("status"),
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