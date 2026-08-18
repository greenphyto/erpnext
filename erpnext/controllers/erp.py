import frappe


def rename_purchase_receipt(old_name, new_name):
	pr = frappe.get_doc("Purchase Receipt", old_name)

	if pr.docstatus != 0:
		frappe.throw("Only Draft Purchase Receipt can be renamed")

	frappe.rename_doc("Purchase Receipt", old_name, new_name, force=True)

	child_tables = [
		"Purchase Receipt Item",
		"Pricing Rule Detail",
		"Purchase Receipt Item Supplied",
		"Purchase Taxes and Charges",
	]

	for doctype in child_tables:
		frappe.db.sql(
			"""UPDATE `tab{doctype}` SET parent = %s WHERE parent = %s""".format(doctype=doctype),
			(new_name, old_name),
		)

	print(f"Purchase Receipt renamed from {old_name} to {new_name}")


def rename_purchase_invoice(old_name, new_name):
	pi = frappe.get_doc("Purchase Invoice", old_name)

	if pi.docstatus != 0:
		frappe.throw("Only Draft Purchase Invoice can be renamed")

	frappe.rename_doc("Purchase Invoice", old_name, new_name, force=True)

	child_tables = [
		"Purchase Invoice Item",
		"Pricing Rule Detail",
		"Purchase Receipt Item Supplied",
		"Purchase Taxes and Charges",
		"Purchase Invoice Advance",
		"Payment Schedule",
		"Advance Tax",
		"Tax Withheld Vouchers",
	]

	for doctype in child_tables:
		frappe.db.sql(
			"""UPDATE `tab{doctype}` SET parent = %s WHERE parent = %s""".format(doctype=doctype),
			(new_name, old_name),
		)

	print(f"Purchase Invoice renamed from {old_name} to {new_name}")
