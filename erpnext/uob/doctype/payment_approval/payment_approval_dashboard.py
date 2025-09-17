from frappe import _


def get_data():
	return {
		"fieldname": "payment_approval",
		"transactions": [
			{"label": _("Payment"), "items": ["Payment Entry"]},
		],
	}
