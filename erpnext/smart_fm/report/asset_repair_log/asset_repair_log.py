import frappe
from frappe.utils import flt,cint,getdate, add_days

def execute(filters):
	return Report(filters).run()


class Report:
	def __init__(self, filters):
		self.filters = filters
		self.columns = []
		self.data = []
		self.chart = []
		self.conditions = ""

	def setup_conditions(self):
    
		if self.filters.get("asset"):
			self.conditions += " and ar.asset_name = %(asset)s "

		if self.filters.get("description"):
			self.filters.description = "%"+self.filters.description+"%"
			self.conditions += " and ar.description like %(description)s "

		if self.filters.get("failure_date"):
			self.filters.failure_date_next = add_days(self.filters.failure_date, 1)
			self.conditions += " and ar.failure_date between %(failure_date)s and %(failure_date_next)s"

		if self.filters.get("completion_date"):
			self.filters.completion_date_next = add_days(self.filters.completion_date, 1)
			self.conditions += " and ar.completion_date between %(completion_date)s and %(completion_date_next)s"

	def get_columns(self):
		self.columns = [
			{ "fieldname": "asset_name" , 			"label": "Asset", 			"fieldtype": "Data", "width": 120, "options": ""},
			{ "fieldname": "request_id" , 			"label": "Request ID", 		"fieldtype": "Link", "width": 120, "options": "Maintenance Request"},
			{ "fieldname": "todo" , 				"label": "ToDo", 			"fieldtype": "Link", "width": 120, "options": "ToDo"},
            { "fieldname": "repair_status" , 		"label": "Status", 			"fieldtype": "Data", "width": 100, "options": ""},
            { "fieldname": "failure_date" , 		"label": "Failure Time", 	"fieldtype": "Datetime", "width": 180, "options": ""},
            { "fieldname": "completion_date" , 		"label": "Comp. Time", 		"fieldtype": "Datetime", "width": 180, "options": ""},
            { "fieldname": "downtime" , 			"label": "Downtime", 		"fieldtype": "Duration", "width": 100, "options": ""},
            { "fieldname": "repair_cost" , 			"label": "Repair Cost", 	"fieldtype": "Currency", "width": 120, "options": ""},
            { "fieldname": "description" , 			"label": "Description", 	"fieldtype": "Data", "width": 200, "options": ""},
            { "fieldname": "actions_performed" , 	"label": "Actions",			"fieldtype": "Data", "width": 200, "options": ""},
		]

	def get_data(self):
		self.raw_data = frappe.db.sql("""
			select 
				ar.name as log_name,
				ar.asset,
				ar.asset_name,
				ar.failure_date,
				ar.completion_date,
				ar.downtime,
				ar.request_id,
				ar.repair_status,
				ar.repair_cost,
				ar.description,
				ar.actions_performed
			from 
				`tabAsset Repair` ar
			left join 
				tabToDo as t on t.reference_name = ar.name
			where 
				ar.docstatus != 2
			{}
			order by
				ar.failure_date
		""".format(self.conditions), self.filters, as_dict=1, debug=0)

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