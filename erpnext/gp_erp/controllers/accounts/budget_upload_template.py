import frappe
from frappe import _


@frappe.whitelist()
def download_budget_template(company=None):
	from frappe.utils.xlsxutils import make_xlsx

	months = [
		"January", "February", "March", "April", "May", "June",
		"July", "August", "September", "October", "November", "December",
	]

	headers = [_("Cost Center"), _("Account")] + [_(month) for month in months]

	data = [headers]

	if company:
		sample_cost_center = frappe.db.get_value(
			"Cost Center",
			filters={"company": company, "is_group": 0, "disabled": 0},
			pluck="name",
		) or "Main - " + company

		sample_accounts = frappe.db.get_all(
			"Account",
			filters={"company": company, "report_type": "Profit and Loss", "is_group": 0, "disabled": 0},
			fields=["name"],
			limit=3,
		)

		for acc in sample_accounts:
			row = [sample_cost_center, acc.name] + [0] * 12
			data.append(row)
	else:
		data.append(["Main - Company", "Salary - Company"] + [0] * 12)
		data.append(["Main - Company", "Rent - Company"] + [0] * 12)
		data.append(["Operations - Company", "Utilities - Company"] + [0] * 12)

	xlsx_file = make_xlsx(data, "Budget Upload Template")

	frappe.response["filename"] = "budget_upload_template.xlsx"
	frappe.response["filecontent"] = xlsx_file.getvalue()
	frappe.response["type"] = "binary"
