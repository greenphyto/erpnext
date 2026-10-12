import frappe
from frappe.utils import flt

"""
Fix Delivery Note items that were submitted with rate=0 / amount=0 while the
linked Sales Order Item carries the correct rate. This leaves the DN net_total
understated so any Sales Invoice billing against it trips the over-billing check
(billed amount >> DN item amount).

The patch repairs the DN *in place* (no cancel/amend):
  1. load the submitted DN as a document
  2. for each zero-rate item, pull the correct rate from its Sales Order Item
     (so_detail), fall back to price_list_rate when no SO link exists
  3. recompute every item + total + tax field via ERPNext's own
     calculate_taxes_and_totals()
  4. persist with db_update() so GL/stock ledger entries (qty-only here) stay intact
  5. refresh downstream per_billed on the DN

Usage:
  bench --site erp-prod execute erpnext.patches.gp.fix_dn_zero_rate_overbilling.execute
  bench --site erp-prod execute "erpnext.patches.gp.fix_dn_zero_rate_overbilling.execute --kwargs \"{'delivery_note': 'DO-2026-04756', 'dry_run': True}\""
"""

TARGET_DELIVERY_NOTES = ["DO-2026-04756"]


def execute(delivery_note=None, dry_run=0):
	mode = "DRY RUN (no changes will be committed)" if dry_run else "APPLY"
	print("=== fix_dn_zero_rate_overbilling: {0} ===".format(mode))

	targets = [delivery_note] if delivery_note else TARGET_DELIVERY_NOTES
	for dn_name in targets:
		fix_delivery_note(dn_name, dry_run)

	if dry_run:
		print("=== DRY RUN finished: nothing was committed ===")
	else:
		print("=== APPLY finished ===")


def _resolve_rate(item):
	"""Return the correct rate for a zero-rate DN item."""
	if item.so_detail:
		so_rate = frappe.db.get_value("Sales Order Item", item.so_detail, "rate")
		if flt(so_rate):
			return flt(so_rate)
	if flt(item.price_list_rate):
		return flt(item.price_list_rate)
	return 0.0


def fix_delivery_note(dn_name, dry_run=0):
	if not frappe.db.exists("Delivery Note", dn_name):
		print("  skip {0}: not found".format(dn_name))
		return

	doc = frappe.get_doc("Delivery Note", dn_name)
	if doc.docstatus != 1:
		print("  skip {0}: docstatus={1} (only submitted DN handled)".format(dn_name, doc.docstatus))
		return

	zero_items = [d for d in doc.items if not flt(d.rate) or not flt(d.amount)]
	if not zero_items:
		print("  {0}: no zero-rate items, nothing to do".format(dn_name))
		return

	print("  {0}: before total={1} net_total={2} total_taxes={3} grand_total={4}".format(
		dn_name, doc.total, doc.net_total, doc.total_taxes_and_charges, doc.grand_total
	))

	changed = 0
	for d in zero_items:
		new_rate = _resolve_rate(d)
		if not new_rate:
			print("    row idx {0} ({1}): no source rate found, skipped".format(d.idx, d.item_code))
			continue
		print("    row idx {0} ({1}) qty={2}: rate {3} -> {4}".format(
			d.idx, d.item_code, d.qty, d.rate, new_rate
		))
		d.rate = new_rate
		d.price_list_rate = d.price_list_rate or new_rate
		d.margin_type = ""
		d.discount_percentage = 0
		d.discount_amount = 0
		changed += 1

	if not changed:
		print("  {0}: no rows updated".format(dn_name))
		return

	doc.calculate_taxes_and_totals()

	print("  {0}: after  total={1} net_total={2} total_taxes={3} grand_total={4}".format(
		dn_name, doc.total, doc.net_total, doc.total_taxes_and_charges, doc.grand_total
	))

	if dry_run:
		return

	for d in doc.items:
		d.db_update()
	for t in doc.taxes:
		t.db_update()
	doc.db_update()

	doc.update_billing_status(update_modified=False)
	doc.set_status(update=True)
	doc.db_update()

	frappe.db.commit()
	print("  {0}: committed. new per_billed={1}".format(
		dn_name, frappe.db.get_value("Delivery Note", dn_name, "per_billed")
	))
