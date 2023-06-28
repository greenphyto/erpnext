# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document

class SmartFMWorkOrder(Document):
	pass

@frappe.whitelist()
def create_asset_maintenance_log(asset_name, item_code, item_name):
	asset_maintenance_log = frappe.new_doc("Asset Maintenance Log")
	asset_maintenance_log.update(
		{
			"asset_name": asset_name,
			"item_code": item_code,
			"item_name": item_name,
		}
	)
	return asset_maintenance_log