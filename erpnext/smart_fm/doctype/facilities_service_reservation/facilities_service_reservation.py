# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import getdate, get_datetime
from frappe import _

class FacilitiesServiceReservation(Document):
	def validate(self):
		self.validate_time()
		self.validate_service()

	def validate_time(self):
		if get_datetime(self.from_time) > get_datetime(self.to_time):
			frappe.throw(_("From time cannot higher than to time"))

	