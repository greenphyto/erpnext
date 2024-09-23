# Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _


def execute(filters=None):
	columns = [
		{"label": _("Material Type"), 	"fieldname": "material_type", 	"fieldtype": "Link", "width": 125, "options":"Material Group"},
		{"label": _("Material Group"), 	"fieldname": "material_group", 	"fieldtype": "Data", "width": 135},
		{"label": _("Title"), 			"fieldname": "title", 			"fieldtype": "Data", "width": 250},
		{"label": _("Description"), 	"fieldname": "description", 	"fieldtype": "Data", "width": 250},
		{"label": _("Part Number"), 	"fieldname": "part_number", 	"fieldtype": "Int", "width": 120},
		{"label": _("End"), 			"fieldname": "end", 			"fieldtype": "Int", "width": 100},
		{"label": _("Price Control"), 	"fieldname": "price_control", 	"fieldtype": "Data", "width": 125},
		{"label": _("BS Inventory"), 	"fieldname": "bs_inventory", 	"fieldtype": "Link", "width": 260, "options":"Account"},
	]

	raw_data = frappe.db.sql("""
		select * from `tabPart Number Details` order by idx
	""", as_dict=1)
	data = []
	cur_group = ""
	for d in raw_data:
		dt = {}
		if not cur_group or cur_group != d.material_group:
			if cur_group:
				data.append({})
			cur_group = d.material_group
			dt['material_type'] = frappe.get_value("Material Group", d.material_group, "material_type")
			dt['material_group'] = d.material_group
			dt['part_number'] = d.part_number
			dt['end'] = d.end
			dt['price_control'] = d.price
			dt['bs_inventory'] = d.account_code
			data.append(dt)
		
		dt = {}
		dt['material_group'] = d.code
		dt['title'] = d.title
		dt['part_number'] = d.part_number
		dt['bs_inventory'] = d.account_code
		data.append(dt)

	return columns, data
