import frappe
from frappe.utils import cstr, flt

DRY_RUN_SAMPLE_LIMIT = 10


"""
bench --site erp-prod execute erpnext.patches.gp.restore_dn_reference_to_si.execute
"""
def execute(dry_run=0):
	"""Restore custom_delivery_note_references on older Sales Invoice Items.

	Targets 3 groups (test6 audit 2026-09-30):
	A. SI item has dn_detail + delivery_note but empty custom_delivery_note_references
	   -> backfill single ref: {delivery_note}|{dn_detail}|{qty}|{sales_order}|{so_detail}
	B. SI item has custom_sales_order_references but no dn_detail and no custom_delivery_note_references
	   (wiped by old has_multi_delivery_note_references bug, commit 1e5d723 fixed going forward)
	   -> rebuild refs from Delivery Note Items matching each so_detail
	C. DN item has si_detail/against_sales_invoice but SI item lost dn_detail
	   -> rebuild refs from DN reverse link

	Pass dry_run=True for checking only without commit.
	Usage:
	  bench --site test6 execute erpnext.patches.gp.restore_dn_reference_to_si.execute
	  bench --site test6 execute "erpnext.patches.gp.restore_dn_reference_to_si.execute --kwargs \"{'dry_run': True}\""
	"""

	mode = "DRY RUN (no changes will be committed)" if dry_run else "APPLY"
	print("=== restore_dn_reference_to_si: {0} ===".format(mode))

	restore_from_dn_detail(dry_run)
	restore_from_custom_so_references(dry_run)
	restore_from_dn_reverse_link(dry_run)

	if dry_run:
		print("=== DRY RUN finished: nothing was committed ===")
	else:
		print("=== APPLY finished ===")


def _apply(si_item, ref, dry_run):
	if dry_run:
		return
	frappe.db.set_value(
		"Sales Invoice Item", si_item, "custom_delivery_note_references", ref, update_modified=False
	)


def _set_parent_delivery_note(si_parents, dry_run):
	"""Set parent.delivery_note (comma-joined DN list) on restored SI, skip is_lazada_order."""
	updated = 0
	for si_name in si_parents:
		is_lazada = frappe.db.get_value("Sales Invoice", si_name, "is_lazada_order")
		if is_lazada:
			continue
		dn_list = sorted(set(filter(None, si_parents[si_name])))
		if not dn_list:
			continue
		existing = frappe.db.get_value("Sales Invoice", si_name, "delivery_note")
		if existing:
			continue
		if len(dn_list) > 1:
			print("  {0}: {1} DN refs deduped -> {2}".format(si_name, len(si_parents[si_name]), ",".join(dn_list)))
		print("  parent {0} -> delivery_note: {1}".format(si_name, ",".join(dn_list)))
		if not dry_run:
			frappe.db.set_value(
				"Sales Invoice", si_name, "delivery_note", ",".join(dn_list), update_modified=True
			)
		updated += 1

	if not dry_run:
		frappe.db.commit()
	print("parent.delivery_note updated: {0}".format(updated))


def restore_from_dn_detail(dry_run=False):
	"""Group A: backfill ref from existing dn_detail field."""
	entries = frappe.db.sql(
		"""
		select sii.name, sii.parent, sii.delivery_note, sii.dn_detail, sii.qty, sii.sales_order, sii.so_detail
		from `tabSales Invoice Item` sii
		inner join `tabSales Invoice` si on si.name = sii.parent and si.docstatus < 2
		where ifnull(si.delivery_note, '') = ''
			and ifnull(sii.dn_detail, '') != ''
			and ifnull(sii.custom_delivery_note_references, '') = ''
		""",
		as_dict=True,
	)

	print("Group A candidates (dn_detail present, ref empty): {0} rows / {1} SI docs".format(
		len(entries), len(set(d.parent for d in entries))
	))
	updated = 0
	si_parents = {}
	for d in entries:
		if not frappe.db.exists("Delivery Note Item", d.dn_detail):
			print("  skip {0}: dn_detail {1} no longer exists".format(d.name, d.dn_detail))
			continue
		ref = "|".join(
			[
				d.delivery_note or "",
				d.dn_detail,
				cstr(flt(d.qty)),
				d.sales_order or "",
				d.so_detail or "",
			]
		)
		print("  {0} (SI {1}) -> {2}".format(d.name, d.parent, ref))
		_apply(d.name, ref, dry_run)
		if d.delivery_note:
			si_parents.setdefault(d.parent, []).append(d.delivery_note)
		updated += 1
		if not dry_run and updated % 500 == 0:
			frappe.db.commit()
			print("  Group A committed {0}".format(updated))
		# break
	if not dry_run:
		frappe.db.commit()
	print("Group A updated: {0}".format(updated))
	_set_parent_delivery_note(si_parents, dry_run)


