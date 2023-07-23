import frappe
from frappe.utils import flt,cint,getdate

def execute(filters):
	return Report(filters).run()


class Report:
	def __init__(self, filters):
		self.filters = filters
		self.columns = []
		self.data = []
		self.chart = []

	def setup_conditions(self):
		self.conditions = ""

	def get_columns(self):
		self.columns = [
			{ "fieldname": "task_name" , 			"label": "Task Name", 			"fieldtype": "Data", "width": 180, "options": ""},
			{ "fieldname": "maintenance_type" , 	"label": "Maintenance Type", 	"fieldtype": "Data", "width": 180, "options": ""},
			{ "fieldname": "periodicity" , 			"label": "Periodicity", 		"fieldtype": "Data", "width": 150, "options": ""},
			{ "fieldname": "maintenance_status" , 	"label": "Status", 				"fieldtype": "Data", "width": 180, "options": ""},
			{ "fieldname": "assign_to_name" , 		"label": "Assign To", 			"fieldtype": "", 	 "width": 150, "options": ""},
			{ "fieldname": "due_date" , 			"label": "Due Date", 			"fieldtype": "Date", "width": 120, "options": ""},
			{ "fieldname": "completion_date" , 		"label": "Completion Date", 	"fieldtype": "Date", "width": 120, "options": ""},
		]

	def get_data(self):
		self.raw_data = frappe.db.sql("""
			select 
				aml.name as log_name,
				aml.asset_maintenance,
				aml.asset_name,
				aml.item_code,
				aml.item_name,
				aml.task_name,
				aml.maintenance_type,
				aml.periodicity,
				aml.maintenance_status,
				aml.assign_to_name,
				aml.due_date,
				aml.completion_date
			from 
				`tabAsset Maintenance Log` aml
			where 
				aml.docstatus != 2
			order by
				aml.due_date
			{}
		""".format(self.conditions), self.filters, as_dict=1)

	def process_data(self):
		self.data = self.raw_data

	def get_chart(self):
		pass

	def run(self):
		self.setup_conditions()
		self.get_columns()
		self.get_data()
		self.process_data()
		self.get_chart()

		return self.columns, self.data, self.chart