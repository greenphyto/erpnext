from frappe import _


def get_data():
	return {
		"fieldname": "consignment_order",
		"internal_links": {
			"Consignment Request": "consignment_request",
		},
		"transactions": [
			{
				"label": _("Reference"),
				"items": ["Consignment Request"],
			},
		],
	}
