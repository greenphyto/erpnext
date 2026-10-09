# Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe


def switch_to_company_admin(company, change_user=True):
	if frappe.get_default_company() == company:
		return frappe.session.user

	user = frappe.get_value("Company", company, "admin_user") or "Administrator"
	if change_user and user:
		frappe.set_user(user)
	return user
