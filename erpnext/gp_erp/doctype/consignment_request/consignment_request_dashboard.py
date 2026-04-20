from frappe import _


def get_data():
	return {
		"fieldname": "consignment_request",
		"non_standard_fieldnames": {
			"Delivery Note": "against_consignment_request",
		},
		"transactions": [
			{
				"label": _("Fulfillment"),
				"items": ["Sales Invoice", "Delivery Note"],
			},
			{"label": _("Stock"), "items": ["Stock Entry"]},
		],
	}
