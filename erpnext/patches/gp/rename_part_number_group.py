import re

import frappe
from frappe.model.naming import make_autoname
from frappe.model.rename_doc import rename_doc

"""
bench --site test7 execute erpnext.patches.gp.rename_part_number_group.execute
"""

NAMING_SERIES = "500.###"
NEW_NAME_PATTERN = re.compile(r"^50\d{4}$")


def execute():
	if not frappe.db.exists("DocType", "Part Number Group"):
		return

	groups = frappe.get_all(
		"Part Number Group",
		fields=["name", "creation"],
		order_by="creation asc, name asc",
	)

	for group in groups:
		# if NEW_NAME_PATTERN.match(group.name):
		# 	continue

		new_name = make_autoname(NAMING_SERIES, "Part Number Group")
		print("Rename Part Number Group", group.name, "->", new_name)
		rename_doc("Part Number Group", group.name, new_name, force=True)
		# break
