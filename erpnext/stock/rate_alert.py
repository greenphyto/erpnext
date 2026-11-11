import frappe
from frappe.utils import flt


RATE_THRESHOLD = 0.25
MIN_PREV_RATE = 0.01


def check_rate_anomaly(doc, method):
	items_to_check = _get_stock_items(doc)
	if not items_to_check:
		return

	anomalies = []
	for item_code, warehouse, current_rate in items_to_check:
		if not current_rate:
			continue

		prev_rate = _get_last_valuation_rate(item_code, warehouse, doc.doctype, doc.name)
		if not prev_rate or prev_rate < MIN_PREV_RATE:
			continue

		diff_pct = (current_rate - prev_rate) / prev_rate
		if abs(diff_pct) > RATE_THRESHOLD:
			anomalies.append({
				"item_code": item_code,
				"warehouse": warehouse,
				"prev_rate": flt(prev_rate, 4),
				"current_rate": flt(current_rate, 4),
				"diff_pct": flt(diff_pct * 100, 1),
			})

	if anomalies:
		_send_alert(doc, anomalies)


def _get_stock_items(doc):
	results = []
	if doc.doctype == "Delivery Note":
		for d in doc.get("items") or []:
			if not _is_product_item(d.item_code):
				continue
			if doc.get("is_return"):
				results.append((d.item_code, d.warehouse, flt(d.incoming_rate)))
			else:
				sle_rate = _get_current_voucher_valuation_rate(
					d.item_code, d.warehouse, doc.doctype, doc.name
				)
				if sle_rate:
					results.append((d.item_code, d.warehouse, flt(sle_rate)))
	elif doc.doctype == "Stock Entry":
		for d in doc.get("items") or []:
			if not _is_product_item(d.item_code):
				continue
			if d.s_warehouse and not d.t_warehouse:
				results.append((d.item_code, d.s_warehouse, flt(d.basic_rate)))
			elif d.t_warehouse and not d.s_warehouse:
				results.append((d.item_code, d.t_warehouse, flt(d.basic_rate)))
	return results


def _is_product_item(item_code):
	item_group = frappe.get_cached_value("Item", item_code, "item_group")
	return item_group == "Products"


def _get_last_valuation_rate(item_code, warehouse, voucher_type=None, voucher_no=None):
	filters = {
		"item_code": item_code,
		"warehouse": warehouse,
		"is_cancelled": 0,
	}
	if voucher_no:
		filters["voucher_no"] = ["!=", voucher_no]

	rate = frappe.db.get_value(
		"Stock Ledger Entry",
		filters,
		"valuation_rate",
		order_by="posting_date desc, posting_time desc, creation desc",
	)
	return flt(rate)


def _get_current_voucher_valuation_rate(item_code, warehouse, voucher_type, voucher_no):
	rate = frappe.db.get_value(
		"Stock Ledger Entry",
		{
			"item_code": item_code,
			"warehouse": warehouse,
			"is_cancelled": 0,
			"voucher_type": voucher_type,
			"voucher_no": voucher_no,
		},
		"valuation_rate",
		order_by="posting_date desc, posting_time desc, creation desc",
	)
	return flt(rate)


def _send_alert(doc, anomalies):
	message = _build_message(doc, anomalies)
	try:
		notif = frappe.get_doc("Notification", "Rate increase alert")
		alert_doc = frappe._dict({
			"doctype": doc.doctype,
			"name": doc.name,
			"anomalies": anomalies,
			"message": message,
		})
		notif.send(alert_doc)
	except Exception:
		pass


def _build_message(doc, anomalies):
	doc_link = frappe.utils.get_link_to_form(doc.doctype, doc.name)
	lines = [f"Rate anomaly detected in {doc_link}:"]
	for a in anomalies:
		direction = "higher" if a["diff_pct"] > 0 else "lower"
		lines.append(
			f"- {a['item_code']} ({a['warehouse']}): "
			f"rate {a['current_rate']} is {abs(a['diff_pct'])}% {direction} "
			f"than previous rate {a['prev_rate']}"
		)
	return "<br>".join(lines)


