# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.model.naming import make_autoname

class MaintenanceRequest(Document):
  pass
	# def autoname(self):
	# 	self.name = make_autoname(self.name1[0:3].upper() + "-.#####") 

@frappe.whitelist()
def create_to_do(name):
	todo = frappe.new_doc("ToDo")
	todo.update({"reference_type": "Maintenance Request", "reference_name": name})
	return todo

@frappe.whitelist()
def create_asset_repair(name, asset, asset_name):
	asset_repair = frappe.new_doc("Asset Repair")
	asset_repair.update({"asset": asset, "asset_name": asset_name, "request_id": name})
	return asset_repair

@frappe.whitelist()
def create_asset_maintenance_log(name,asset_name, item_code, item_name):
	asset_maintenance_log = frappe.new_doc("Asset Maintenance Log")
	asset_maintenance_log.update(
		{
      		"request_id": name,
			"asset_name": asset_name,
			"item_code": item_code,
			"item_name": item_name,
      
		}
	)
	return asset_maintenance_log