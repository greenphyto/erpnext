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
			"Incident Report", 
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
			{ "fieldname": "source" , "label": "Source", "fieldtype": "Data", "width": 100, "options": ""},
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
			""".format(doctype), as_dict=1, debug=1)
		dt = {
			"source": doctype
		}
		for d in data:
			dt[d.state] = d.cnt

		return dt


	def process_data(self):
		self.data = []
		for doctype in self.list_type:
			dt = self.get_data_detail(doctype)
			if dt:
				self.data.append(dt)

	def get_chart(self):
		pass

	def run(self):
		self.setup_conditions()
		self.get_columns()
		self.get_data()
		self.process_data()
		self.get_chart()

		return self.columns, self.data, self.chart