# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _


def execute(filters=None):
	filters = frappe._dict(filters or {})
	return get_columns(), get_data(filters)


def get_columns():
	return [
		{"label": _("Part Number Group / Item"), "fieldname": "name_col", "fieldtype": "Data", "width": 220},
		{"label": _("Item Name"), "fieldname": "item_name", "fieldtype": "Data", "width": 240},
		{"label": _("Part Number"), "fieldname": "part_number", "fieldtype": "Data", "width": 120},
		{"label": _("Credit Factor"), "fieldname": "credit_factor", "fieldtype": "Int", "width": 120},
	]


def get_data(filters):
	conditions = ["png.disabled = 0"]
	values = {}

	if filters.part_number_group:
		conditions.append("png.name = %(part_number_group)s")
		values["part_number_group"] = filters.part_number_group

	if filters.pack_type:
		conditions.append("png.pack_type = %(pack_type)s")
		values["pack_type"] = filters.pack_type

	if filters.item_default:
		conditions.append("png.item_default = %(item_default)s")
		values["item_default"] = filters.item_default

	if filters.item_code:
		conditions.append("pnt.item_code = %(item_code)s")
		values["item_code"] = filters.item_code

	if filters.part_number:
		conditions.append("pnt.part_number like %(part_number)s")
		values["part_number"] = "%{0}%".format(filters.part_number)

	where = "where " + " and ".join(conditions)

	rows = frappe.db.sql(
		"""
		select
			png.name as part_number_group,
			png.pack_type,
			png.item_default,
			default_item.item_name as item_default_name,
			pnt.item_code,
			pnt.part_number,
			pnt.item_name,
			pnt.credit_factor
		from `tabPart Number Group` png
		inner join `tabPart Number Table List` pnt
			on pnt.parent = png.name and pnt.parenttype = 'Part Number Group'
		left join `tabItem` default_item on default_item.name = png.item_default
		{where}
		order by png.name asc, pnt.idx asc
		""".format(where=where),
		values,
		as_dict=1,
	)

	data = []
	current_group = None
	for row in rows:
		if row.part_number_group != current_group:
			current_group = row.part_number_group
			data.append(
				{
					"name_col": "{0} / {1}".format(
						row.part_number_group, row.item_default_name or row.item_default
					)
					if row.item_default
					else row.part_number_group,
					"pack_type": row.pack_type,
					"part_number_group": row.part_number_group,
					"indent": 0,
				}
			)
		data.append(
			{
				"name_col": row.item_code,
				"item_code": row.item_code,
				"part_number": row.part_number,
				"item_name": row.item_name,
				"credit_factor": row.credit_factor,
				"indent": 1,
			}
		)
	return data
