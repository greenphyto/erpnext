from frappe import _


def get_data():
	return {
		"fieldname": "payment_approval",
		"non_standard_fieldnames": {
			"Journal Entry": "reference_detail_no",
		},
		"transactions": [
			{"label": _("Payment"), "items": ["Payment Entry"]},
			{"label": _("Charges"), "items": ["Journal Entry"]},
		],
	}
