import frappe


@frappe.whitelist()
def ping_data(data):
	print("GET DATA", data)
	return data