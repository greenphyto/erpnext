import frappe
from frappe.utils import flt,cint,getdate

def execute(filters={}):
	return Report(filters).run()

"""
This is repoprt to count any Issued and Start task
from listed docuemnt only
"""
class Report:
	def __init__(self, filters):
		self.filters = filters
		self.columns = []
		self.data = []
		self.chart = []
		self.list_type = [
			"Maintenance Request",
			"Access Request",
			"Inspection Checklist",
			"Vendor Registration",
			"Key Control",
			"Work Order"
		]

	def setup_conditions(self):
		self.conditions = []

	def get_columns(self):
		self.columns = [
			{ "fieldname": "source" , "label": "Source", "fieldtype": "Data", "width": 200, "options": ""},
			{ "fieldname": "issued" , "label": "Issued", "fieldtype": "Int", "width": 100, "options": ""},
			{ "fieldname": "started" , "label": "Started", "fieldtype": "Int", "width": 100, "options": ""}
		]

	def get_data(self):
		pass


	def get_data_detail(self, doctype):
		if not frappe.get_meta(doctype).get_field("workflow_state"):
			return
		
		data = frappe.db.sql("""
				SELECT 
					COUNT(name) AS cnt, workflow_state as state
				FROM
					`tab{}`
				WHERE
					workflow_state IN ('Issued' , 'Started')
				GROUP BY workflow_state
			""".format(doctype), as_dict=1, debug=0)
		dt = {
			"source": doctype
		}
		for d in data:
			dt[ frappe.scrub(d.state) ] = d.cnt

		return dt


	def process_data(self):
		self.data = []
		for doctype in self.list_type:
			dt = self.get_data_detail(doctype)
			if dt:
				self.data.append(dt)

	def get_chart(self):
		labels = []
		datasets = []
		data_dict = {}
		list_type = ['Issued', 'Started']

		for t in list_type:
			data_dict[t] = []

		for d in self.data:
			labels.append(d['source'])
			for t in list_type:
				typ = frappe.scrub(t)
				val = d.get(typ)
				if val:
					data_dict[t].append(d[typ])
				else:
					data_dict[t].append(0)

		
		for typ, d in data_dict.items():
			datasets.append({
				"name": typ,
				"values": d
			})

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