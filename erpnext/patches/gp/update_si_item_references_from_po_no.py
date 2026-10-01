import frappe

"""
bench --site erp-prod execute erpnext.patches.gp.update_si_item_references_from_po_no.execute
bench --site SITE execute "erpnext.patches.gp.update_si_item_references_from_po_no.execute --kwargs \"{'dry_run': 1}\""

Entry point: Sales Invoices yang punya po_no tapi item-nya tidak punya reff sama sekali.
Untuk tiap SI tersebut, cari SO/DN sibling dengan po_no + customer sama
(dan DN yang mereff SO tersebut), lalu isi reff item yang kosong:
- sii.sales_order / sii.so_detail dari Sales Order Item
- sii.delivery_note / sii.dn_detail dari Delivery Note Item
- header si.delivery_note kalau kosong
Tidak ada reff existing yang di-override.
"""


def execute(dry_run=0):
	mode = "DRY RUN (no changes will be committed)" if dry_run else "APPLY"
	print("=== update_si_item_references_from_po_no: {0} ===".format(mode))

	sis = frappe.db.sql(
		"""
		select distinct si.name, si.po_no, si.customer
		from `tabSales Invoice` si
		inner join `tabSales Invoice Item` sii on sii.parent = si.name
		where si.docstatus < 2
			and ifnull(si.po_no, '') != ''
			and ifnull(sii.sales_order, '') = ''
			and ifnull(sii.so_detail, '') = ''
			and ifnull(sii.delivery_note, '') = ''
			and ifnull(sii.dn_detail, '') = ''
		""",
		as_dict=True,
	)
	print("SI candidates (po_no set, item reff empty): {0} docs".format(len(sis)))

	updated_items = 0
	updated_si = 0
	processed_si = 0
	for si in sis:
		processed_si += 1
		po_nos = [x.strip() for x in si.po_no.split(",") if x.strip()]
		if not po_nos:
			continue

		print("[{0}/{1}] {2} (po_no: {3}, customer: {4})".format(
			processed_si, len(sis), si.name, si.po_no, si.customer
		))

		so_map = get_so_map(po_nos, si.customer)
		dn_map = get_dn_map(po_nos, si.customer, so_map)

		si_changed = False
		dn_parents = set()

		for sii in frappe.get_all(
			"Sales Invoice Item",
			filters={"parent": si.name},
			fields=["name", "item_code", "sales_order", "so_detail", "delivery_note", "dn_detail"],
		):
			so = sii.sales_order
			so_detail = sii.so_detail
			dn = sii.delivery_note
			dn_detail = sii.dn_detail

			# 1. SO reff dari po_no
			if not so or not so_detail:
				match = so_map.get(sii.item_code)
				if match:
					so, so_detail = match
			# 2. DN reff: DN yang mereff SO yang sama, atau DN sibling dengan po_no sama
			if not dn or not dn_detail:
				match = None
				if so:
					match = dn_map.get((sii.item_code, so))
				if not match:
					match = dn_map.get((sii.item_code, None))
				if match:
					dn, dn_detail = match

			updates = {}
			if so and so != sii.sales_order:
				updates["sales_order"] = so
			if so_detail and so_detail != sii.so_detail:
				updates["so_detail"] = so_detail
			if dn and dn != sii.delivery_note:
				updates["delivery_note"] = dn
			if dn_detail and dn_detail != sii.dn_detail:
				updates["dn_detail"] = dn_detail

			if not updates:
				continue

			print("  {0} [{1}] -> SO: {2} ({3}) | DN: {4} ({5})".format(
				sii.name, sii.item_code, updates.get("sales_order"), updates.get("so_detail"),
				updates.get("delivery_note"), updates.get("dn_detail"),
			))
			if not dry_run:
				frappe.db.set_value("Sales Invoice Item", sii.name, updates, update_modified=True)
			if updates.get("delivery_note"):
				dn_parents.add(updates["delivery_note"])
			updated_items += 1
			si_changed = True

		# header delivery_note kalau kosong
		if si_changed and dn_parents:
			existing = frappe.db.get_value("Sales Invoice", si.name, "delivery_note")
			if not existing:
				print("  header {0} -> delivery_note: {1}".format(si.name, ",".join(sorted(dn_parents))))
				if not dry_run:
					frappe.db.set_value(
						"Sales Invoice", si.name, "delivery_note", ",".join(sorted(dn_parents)),
						update_modified=True,
					)
			updated_si += 1

		if not dry_run and updated_items and updated_items % 500 == 0:
			frappe.db.commit()
			print("  ... committed {0} items".format(updated_items))

		# break
	if not dry_run:
		frappe.db.commit()
	print("=== {0}: {1} SI items updated / {2} SI docs updated ===".format(mode, updated_items, updated_si))


def get_so_map(po_nos, customer):
	"""item_code -> (so_name, so_detail). SO terbaru per item."""
	rows = frappe.db.sql(
		"""
		select soi.item_code, soi.parent, soi.name
		from `tabSales Order Item` soi
		inner join `tabSales Order` so on so.name = soi.parent
		where so.docstatus < 2
			and so.po_no in %s
			and so.customer = %s
		order by soi.creation asc
		""",
		(po_nos, customer),
		as_dict=True,
	)
	so_map = {}
	for r in rows:
		so_map.setdefault(r.item_code, (r.parent, r.name))
	return so_map


def get_dn_map(po_nos, customer, so_map):
	"""(item_code, so_name|None) -> (dn_name, dn_detail).

	Prioritas:
	1. DN item yang against_sales_order cocok dengan SO reff item tersebut
	2. DN sibling dengan po_no sama (tanpa SO reff)
	DN terbaru per kunci.
	"""
	item_codes = list(so_map.keys())
	if not item_codes:
		return {}
	rows = frappe.db.sql(
		"""
		select dni.item_code, dni.parent, dni.name, dni.against_sales_order
		from `tabDelivery Note Item` dni
		inner join `tabDelivery Note` dn on dn.name = dni.parent
		where dn.docstatus < 2
			and dn.customer = %s
			and dn.po_no in %s
			and dni.item_code in %s
		order by dni.creation asc
		""",
		(customer, po_nos, item_codes),
		as_dict=True,
	)
	dn_map = {}
	for r in rows:
		if r.against_sales_order:
			dn_map.setdefault((r.item_code, r.against_sales_order), (r.parent, r.name))
		else:
			dn_map.setdefault((r.item_code, None), (r.parent, r.name))
	return dn_map
