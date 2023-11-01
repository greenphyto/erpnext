# Copyright (c) 2013, erfidner.id and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import flt, cint

def execute(filters=None):
	report = Report(filters)
	return report.run()

class Report:
	def __init__(self, filters):
		self.filters = filters
		self.data = []
		self.columns = []
		self.condition = ""
		self.total_quiz = 10
		self.filters_dict = {}
		self.meta = frappe.get_meta("Building Environment Feedback")

	def get_columns(self):
		self.columns = [
			{"fieldname": "question", 	"label": "Question", 	"fieldtype": "Data", 	"width":500, "options": ""},
			{"fieldname": "percent", 	"label": "% Percent", 	"fieldtype": "Data", 	"width":100, "precision":2, "options": ""},
			{"fieldname": "count", 		"label": "Count", 		"fieldtype": "Int", 	"width":100, "precision":2, "options": ""},
		]

	def set_filter(self):
		pass

	def get_raw_data(self):
		self.data
		cur_label = ""
		for i in range(self.total_quiz):
			field = "q{}".format(i+1)
			df = self.meta.get_field(field)
			if not df:
				continue

			msg_field = None
			field_detail = "{}_detail".format(field)
			if self.meta.get_field(field_detail):
				msg_field = field_detail

			label = df.label
			if not cur_label or cur_label!=label:
				# add new row quiz
				if cur_label:

					self.data.append({})

				self.data.append({
					"indent":0,
					"is_group":1,
					"question": "{}. {}".format(i+1,label)
				})
				cur_label = label

			# for optioned question
			if df.options:
				all_opts = df.options.split("\n")
				all_opts.remove("")
				all_opts.append("")

				data = frappe.db.get_list("Building Environment Feedback", self.filters_dict, "count({0}) as count, {0} as question".format(field), group_by=field, debug=0)
			else:
				all_opts = ["Answered", "None"]
				data = frappe.db.sql("""
					SELECT 
						count(if(isnull({0}), "None", "Answered")) as count,
						if(isnull({0}), "None", "Answered") as question
					FROM
						`tabBuilding Environment Feedback`
					group by if(isnull({0}), "None", "Answered")
						 """.format(field), as_dict=1)
				msg_field = field

			answer_map = {}
			total = 0
			for x in data:
				total += flt(x.get("count"))
				answer_map[x.question] = x

			for opts in all_opts:
				d = answer_map.get(opts)
				percent_view = "0%"
				count = 0
				if d:
					question = d.question or "None"
					count = cint(d.get("count"))
					percent = flt(d.count) / total * 100
					percent_view = "{:.2f}%".format(round(percent, 2))
				else:
					question = opts or "None"

				self.data.append({
					"indent":1,
					"question":question,
					"percent":percent_view,
					"count": count
				})
			
			if msg_field:
				self.data.append({"question":"Button", "indent":1, "msg_field":msg_field})


	def process_data(self):
		pass

	def run(self):
		self.set_filter()
		self.get_columns()
		self.get_raw_data()
		self.process_data()

		return self.columns, self.data
	