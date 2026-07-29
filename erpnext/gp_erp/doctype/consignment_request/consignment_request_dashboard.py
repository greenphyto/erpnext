from frappe import _


def get_data():
	return {
		"fieldname": "consignment_request",
		"non_standard_fieldnames": {
		},
		"transactions": [
			{
				"label": _("Fulfillment"),
				"items": ["Consignment Order", "Sales Invoice"],
			},
			{"label": _("Stock"), "items": ["Stock Entry"]},
		],
	}
