import frappe
from frappe.utils import flt,cint,getdate
from erpnext.smart_fm.report.utility_report.utility_report import get_last_meter_data
from datetime import datetime
from dateutil.relativedelta import relativedelta
from dateutil import rrule

def execute(filters={}):
	return Report(filters).run()

"""
make report:
Column = Months
Row = List Utility
Group by:
- Utility
- Type of Meter

Filters:
- Year
- Group By
- Type of Meter
- Utility
- Location

Chart is from 1 month to X Month
Value is from last Meter Reading from the Month from 1 utility

The problem:
Very Utility cannot be sum!
"""


class Report:
	def __init__(self, filters):
		self.filters = filters
		self.columns = []
		self.data = []
		self.chart = []
		self.chart_label = []

	def setup_conditions(self):
		self.conditions = []
		if self.filters.group_by == "Utility":
			self.key_id = "meter_id"
		else:
			self.key_id = "type_of_meter"

	def get_columns(self):
		self.columns = []

		if self.filters.get("group_by") == "Utility":
			self.columns += [
				{ "fieldname": "meter_id" ,         "label": "Meter ID",        "fieldtype": "Link",    "width": 120, "options": "Utility"},
			]

		self.columns += [
            { "fieldname": "type_of_meter" ,    "label": "Type of Meter",   "fieldtype": "Data",    "width": 150, "options": ""},
            { "fieldname": "meter_location" ,   "label": "Meter Location",  "fieldtype": "Data",    "width": 150, "options": ""}
		]

		for d in self.column_date:
			self.columns.append({
				"label": self.get_column_label(d),
				"fieldname": self.get_column_key(d),
				"fieldtype": "Float",
				"precision": 2,
				"width": 120
			})

	def get_column_key(self, date):
		return frappe.scrub(self.get_column_label(date))

	def get_column_label (self, date):
		return date.strftime("%b %y")
		
	def get_periode(self):
		# for d in 
		start_date = getdate(self.filters.from_date).replace(day=1)
		end_date = getdate(self.filters.to_date).replace(day=1)
		self.periode = {}
		self.column_date = []
		for dt in rrule.rrule(rrule.MONTHLY, dtstart=start_date, until=end_date):
			name = self.get_column_label(dt)
			nd = dt + relativedelta(months=1) - relativedelta(days=1)
			self.periode[name] = [dt, nd]
			self.column_date.append(dt)

	def get_data(self):
		self.raw_data = []
		self.data_dict = {}
		filters = {}
		if self.filters.get("type_of_meter"):
			filters['type_of_meter'] = self.filters.type_of_meter

		if self.filters.get("group_by") == "Utility":

			if self.filters.get("utility"):
				filters['utility'] = self.filters.utility
			if self.filters.get("meter_location"):
				filters['meter_location'] = self.filters.meter_location

		for key, dates in self.periode.items():
			last_date = dates[1]
			filters.update({"reading_date": last_date})
			data = get_last_meter_data(filters)
			print(filters)
			print(109, data)
			for d in data:
				key_name = d.get(self.key_id)
				if key_name not in self.data_dict:
					self.data_dict[key_name] = d
					row = d
				else:
					row = self.data_dict[key_name]

				key_month = self.get_column_key(dates[0])
				value = d.current_reading

				if self.filters.get("group_by") == "Utility":
					row[key_month] = value
				else:
					if key_month not in row:
						row[key_month] = value
					else:
						row[key_month] += value

		
		print(self.data_dict)

	def process_data(self):
		self.data = []
		for key, d in self.data_dict.items():
			prev_value = 0
			for dt in self.column_date:
				key_date = self.get_column_key(dt)
				if self.filters.get("show_by") == "Growth":
					if not prev_value:
						prev_value = cint(d.get(key_date))
						
					if key_date not in d:
						continue

					d[key_date] -= prev_value
					prev_value += d[key_date]

			self.data.append(d)

	def get_chart(self):
		labels = []
		datasets = []

		for key, d in self.data_dict.items():
			
			values = []
			for dt in self.column_date:
				key_date = self.get_column_key(dt)
				label = self.get_column_label(dt)
				if label not in labels:
					labels.append(label)

				value = d.get(key_date)
				values.append(value)

			datasets.append({
				"name": key,
				"values": values
			})

		self.chart = {
			"data": {
				"labels": labels, 
				"datasets": datasets,
			}, 
			"colors": ['yellow', "orange"],
			"type": "line"
		}

	def run(self):
		self.setup_conditions()
		self.get_periode()
		self.get_columns()
		self.get_data()
		self.process_data()
		self.get_chart()

		return self.columns, self.data, None, self.chart