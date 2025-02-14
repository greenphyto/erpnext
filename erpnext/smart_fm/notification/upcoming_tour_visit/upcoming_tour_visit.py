import frappe
from frappe.utils import today, format_date, format_time

def get_context(context):
	# do your magic here
	context.update({
		"end_support": frappe.render_template("erpnext/templates/end_support.html", {}),
		"date":format_date(today())
	})
	return context
	