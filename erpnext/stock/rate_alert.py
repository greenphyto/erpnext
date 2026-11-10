import json

import frappe
from frappe import _
from frappe.query_builder.functions import CombineDatetime, Sum
from frappe.utils import flt, get_link_to_form


RATE_THRESHOLD = 0.25
MIN_PREV_RATE = 0.01


def check_rate_anomaly(doc, method):
	items_to_check = _get_stock_items(doc)
	if not items_to_check:
		return

	anomalies = []
	for item_code, warehouse, current_rate, batch_no in items_to_check:
		if not current_rate:
			continue

		prev_rate = _get_prev_rate(doc, item_code, warehouse, batch_no)
		if not prev_rate or prev_rate < MIN_PREV_RATE:
			continue

		diff_pct = (current_rate - prev_rate) / prev_rate
		if abs(diff_pct) > RATE_THRESHOLD:
			anomalies.append({
				"item_code": item_code,
				"warehouse": warehouse,
				"batch_no": batch_no or "",
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
				results.append((d.item_code, d.warehouse, flt(d.incoming_rate), d.get("batch_no")))
			else:
				sle_rate = _get_current_voucher_valuation_rate(
					d.item_code, d.warehouse, doc.doctype, doc.name, d.get("batch_no")
				)
				if sle_rate:
					results.append((d.item_code, d.warehouse, flt(sle_rate), d.get("batch_no")))
	elif doc.doctype == "Stock Entry":
		for d in doc.get("items") or []:
			if not _is_product_item(d.item_code):
				continue
			batch_no = _get_batch_no(doc, d)
			if d.s_warehouse and not d.t_warehouse:
				results.append((d.item_code, d.s_warehouse, flt(d.basic_rate), batch_no))
			elif d.t_warehouse and not d.s_warehouse:
				results.append((d.item_code, d.t_warehouse, flt(d.basic_rate), batch_no))
	return results


def _get_batch_no(doc, row):
	if doc.doctype == "Stock Entry":
		return row.get("batch_no") or None
	return None


def _is_product_item(item_code):
	item_group = frappe.get_cached_value("Item", item_code, "item_group")
	return item_group == "Products"


def _get_prev_rate(doc, item_code, warehouse, batch_no):
	if batch_no:
		sle = frappe.qb.DocType("Stock Ledger Entry")
		timestamp_condition = CombineDatetime(sle.posting_date, sle.posting_time) < CombineDatetime(
			doc.posting_date, doc.posting_time
		)
		if doc.creation:
			timestamp_condition |= (
				CombineDatetime(sle.posting_date, sle.posting_time)
				== CombineDatetime(doc.posting_date, doc.posting_time)
			) & (sle.creation < doc.creation)

		batch_details = (
			frappe.qb.from_(sle)
			.select(Sum(sle.stock_value_difference).as_("batch_value"), Sum(sle.actual_qty).as_("batch_qty"))
			.where(
				(sle.item_code == item_code)
				& (sle.warehouse == warehouse)
				& (sle.batch_no == batch_no)
				& (sle.is_cancelled == 0)
				& (sle.actual_qty > 0)
			)
			.where(timestamp_condition)
		).run(as_dict=True)

		if batch_details and batch_details[0].batch_qty:
			return flt(batch_details[0].batch_value / batch_details[0].batch_qty)
	return _get_last_valuation_rate(item_code, warehouse, doc.doctype, doc.name)


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


def _get_current_voucher_valuation_rate(item_code, warehouse, voucher_type, voucher_no, batch_no=None):
	filters = {
		"item_code": item_code,
		"warehouse": warehouse,
		"is_cancelled": 0,
		"voucher_type": voucher_type,
		"voucher_no": voucher_no,
	}
	if batch_no:
		if not frappe.get_meta("Stock Ledger Entry").has_field("batch_no"):
			return 0
		filters["batch_no"] = batch_no

	rate = frappe.db.get_value(
		"Stock Ledger Entry",
		filters,
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
		batch = f", batch {a['batch_no']})" if a["batch_no"] else ")"
		lines.append(
			f"- {a['item_code']} ({a['warehouse']}{batch}: "
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
