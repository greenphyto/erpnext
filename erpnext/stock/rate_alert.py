import frappe
from frappe.utils import flt


RATE_THRESHOLD = 0.25


def check_rate_anomaly(doc, method):
	items_to_check = _get_stock_items(doc)
	if not items_to_check:
		return

	anomalies = []
	for item_code, warehouse, current_rate in items_to_check:
		if not current_rate:
			continue

		prev_rate = _get_last_valuation_rate(item_code, warehouse)
		if not prev_rate:
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
				results.append((d.item_code, d.warehouse, flt(d.incoming_rate)))
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


def _get_last_valuation_rate(item_code, warehouse):
	rate = frappe.db.get_value(
		"Stock Ledger Entry",
		{
			"item_code": item_code,
			"warehouse": warehouse,
			"is_cancelled": 0,
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

	frappe.msgprint(
		message,
		title="Rate Increase Alert",
		indicator="orange",
	)


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