def restore_from_custom_so_references(dry_run=False):
	"""Group B: rebuild dn refs from custom_sales_order_references (links were wiped)."""
	entries = frappe.db.sql(
		"""
		select sii.name, sii.parent, sii.custom_sales_order_references
		from `tabSales Invoice Item` sii
		inner join `tabSales Invoice` si on si.name = sii.parent and si.docstatus < 2
		where ifnull(si.delivery_note, '') = ''
			and ifnull(sii.custom_sales_order_references, '') != ''
			and ifnull(sii.dn_detail, '') = ''
			and ifnull(sii.delivery_note, '') = ''
			and ifnull(sii.custom_delivery_note_references, '') = ''
		""",
		as_dict=True,
	)

	print("Group B candidates (custom_so ref only): {0} rows / {1} SI docs".format(
		len(entries), len(set(d.parent for d in entries))
	))
	updated = 0
	si_parents = {}
	for d in entries:
		refs = []
		for so_ref in filter(None, (d.custom_sales_order_references or "").split(",")):
			parts = so_ref.split("|")
			if len(parts) < 3:
				continue
			so_name, so_detail, so_qty = parts[0], parts[1], flt(parts[2])
			remaining = so_qty
			dn_items = frappe.get_all(
				"Delivery Note Item",
				filters={"so_detail": so_detail, "docstatus": 1},
				fields=["parent", "name", "qty"],
				order_by="creation",
			)
			for dn_item in dn_items:
				if remaining <= 0:
					break
				qty = min(flt(dn_item.qty), remaining)
				refs.append(
					"|".join([dn_item.parent, dn_item.name, cstr(flt(qty)), so_name, so_detail])
				)
				remaining -= qty
		if not refs:
			print("  skip {0}: no DN found for SO refs".format(d.name))
			continue
		print("  {0} (SI {1}) -> {2}".format(d.name, d.parent, ",".join(refs)))
		_apply(d.name, ",".join(refs), dry_run)
		for r in refs:
			si_parents.setdefault(d.parent, []).append(r.split("|")[0])
		updated += 1
		# break
	if not dry_run:
		frappe.db.commit()
	print("Group B updated: {0}".format(updated))
	_set_parent_delivery_note(si_parents, dry_run)


def restore_from_dn_reverse_link(dry_run=False):
	"""Group C: DN item points to SI (si_detail) but SI item lost dn_detail."""
	entries = frappe.db.sql(
		"""
		select sii.name as si_item, sii.parent as si_parent, sii.custom_sales_order_references, sii.qty,
			dni.parent as dn, dni.name as dn_detail, dni.qty as dn_qty,
			dni.against_sales_order as sales_order, dni.so_detail
		from `tabDelivery Note Item` dni
		inner join `tabDelivery Note` dn on dn.name = dni.parent and dn.docstatus = 1
		inner join `tabSales Invoice` si on si.name = dni.against_sales_invoice and si.docstatus < 2
		inner join `tabSales Invoice Item` sii on sii.name = dni.si_detail
		where ifnull(si.delivery_note, '') = ''
			and ifnull(dni.against_sales_invoice, '') != ''
			and ifnull(dni.si_detail, '') != ''
			and ifnull(sii.dn_detail, '') = ''
			and ifnull(sii.custom_delivery_note_references, '') = ''
		""",
		as_dict=True,
	)

	print("Group C candidates (DN reverse link, SI lost dn_detail): {0} DN rows / {1} SI item rows / {2} SI docs".format(
		len(entries),
		len(set(d.si_item for d in entries)),
		len(set(d.si_parent for d in entries)),
	))
	updated = 0
	si_parents = {}
	by_si_item = {}
	for d in entries:
		by_si_item.setdefault(d.si_item, []).append(d)

	for si_item, rows in by_si_item.items():
		refs = []
		for r in rows:
			refs.append(
				"|".join([r.dn, r.dn_detail, cstr(flt(r.dn_qty)), r.sales_order or "", r.so_detail or ""])
			)
		print("  {0} (SI {1}) -> {2}".format(si_item, rows[0].si_parent, ",".join(refs)))
		_apply(si_item, ",".join(refs), dry_run)
		for r in rows:
			si_parents.setdefault(r.si_parent, []).append(r.dn)
		updated += 1
		# break
	
	if not dry_run:
		frappe.db.commit()
	print("Group C updated: {0}".format(updated))
	_set_parent_delivery_note(si_parents, dry_run)
