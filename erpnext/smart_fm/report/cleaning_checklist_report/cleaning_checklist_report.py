# Copyright (c) 2013, erfidner.id and contributors
# For license information, please see license.txt


import frappe

def execute(filters=None):
	return Report(filters).execute()

class Report():
	def __init__(self, filters):
		self.filters = filters

	def setup_condition(self):
		self.cond = ""

	def setup_column(self):
		self.columns = [
			{"fieldname": "date", 				"label": "Date", 			"fieldtype": "Date", "width":120, "options":""},
			{"fieldname": "cleaned_by", 		"label": "Cleaned By", 		"fieldtype": "Data", "width":120, "options":""},
			{"fieldname": "location", 			"label": "Location", 		"fieldtype": "Data", "width":150, "options":""},
			{"fieldname": "area", 				"label": "Area", 			"fieldtype": "Link", "width":120, "options":"Cleaning Area"},
			{"fieldname": "general_cleaning", 	"label": "General Cleaning", "fieldtype": "Check", "width":150, "options":""},
			{"fieldname": "regulary_inspection", "label": "Regulary Inspection", "fieldtype": "Check", "width":150, "options":""},
			{"fieldname": "remarks", 			"label": "Remarks", 		"fieldtype": "Data", "width":250, "options":""},
		]
	
	def get_data(self):
		self.raw_data = frappe.db.sql("""
			SELECT 
				c.name,
				c.posting_date AS date,
				ci.area,
				c.cleaned_by,
				ci.general_cleaning,
				ci.regulary_inspection,
				c.remarks,
				CASE 
					WHEN ci.parentfield = 'level_1_area' THEN 'Level 1'
					WHEN ci.parentfield = 'level_2_area' THEN 'Level 2'
					WHEN ci.parentfield = 'level_3_area' THEN 'Level 3'
					WHEN ci.parentfield = 'level_4_area' THEN 'Level 4'
					ELSE 'Level 5'
				END AS location
			FROM
				`tabCleaning Checklist Items` ci
					LEFT JOIN
				`tabCleaning Checklist` c ON c.name = ci.parent
			ORDER BY c.posting_date DESC , c.name , ci.parentfield , ci.idx
		""".format(self.cond), self.filters, as_dict=1)
	
	def process_data(self):
		self.data = self.raw_data
		cur_name = ""
		cur_loc = ""
		for d in self.data:
			if not cur_name or cur_name != d.name:
				cur_name = d.name
			else:
				d.date = ""
				d.cleaned_by = ""
				d.remarks = ""
			
			if not cur_loc or cur_loc != (d.name, d.location):
				cur_loc = (d.name, d.location)
			else:
				d.location = ""

	def execute(self):
		self.setup_condition()
		self.setup_column()
		self.get_data()
		self.process_data()

		return self.columns, self.data