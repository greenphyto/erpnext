# Copyright (c) 2013, erfidner.id and contributors
# For license information, please see license.txt

"""
Work Order Operations Detail

Breaks down Stock Entries linked to Work Orders into
four operations based on stock entry types/operation:
- Seeding (Seeding Transfer)
- Transplanting (Transplanting Transfer)
- Harvesting Transfer
- Harvesting Finish (Harvesting Finished Goods)
"""

import frappe
from frappe.utils import getdate

def execute(filters=None):
	return Report(filters).execute()

class Report():
	def __init__(self, filters):
		self.filters = filters

	def setup_condition(self):
		self.cond = ""
		# Optional filters support (even if UI doesn't expose them yet)
		if not self.filters:
			self.filters = frappe._dict()

		self.filters.from_date = getdate(self.filters.get("from_date") or "1900-01-01")
		self.filters.to_date = getdate(self.filters.get("to_date") or "2199-12-31")
		# Default Work Order status to Completed if not provided
		self.filters.wo_status = self.filters.get("wo_status") or "Completed"

		self.cond += " AND se.posting_date BETWEEN %(from_date)s AND %(to_date)s"

		if self.filters.get("work_order"):
			self.cond += " AND se.work_order = %(work_order)s"

		if self.filters.get("product"):
			self.cond += " AND w.production_item = %(product)s"

		if self.filters.get("wo_status"):
			self.cond += " AND w.status = %(wo_status)s"

	def setup_column(self):
		self.columns = [
			{"fieldname": "posting_date", 		"label": "Posting Date", 		"fieldtype": "Date", 		"width": 100},
			{"fieldname": "stock_entry", 		"label": "Stock Entry", 		"fieldtype": "Link", 	"options": "Stock Entry", 	"width": 150},
			{"fieldname": "work_order", 		"label": "Work Order", 		"fieldtype": "Link", 	"options": "Work Order", 	"width": 150},
			{"fieldname": "product", 			"label": "Product", 			"fieldtype": "Link", 	"options": "Item", 		"width": 140},
			{"fieldname": "operation", 		"label": "Operation", 			"fieldtype": "Data", 								"width": 160},
			{"fieldname": "stock_entry_type", 	"label": "Stock Entry Type", 	"fieldtype": "Link", 	"options": "Stock Entry Type", "width": 180},
			{"fieldname": "qty", 				"label": "Qty", 				"fieldtype": "Float", 							"width": 90},
			{"fieldname": "value", 			"label": "Value", 			"fieldtype": "Currency", 					"width": 120},
		]
	
	def get_data(self):
		self.raw_data = frappe.db.sql(
			"""
			SELECT 
				se.posting_date,
				se.name AS stock_entry,
				se.work_order,
				w.production_item AS product,
				CASE 
					WHEN se.purpose = 'Manufacture' AND se.stock_entry_type_view = 'Harvesting Finished Goods' THEN 'Harvesting Finish'
					WHEN se.purpose = 'Material Transfer for Manufacture' AND se.stock_entry_type_view = 'Harvesting Transfer' THEN 'Harvesting Transfer'
					WHEN se.purpose = 'Material Issue' AND se.stock_entry_type_view IN ('Scrap Materials','Waste Materials') THEN 'Scrap Materials'
					ELSE se.operation
				END AS operation,
				se.stock_entry_type_view AS stock_entry_type,
				se.purpose,
				se.fg_completed_qty AS qty,
				CASE 
					WHEN se.purpose = 'Manufacture' THEN COALESCE(se.total_incoming_value, 0)
					WHEN se.purpose = 'Material Issue' AND se.stock_entry_type_view IN ('Scrap Materials','Waste Materials') THEN COALESCE(se.total_outgoing_value, 0)
					ELSE -1 * COALESCE(se.total_outgoing_value, 0)
				END AS value
			FROM `tabStock Entry` se
			LEFT JOIN `tabWork Order` w ON w.name = se.work_order
			WHERE
				se.docstatus = 1
				-- include returns too (e.g., Waste Materials for Work Order uses is_return = 1)
				AND se.work_order IS NOT NULL
				AND se.stock_entry_type_view IN (
					'Seeding Transfer',
					'Transplanting Transfer',
					'Harvesting Transfer',
					'Harvesting Finished Goods',
					'Scrap Materials',
					'Waste Materials'
				)
				{cond}
			ORDER BY 
				w.creation DESC,
				CASE 
					WHEN se.stock_entry_type_view = 'Seeding Transfer' THEN 1
					WHEN se.stock_entry_type_view = 'Transplanting Transfer' THEN 2
					WHEN se.stock_entry_type_view = 'Harvesting Transfer' THEN 3
					WHEN se.stock_entry_type_view IN ('Scrap Materials','Waste Materials') THEN 4
					WHEN se.stock_entry_type_view = 'Harvesting Finished Goods' THEN 5
					ELSE 9
				END,
				se.posting_date,
				se.name
			""".format(cond=self.cond),
			self.filters,
			as_dict=1,
		)
	
	def process_data(self):
		# Group by Work Order, add subtotal rows:
		# - Total Material Transfer (sum of transfers only) right after last transfer
		# - Total (In + Out) net after Manufacture rows (end of WO)
		self.data = []
		last_wo = None
		transfer_sum_qty = 0
		transfer_sum_value = 0
		net_sum_qty = 0
		net_sum_value = 0
		transfer_total_inserted = False

		def append_transfer_total_row(work_order, product):
			if transfer_sum_qty or transfer_sum_value:
				self.data.append({
					"posting_date": None,
					"stock_entry": None,
					"work_order": "",
					"product": "",
					"operation": "Total Material Transfer",
					"stock_entry_type": None,
					"qty": transfer_sum_qty,
					"value": transfer_sum_value,
				})

		def append_net_total_row(work_order, product):
			if net_sum_qty or net_sum_value:
				self.data.append({
					"posting_date": None,
					"stock_entry": None,
					"work_order": "",
					"product": "",
					"operation": "Total (In + Out)",
					"stock_entry_type": None,
					"qty": net_sum_qty,
					"value": net_sum_value,
				})

		for i, d in enumerate(self.raw_data):
			# New Work Order group
			if last_wo is not None and d.work_order != last_wo:
				# Close previous WO: ensure transfer total appended if not yet and there were transfers
				if not transfer_total_inserted:
					append_transfer_total_row(last_wo, last_product)
				# Append net total for previous WO
				append_net_total_row(last_wo, last_product)
				# Empty separator row
				self.data.append({})
				# Reset accumulators for new WO
				transfer_sum_qty = 0
				transfer_sum_value = 0
				net_sum_qty = 0
				net_sum_value = 0
				transfer_total_inserted = False

			# For current row, if it's the first in WO and is Manufacture, we still need to show transfer total as 0? Skip.

			# Continue with current row
			self.data.append(d)
			last_wo = d.work_order
			last_product = d.product
			# accumulate sums
			net_sum_qty += d.qty or 0
			net_sum_value += d.value or 0
			if d.purpose != 'Manufacture':
				transfer_sum_qty += d.qty or 0
				transfer_sum_value += d.value or 0
			else:
				# First Manufacture row triggers insertion of transfer subtotal if not inserted
				if not transfer_total_inserted:
					# Insert transfer subtotal right before this manufacture row
					# Replace the last appended row (which is current row) by inserting subtotal before it
					# Approach: remove last appended row, append subtotal, then re-append current row
					self.data.pop()
					append_transfer_total_row(d.work_order, d.product)
					self.data.append(d)
					transfer_total_inserted = True

		# Close last WO after loop
		if last_wo is not None:
			if not transfer_total_inserted:
				append_transfer_total_row(last_wo, last_product)
			append_net_total_row(last_wo, last_product)

	def execute(self):
		self.setup_condition()
		self.setup_column()
		self.get_data()
		self.process_data()

		return self.columns, self.data
