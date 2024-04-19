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
		self.conditions = ""
		
		if self.filters.get("from_date") and self.filters.get("to_date"):
			self.conditions += " and creation between %(from_date)s and %(to_date)s "

	def get_columns(self):
		self.columns = [
			{ "fieldname": "type" , "label": "Type", "fieldtype": "Data", "width": 250, "options": "", "precision":2},
			{ "fieldname": "percent" , "label": "Percent", "fieldtype": "Percent", "width": 150, "options": "", "precision":2},
			{ "fieldname": "count" , "label": "Count", "fieldtype": "Int", "width": 150, "options": ""},
		]

	def get_data(self):
		# Get todo
		self.get_todo()

		# Get preventive maintenance
		self.get_preventive_maintenance()

		# Get corrective maintenance
		self.get_corrective_maintenance()

		# Get asset repair
		self.get_asset_repair()
		
	def get_todo(self):
		self.completed_todo_count = frappe.db.sql("""
			SELECT 
				COUNT(name) as count
			FROM
				`tabToDo`
			WHERE
				status = 'Completed';
		""".format(self.conditions), self.filters, as_dict=1)[0]

		self.total_todo_count = frappe.db.sql("""
			SELECT 
				COUNT(name) as count
			FROM
				`tabToDo`;
		""".format(self.conditions), self.filters, as_dict=1)[0]


		print(self.completed_todo_count)
		print(self.total_todo_count)
		
	def get_preventive_maintenance(self):
		self.completed_pm_count = frappe.db.sql("""
			SELECT 
				COUNT(name) as count
			FROM
				`tabAsset Maintenance Log`
			WHERE
				maintenance_status = 'Completed' AND
				maintenance_type = 'Preventive Maintenance';
		""".format(self.conditions), self.filters, as_dict=1)[0]

		self.total_pm_count = frappe.db.sql("""
			SELECT 
				COUNT(name) as count
			FROM
				`tabAsset Maintenance Log`
			WHERE
				maintenance_type = 'Preventive Maintenance';
		""".format(self.conditions), self.filters, as_dict=1)[0]


		print(self.completed_pm_count)
		print(self.total_pm_count)
		
	def get_corrective_maintenance(self):
		self.completed_cm_count = frappe.db.sql("""
			SELECT 
				COUNT(name) as count
			FROM
				`tabAsset Maintenance Log`
			WHERE
				maintenance_status = 'Completed' AND
				maintenance_type = 'Corrective Maintenance';
		""".format(self.conditions), self.filters, as_dict=1)[0]

		self.total_cm_count = frappe.db.sql("""
			SELECT 
				COUNT(name) as count
			FROM
				`tabAsset Maintenance Log`
			WHERE
				maintenance_type = 'Corrective Maintenance';
		""".format(self.conditions), self.filters, as_dict=1)[0]


		print(self.completed_cm_count)
		print(self.total_cm_count)
		
	def get_asset_repair(self):
		self.asset_repair = frappe.db.sql("""
			select 
				ar.name as log_name,
				ar.asset,
				ar.asset_name,
				ar.failure_date,
				ar.completion_date,
				ar.downtime
			from 
				`tabAsset Repair` ar
			where 
				ar.docstatus = 1;
		""".format(self.conditions), self.filters, as_dict=1, debug=0)


		print(self.asset_repair)

	def process_data(self):
		if self.total_todo_count.count != 0:
			self.data.append({
				"type": "Work Order Closure Completion Rate",
				"bold": 1,
				"count": self.completed_todo_count.count/self.total_todo_count.count,
				"percent": self.completed_todo_count.count/self.total_todo_count.count*100
			})
		if self.total_pm_count.count != 0:
			self.data.append({
				"type": "On Time Preventive Maintenace",
				"bold": 1,
				"count": self.completed_pm_count.count/self.total_pm_count.count,
				"percent": self.completed_pm_count.count/self.total_pm_count.count*100
			})
		self.data.append({
			"type": "Corrective Maintenance - Follow WO Creation Corrective maintenance = repair on Smart FM",
			"bold": 1,
			# "count": self.completed_todo_count/self.total_todo_count,
			# "percent": self.completed_todo_count/self.total_todo_count*100
		})
		self.data.append({
			"type": "Mean Time To Repair (MTTR)",
			"bold": 1,
			# "count": self.completed_todo_count/self.total_todo_count,
			# "percent": self.completed_todo_count/self.total_todo_count*100
		})
			
	def get_chart(self):
		pass

	def run(self):
		self.setup_conditions()
		self.get_columns()
		self.get_data()
		self.process_data()
		self.get_chart()

		return self.columns, self.data, self.chart