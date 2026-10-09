import frappe
from frappe import _
from frappe.utils import getdate, nowdate, today


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def filter_asset_maintenance(doctype, txt, searchfield, start, page_len, filters):
	return frappe.db.sql(
		"""select am.name, am.item_name
		from `tabAsset Maintenance` as am
		where am.docstatus != 2 and
		am.{key} LIKE %(txt)s""".format(
			key=searchfield
		),
		{"txt": "%" + txt + "%"},
	)