def notify_negative_sle_rate(doc, method=None):
	"""Email the support list when this voucher produced any Stock Ledger Entry
	with a negative valuation rate or negative stock value.

	Wired to on_submit of Delivery Note, Sales Invoice and Stock Entry.
	"""
	negatives = _get_negative_sle(doc)
	if not negatives:
		return

	recipients = _get_support_recipients()
	if not recipients:
		return

	subject = _("Negative stock valuation detected in {0} {1}").format(doc.doctype, doc.name)
	message = _build_negative_sle_message(doc, negatives)
	frappe.sendmail(recipients=recipients, subject=subject, message=message)


def notify_missing_part_number(doc, method=None):
	"""Email the support list when a Work Order's production item is not listed
	in Part Number Settings, or is listed without an account.

	Wired to on_submit of Work Order.
	"""
	item_code = doc.get("production_item")
	if not item_code:
		return

	status = _get_part_number_status(item_code, doc.get("company"))
	if status == "ok":
		return

	recipients = _get_support_recipients()
	if not recipients:
		return

	subject = _("[Alert] Production item missing from Part Number Settings in {0} {1}").format(
		doc.doctype, doc.name
	)
	message = _build_missing_part_number_message(doc, item_code, status)
	frappe.sendmail(recipients=recipients, subject=subject, message=message)


def _get_part_number_status(item_code, company=None):
	filters = {"parenttype": "Part Number Settings", "code": item_code}
	if company:
		filters["parent"] = company
	rows = frappe.db.get_all(
		"Part Number Details",
		filters=filters,
		fields=["account_code"],
	)
	if not rows:
		return "not_listed"
	if not any(r.account_code for r in rows):
		return "no_account"
	return "ok"


def _build_missing_part_number_message(doc, item_code, status):
	doc_link = get_link_to_form(doc.doctype, doc.name)
	item_link = get_link_to_form("Item", item_code)
	company = doc.get("company")
	if company:
		settings_link = get_link_to_form("Part Number Settings", company)
	else:
		settings_link = get_link_to_form("Part Number Settings", "", "Part Number Settings")
	if status == "not_listed":
		reason = _("Production item {0} is not listed in Part Number Settings.").format(item_link)
	else:
		reason = _("Production item {0} is listed in Part Number Settings but has no account.").format(
			item_link
		)
	lines = [
		_("Hi,"),
		_("Work Order {0} was submitted.").format(doc_link),
		reason,
		_("Please update the {0}.").format(settings_link),
	]
	return "<br>".join(lines)


def _get_support_recipients():
	email_candidate = frappe.local.conf.email_support
	if not email_candidate:
		return []
	if isinstance(email_candidate, str):
		try:
			return json.loads(email_candidate)
		except (ValueError, TypeError):
			return [email_candidate]
	return email_candidate


def _get_negative_sle(doc):
	rows = frappe.db.sql(
		"""
		select item_code, warehouse, batch_no, valuation_rate,
			qty_after_transaction, stock_value
		from `tabStock Ledger Entry`
		where voucher_type = %(voucher_type)s
			and voucher_no = %(voucher_no)s
			and is_cancelled = 0
			and (valuation_rate < 0 or stock_value < 0)
		order by posting_date, posting_time, creation
		""",
		{"voucher_type": doc.doctype, "voucher_no": doc.name},
		as_dict=True,
	)
	return rows


def _build_negative_sle_message(doc, negatives):
	doc_link = get_link_to_form(doc.doctype, doc.name)
	lines = [
		_("Hi,"),
		"<br>",
		_("Negative stock valuation was detected after submitting {0}.").format(doc_link),
		"<br>",
		_("Affected Stock Ledger Entries:"),
	]
	for n in negatives:
		batch = f", batch {n.batch_no}" if n.get("batch_no") else ""
		lines.append(
			f"- {n.item_code} ({n.warehouse}{batch}): "
			f"valuation rate {flt(n.valuation_rate, 4)}, "
			f"stock value {flt(n.stock_value, 2)}, "
			f"qty after transaction {flt(n.qty_after_transaction, 2)}"
		)
	lines.append("<br>")
	lines.append(_("Please review the valuation and reconcile if required."))
	return "<br>".join(lines)
