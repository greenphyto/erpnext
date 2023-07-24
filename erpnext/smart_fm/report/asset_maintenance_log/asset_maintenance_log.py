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
  
		for f in ['item_code', 'maintenance_type', 'periodicity', 'maintenance_status']:
			if self.filters.get(f):
				self.conditions += " and aml."+f+" = %("+f+")s"
    
		if self.filters.get("user"):
			self.conditions += " and u.name = %(assign_to)s "

		if self.filters.get("task_name"):
			self.filters.task_name = "%"+self.filters.task_name+"%"
			self.conditions += " and aml.task_name like %(task_name)s "

	def get_columns(self):
		self.columns = [
			{ "fieldname": "task_name" , 			"label": "Task Name", 			"fieldtype": "Data", "width": 180, "options": ""},
			{ "fieldname": "todo" , 				"label": "ToDo", 				"fieldtype": "Link", "width": 120, "options": "ToDo"},
			{ "fieldname": "maintenance_type" , 	"label": "Maintenance Type", 	"fieldtype": "Data", "width": 180, "options": ""},
			{ "fieldname": "periodicity" , 			"label": "Periodicity", 		"fieldtype": "Data", "width": 150, "options": ""},
			{ "fieldname": "maintenance_status" , 	"label": "Status", 				"fieldtype": "Data", "width": 180, "options": ""},
			{ "fieldname": "assign_to_name" , 		"label": "Assign To", 			"fieldtype": "Link", "width": 150, "options": "User"},
			{ "fieldname": "due_date" , 			"label": "Due Date", 			"fieldtype": "Date", "width": 120, "options": ""},
			{ "fieldname": "completion_date" , 		"label": "Comp. Date", 	"fieldtype": "Date", "width": 120, "options": ""},
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
				u.name as assign_to,
				aml.due_date,
				aml.completion_date
			from 
				`tabAsset Maintenance Log` aml
			left join 
				tabUser as u on u.full_name = aml.assign_to_name
			left join 
				tabToDo as t on t.additional_reference = aml.name
			where 
				aml.docstatus != 2
			{}
			order by
				aml.item_code, aml.due_date
		""".format(self.conditions), self.filters, as_dict=1, debug=0)

	def process_data(self):
		self.data = []
		item_code = []
		for d in self.raw_data:
			if d.item_code not in item_code:
				if item_code:
					self.data.append({})

				item_code.append(d.item_code)

				self.data.append({
					"task_name": d.item_code,
					"indent":0,
					"bold":1
				})
			
			d.indent = 1
			self.data.append(d)
			
	def get_chart(self):
		pass

	def run(self):
		self.setup_conditions()
		self.get_columns()
		self.get_data()
		self.process_data()
		self.get_chart()

		return self.columns, self.data, self.chart