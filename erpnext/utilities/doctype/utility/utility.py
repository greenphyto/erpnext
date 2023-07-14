# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

class Utility(Document):
	pass

@frappe.whitelist()
def create_meter_reading(name, location):
	meter_reading = frappe.new_doc("Meter Reading")
	meter_reading.update({"meter_id": name, "meter_location": location})
	return meter_reading