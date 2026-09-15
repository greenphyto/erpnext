import frappe


@frappe.whitelist()
def get_last_email_default(doctype, docname):
	# return {
	# 	"recipients":"riky@gmail.com",
	# 	"cc":"riky@gmail.com",
	# 	"bcc":"riky@greenphyto.com",
	# }
	com_db = frappe.qb.DocType("Communication")
	doc_db = frappe.qb.DocType(doctype)

	party_type = ""
	if doctype in ['Material Request','Purchase Order', 'Purchase Receipt', 'Purchase Invoice']:
		party_type = "supplier"
	elif doctype in ['Quotation', 'Sales Order', 'Sales Invoice', 'Delivery Note']:
		party_type = "customer"

	party_name = frappe.get_value(doctype, docname, party_type)
	user = frappe.session.user
	if user == "Administrator":
		user = frappe.get_value(doctype, docname, "modified_by")


	data = (
		frappe.qb.from_(com_db)
		.join(doc_db)
		.on(doc_db.name == com_db.reference_name)
		.select(
			com_db.cc,
			com_db.recipients,
			com_db.bcc,
			com_db.email_template
		)
		.where(
			(com_db.reference_doctype == doctype) &
			(com_db.sender == user) &
			(doc_db[party_type] == party_name)
		)
		.orderby(doc_db.transaction_date, order=frappe.qb.desc)  # DESC untuk terbaru
		.limit(1)
	).run(as_dict=1, debug=0)

	if data:
		data = data[0]
		return {
			"sender":user,
			"recipients": data.recipients or "",
			"cc": data.cc or "",
			"bcc": data.bcc or "",
			"email_template": data.email_template or ""
		}

	return {}