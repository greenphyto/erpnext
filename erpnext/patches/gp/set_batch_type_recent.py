import frappe

MALAYSIA_COMPANY = "Greenphyto Tech Sdn Bhd"


def execute():
	set_batch_type_on_recent_batches()


def classify_work_order(request_no):
	"""Return the batch_type for a work order based on its linked requests.

	- Export (MY): any linked Request's proposed_customer represents the
	  Malaysia company (Greenphyto Tech Sdn Bhd).
	- No Pack: the work order serves more than one request.
	- Default: single request and not Malaysia.
	"""
	if not request_no:
		return "Default"

	requests = [r.strip() for r in request_no.replace(" ", "").split(",") if r.strip()]
	if not requests:
		return "Default"

	malaysia = frappe.db.sql(
		"""
		SELECT COUNT(*)
		FROM `tabRequest` req
			INNER JOIN `tabCustomer` cust ON cust.name = req.proposed_customer
		WHERE req.name IN %(requests)s
			AND cust.represents_company = %(company)s
		""",
		{"requests": requests, "company": MALAYSIA_COMPANY},
	)[0][0]

	if malaysia:
		return "Export"

	if len(requests) > 1:
		return "No Pack"

	return "Default"


def set_batch_type_on_recent_batches():
	"""Classify Batch.batch_type on the 100 most recently created batches.

	Each batch is traced to its source work order via the Stock Entry it was
	created from (Batch.reference_doctype = "Stock Entry"), then classified
	as Default / Export (MY) / No Pack based on the work order's requests.
	"""
	print("Classifying batch_type on 100 most recent Batch records...")

	batches = frappe.get_all(
		"Batch",
		fields=["name", "reference_doctype", "reference_name"],
		order_by="creation desc",
		limit=100,
	)

	if not batches:
		print("No batches found.")
		return

	counts = {"Default": 0, "Export": 0, "No Pack": 0}
	for b in batches:
		work_order = None
		if b.reference_doctype == "Stock Entry" and b.reference_name:
			work_order = frappe.db.get_value("Stock Entry", b.reference_name, "work_order")

		request_no = None
		if work_order:
			request_no = frappe.db.get_value("Work Order", work_order, "request_no")

		batch_type = classify_work_order(request_no)
		counts[batch_type] += 1

		frappe.db.set_value("Batch", b.name, "batch_type", batch_type, update_modified=False)

	frappe.db.commit()
	print(
		"batch_type set on {0} batches: Default={1}, Export(MY)={2}, No Pack={3}".format(
			len(batches), counts["Default"], counts["Export"], counts["No Pack"]
		)
	)
