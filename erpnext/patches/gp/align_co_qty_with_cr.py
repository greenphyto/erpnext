import frappe
from frappe.utils import flt


def execute(dry_run=False):
	draft_cos = frappe.get_all(
		"Consignment Order",
		filters={"docstatus": 0},
		pluck="name",
	)
	if not draft_cos:
		print("No draft Consignment Orders found")
		return

	updated_items = 0
	updated_docs = 0

	for name in draft_cos:
		doc = frappe.get_doc("Consignment Order", name)
		doc_changed = False

		for item in doc.items:
			if not item.against_consignment_request or not item.cr_detail:
				continue

			cr_item = frappe.db.get_value(
				"Consignment Request Item",
				{
					"name": item.cr_detail,
					"parent": item.against_consignment_request,
				},
				["qty", "conversion_factor", "stock_qty"],
				as_dict=True,
			)
			if not cr_item:
				continue

			cr_qty = flt(cr_item.qty)
			cr_conversion_factor = flt(cr_item.conversion_factor) or 1
			cr_stock_qty = flt(cr_item.stock_qty) or (cr_qty * cr_conversion_factor)

			if (
				flt(item.qty) == cr_qty
				and flt(item.conversion_factor) == cr_conversion_factor
				and flt(item.stock_qty) == cr_stock_qty
			):
				continue

			print(
				f"  {doc.name} / {item.item_code} (CR {item.against_consignment_request}): "
				f"qty {flt(item.qty)} -> {cr_qty}, "
				f"cf {flt(item.conversion_factor)} -> {cr_conversion_factor}, "
				f"stock_qty {flt(item.stock_qty)} -> {cr_stock_qty}"
			)

			item.qty = cr_qty
			item.conversion_factor = cr_conversion_factor
			item.stock_qty = cr_stock_qty
			doc_changed = True
			updated_items += 1

		if doc_changed:
			if not dry_run:
				doc.save()
			updated_docs += 1

	if dry_run:
		frappe.db.rollback()
		print(
			f"[DRY RUN] Would align {updated_docs} draft Consignment Order(s), "
			f"{updated_items} item(s). No changes committed."
		)
	else:
		frappe.db.commit()
		print(
			f"Aligned qty from Consignment Request on {updated_docs} draft Consignment Order(s), "
			f"{updated_items} item(s) updated"
		)

