import frappe


def execute():
	frappe.reload_doc("accounts", "doctype", "bank_account")
