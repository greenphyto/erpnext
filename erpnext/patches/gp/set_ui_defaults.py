import frappe


def execute():
	frappe.db.set_single_value("System Settings", "disable_change_log_notification", 1)
	frappe.db.set_single_value("Accounts Settings", "show_balance_in_coa", 1)
