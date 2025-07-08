# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from time import strptime
from frappe.utils import getdate

def execute(filters=None):
	return Report(filters).execute()

class Report():
	def __init__(self, filters):
		self.filters = filters

	def setup_condition(self):
		self.cond = ""
		if self.filters.get("year"):
			date = frappe.get_value("Fiscal Year", self.filters.year, "year_start_date")
			self.filters.year = getdate(date).strftime("%Y")
			self.cond += " and YEAR(dn.posting_date) = %(year)s"

		if self.filters.get("view_type") == "Daily":
			if self.filters.get("month"):
				self.filters.month = strptime(self.filters.month,'%B').tm_mon
			else:
				self.filters.month = 1

			self.cond += " and MONTH(dn.posting_date) = %(month)s"

		if self.filters.get("view_type") == "Monthly":
			self.select_period = " DATE_FORMAT(dn.posting_date, '%%Y-%%m') "
			self.group_by = " DATE_FORMAT(dn.posting_date, '%%Y-%%m') "
		else:
			self.select_period = " DATE(dn.posting_date) "
			self.group_by = " DATE(dn.posting_date) "

		if self.filters.get("customer"):
			self.cond += " and dn.customer = %(customer)s "

	def setup_column(self):

		self.columns = [
			{
				"fieldname": "period",
				"label": "Date" if self.filters.get("view_type") == "Daily" else "Month",
				"fieldtype": "Data",
				"width": 100
			},
			{
				"fieldname": "total_delivery",
				"label": "Total Delivery",
				"fieldtype": "Float",
				"width": 130
			},
			{
				"fieldname": "replacement_delivery",
				"label": "Replacement Only",
				"fieldtype": "Float",
				"width": 150
			}
		]
	
	def get_data(self):
		self.raw_data = frappe.db.sql("""
			SELECT
				{} AS period,
				SUM(dni.qty) AS total_delivery,
				SUM(CASE WHEN dn.is_replacement = 1 THEN dni.qty ELSE 0 END) AS replacement_delivery
			FROM
				`tabDelivery Note` AS dn
			JOIN
				`tabDelivery Note Item` AS dni ON dni.parent = dn.name
			WHERE
				dn.docstatus = 1
				{}
			GROUP BY
				{}
			ORDER BY
				period ASC;
		""".format(self.select_period, self.cond, self.group_by), self.filters, as_dict=1, debug=0)
	
	def process_data(self):
		self.data = self.raw_data

	def get_chart(self):
		# Pastikan data urut berdasarkan tanggal
		sorted_data = sorted(self.data, key=lambda x: x.get("period"))

		labels = []
		total_delivery = []
		replacement_delivery = []

		for row in sorted_data:
			if self.filters.get("view_type") == "Daily":
				labels.append(getdate(row.period).day)
			else:
				labels.append(getdate(row.period).strftime("%B"))

			total_delivery.append(row.get("total_delivery", 0))
			replacement_delivery.append(row.get("replacement_delivery", 0))

		self.chart =  {
			"data": {
				"labels": labels,
				"datasets": [
					{
						"name": "Total Delivery",
						"values": total_delivery,
						"chartType": "line"
					},
					{
						"name": "Replacement Delivery",
						"values": replacement_delivery,
						"chartType": "line",
						"color": "green"
					}
				]
			},
			"type": "line",
			"colors": ["#28a745", "#5e64ff"],  # Biru & Hijau
			"axisOptions": {
				"xIsSeries": True
			}
		}

	def execute(self):
		self.setup_condition()
		self.setup_column()
		self.get_data()
		self.process_data()
		self.get_chart()

		return self.columns, self.data, None, self.chart
