from frappe import _
def get_data():
	return {
		"docstatus": 1,
		"fieldname": "request_no",
		"transactions": [
			{"label": _("Salad Ingredients"), "items": ["Work Order"]},
			{"label": _("Salad Product"), "items": ["Stock Entry"]},
		],
		"internal_links": {
			"Stock Entry": ["items", "stock_entry"],
			"Work Order": ["salad_items", "work_order"],
		}
	}
