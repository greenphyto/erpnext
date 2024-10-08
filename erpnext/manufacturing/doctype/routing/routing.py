# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint, flt


class Routing(Document):
	def validate(self):
		self.calculate_operating_cost()
		self.set_routing_id()

	def on_update(self):
		self.calculate_operating_cost()

	def calculate_operating_cost(self):
		for operation in self.operations:
			if not operation.operation_rate:
				if operation.calculation_type == "Per Qty":
					operation.operation_rate = frappe.db.get_value("Workstation", operation.workstation, "per_qty_rate")
				else:
					operation.operation_rate = frappe.db.get_value("Workstation", operation.workstation, "hour_rate")
			
			if operation.calculation_type == "Per Qty":
				operation.operating_cost = flt(operation.operation_rate)
			else:
				operation.operating_cost = flt(
					flt(operation.operation_rate) * flt(operation.time_in_mins) / 60,
					operation.precision("operating_cost"),
				)

	def set_routing_id(self):
		sequence_id = 0
		for row in self.operations:
			if not row.sequence_id:
				row.sequence_id = sequence_id + 1
			elif sequence_id and row.sequence_id and cint(sequence_id) > cint(row.sequence_id):
				frappe.throw(
					_("At row #{0}: the sequence id {1} cannot be less than previous row sequence id {2}").format(
						row.idx, row.sequence_id, sequence_id
					)
				)

			sequence_id = row.sequence_id
