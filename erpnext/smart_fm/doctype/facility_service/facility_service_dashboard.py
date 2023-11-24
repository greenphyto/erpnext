from frappe import _


def get_data():
	return {
		"fieldname": "service",
		"transactions": [
			{"label": _("Reservation"), "items": [
				"Facilities Service Reservation"
			]},
		]
	}
