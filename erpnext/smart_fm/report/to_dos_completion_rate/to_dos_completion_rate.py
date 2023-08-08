import frappe
from frappe.utils import flt,cint,getdate

def execute(filters={}):
	return Report(filters).run()


class Report:
	def __init__(self, filters):
		self.filters = filters
		self.columns = []
		self.data = []
		self.chart = []

	def setup_conditions(self):
		self.conditions = ""
		
		if self.filters.get("from_date") and self.filters.get("to_date"):
			self.conditions += " and creation between %(from_date)s and %(to_date)s "


	def get_columns(self):
		self.columns = [
			{ "fieldname": "type" , "label": "Type", "fieldtype": "Data", "width": 150, "options": "", "precision":2},
			{ "fieldname": "percent" , "label": "Percent", "fieldtype": "Percent", "width": 150, "options": "", "precision":2},
			{ "fieldname": "count" , "label": "Count", "fieldtype": "Int", "width": 150, "options": ""},
		]

	def get_data(self):
		self.raw_data = frappe.db.sql("""
			SELECT 
				COUNT(name) AS count, status as type
			FROM
				`tabToDo`
			WHERE
				status != 'Cancelled'
				{}
			GROUP BY status;
		""".format(self.conditions), self.filters, as_dict=1)

	def process_data(self):
		self.data = self.raw_data
		total = sum([ x.count for x in self.raw_data ])
		for d in self.data:
			d.percent = d.count/total*100
		
		self.data.append({
			"type": "Total",
			"bold": 1,
			"count": total,
			"percent": 100
		})

	def get_chart(self):
		labels = []
		datasets = []
	
		self.chart = {
			"data": {
				"labels": labels, 
				"datasets": datasets,
			}, 
			"colors": ['yellow', "orange"],
			"type": "bar"
		}

	def run(self):
		self.setup_conditions()
		self.get_columns()
		self.get_data()
		self.process_data()
		self.get_chart()

		return self.columns, self.data, None, self.chart