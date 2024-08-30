# Copyright (c) 2013, erfidner.id and contributors
# For license information, please see license.txt

import frappe, json
from frappe.utils import flt, cint, getdate, add_days
from six import string_types


def execute(filters=None):
	report = Report(filters)
	return report.run()

class Report:
	def __init__(self, filters):
		self.filters = filters
		self.data = []
		self.columns = []
		self.condition = ""
		self.params = []
		self.quiz_field = [
			"q1", 'q2', 'q3', 'q4', 'q5', 
			'q6', 'q7', 'q8', 'q9', 'q11', 
			'q12', 'q13', 'q10'
		]
		self.quiz_map = {}
		self.meta = frappe.get_meta("Building Environment Feedback")

	def get_columns(self):
		self.columns = [
			{"fieldname": "question", 	"label": "Question", 	"fieldtype": "Data", 	"width":500, "options": ""},
			{"fieldname": "percent", 	"label": "% Percent", 	"fieldtype": "Data", 	"width":100, "precision":2, "options": ""},
			{"fieldname": "count", 		"label": "Count", 		"fieldtype": "Int", 	"width":100, "precision":2, "options": ""},
		]

	def set_filter(self):
		from_date = getdate(self.filters.from_date or "2000-01-01") 
		to_date = add_days(getdate(self.filters.to_date), 1)
		self.condition = " and posting_date between %s and %s "
		self.params = [from_date, to_date]

	def get_raw_data(self):
		self.data
		cur_label = ""
		idx = 0
		for field in self.quiz_field:
			idx += 1
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

				quiz_title = "{}. {}".format(idx,label)

				self.data.append({
					"indent":0,
					"is_group":1,
					"question": quiz_title
				})

				self.quiz_map[field] = []

				cur_label = label

			# for optioned question
			if df.options:
				all_opts = df.options.split("\n")
				all_opts.remove("")
				all_opts.append("")
				all_opts.append("Total")

				data = frappe.db.sql("""
					SELECT 
						count({0}) as count,
						{0} as question
					FROM
						`tabBuilding Environment Feedback`
					where 
						docstatus != 2
						{1}
					group by {0}
						""".format(field, self.condition), self.params, as_dict=1, debug=0)
				
			else:
				all_opts = ["Answered", "None", "Total"]
				data = frappe.db.sql("""
					SELECT 
						count(if(isnull({0}), "None", "Answered")) as count,
						if(isnull({0}), "None", "Answered") as question
					FROM
						`tabBuilding Environment Feedback`
					where 
						docstatus != 2
						{1}
					group by if(isnull({0}), "None", "Answered")
						 """.format(field, self.condition),self.params, as_dict=1, debug=0)
				msg_field = field

			answer_map = {}
			total = 0
			for x in data:
				total += flt(x.get("count"))
				answer_map[x.question] = x

			for opts in all_opts:
				d = answer_map.get(opts)
				percent_view = "0%"
				percent=0
				count = 0
				if d:
					question = d.question or "None"
					count = cint(d.get("count"))
					percent = flt(d.count) / total * 100
					percent_view = "{:.2f}%".format(round(percent, 2))
				else:
					question = opts or "None"
					if opts == "Total":
						count = total
						percent = 100
						percent_view = "{:.2f}%".format(100)

				self.data.append({
					"indent":1,
					"question":question,
					"percent":percent_view,
					"count": count
				})

				self.quiz_map[field].append({
					'question':question,
					'percent': flt(percent,2)
				})
			
			if msg_field:
				msg_list = get_message_list(self.filters, msg_field)
				if self.filters.show_all_messages:
					self.data.append({
						"indent":1,
						"question":"<b>Messages:</b>",
					})
					for d in msg_list.get("messages"):
						person = d['full_name'] or "Anonim"
						msg = f"- <i>{ person }</i>: {d['text']}"
						for i,piece in enumerate(splitter(15, msg)):
							if i > 0:
								piece = "&nbsp;&nbsp;&nbsp;"+piece
							self.data.append({
								"indent":1,
								"question":piece,
							})
				else:
					self.data.append({"question":"Button", "indent":1, "msg_field":msg_field, "msg_list":msg_list})


	def process_data(self):
		pass

	def get_chart(self):
		# print("result", self.quiz_map)
		labels = []
		values = []
		select_quiz = self.filters.filter_chart or "q1"
		data = self.quiz_map[select_quiz]
		sorted_data = sorted(data, key=lambda x: x['percent'], reverse=True)
		for d in sorted_data:
			if d["question"] != "Total" and d['percent']:
					labels.append(d['question'])
					values.append(d['percent'])
		
		df = self.meta.get_field(select_quiz)
		label = f"{df.label}"

		chart_data = {
			"labels": labels,
			"datasets": [
				{
					"values": values
				}
			]
		}

		self.charts = {
			"data": chart_data,
			"type": "donut",
			"height": 300,
			"title": label,
			"colors": ["#0f4b25", "#007BFF", "#FFC107", "#FF8A3D", "#d93232", "#828282"],
		}


	def run(self):
		self.set_filter()
		self.get_columns()
		self.get_raw_data()
		self.process_data()
		self.get_chart()

		return self.columns, self.data, None, self.charts
	
def splitter(n, s):
    pieces = s.split()
    return (" ".join(pieces[i:i+n]) for i in range(0, len(pieces), n))

@frappe.whitelist()
def get_message_list(filters, field):
	if isinstance(filters, string_types):
		filters = json.loads(filters)

	meta = frappe.get_meta("Building Environment Feedback")
	from_date = getdate(filters.get('from_date') or "2000-01-01") 
	to_date = add_days(getdate(filters.get('to_date')), 1)
	condition = {"posting_date":['between', [from_date, to_date]]}
	condition[field] = ['not in', ['', None]]
	
	msg = frappe.db.get_list('Building Environment Feedback', condition, ["{} as text".format(field), "full_name", "email_address"], debug=0)
	field = meta.get_field(field.replace("_detail", ""))
	data = {
		"question":field.label,
		"messages":msg,
		"total":len(msg)
	}
	return data