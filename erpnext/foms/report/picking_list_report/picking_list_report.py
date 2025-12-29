# Copyright (c) 2013, erfidner.id and contributors
# For license information, please see license.txt

"""
Report for daily accumulation broker vs stock
"""

import frappe
from frappe.utils import flt
from frappe import _

def execute(filters=None):
	return Report(filters).execute()

CARTON_FACTOR = 15

class Report():
	def __init__(self, filters):
		self.data = []
		self.filters = filters
		self.outlets = []
		# List to store technical names of outlets
		self.outlet_names = []
		self.row_map ={
			"pic":{
				"outlets":"PIC"
			},
			"total_packs":{
				  	"outlets":"Total Packs",
					'po':0,
					'return':0,
					'delivery':0
			},
			"total_cartons":{
					"outlets":"Total Cartons", 
					'po':0,
					'return':0,
					'delivery':0
			}
		}

	def set_condition(self):
		self.cond = ""
		if self.filters.company:
			self.cond += " and dn.company = %(company)s "
		if self.filters.date:
			self.cond += " and dn.posting_date = %(date)s "

		self.group_by = "outlet_name"
		if self.filters.view_type == "Delivery Note":
			self.group_by = "dn.name"
			self.row_map['pic'] = {"outlets":"Outlets"}
			
	
	def get_data(self):
		# Fetch transaction data by joining Item table with the parent Delivery Note table
		# We use dn.customer as the field that holds the outlet/customer name
		self.raw_data = frappe.db.sql("""
			SELECT 
				dni.item_code,
				dn.customer,
				dn.contact_display,
				dn.name as delivery_note,
				IFNULL(a.outlet_name, dn.customer) AS outlet_name,
				SUM(CASE WHEN dn.is_return = 0 THEN dni.qty ELSE 0 END) AS total_qty,
				ABS(SUM(CASE WHEN dn.is_return = 1 THEN dni.qty ELSE 0 END)) AS total_qty_return,
				b.actual_qty / p.total_weight AS stock_qty
			FROM
				`tabDelivery Note Item` dni
					INNER JOIN
				`tabDelivery Note` dn ON dni.parent = dn.name
					INNER JOIN
				`tabAddress` a ON a.name = dn.shipping_address_name
					INNER JOIN
				`tabItem` i ON i.name = dni.item_code
					INNER JOIN
				`tabBin` b ON b.item_code = dni.item_code
					AND b.warehouse = 'Finished Goods - GPL'
					INNER JOIN
				`tabPackaging` p ON p.name = i.default_packaging
			WHERE
				dn.docstatus = 1 AND dn.is_marketing = 0
					AND dn.is_giveaway = 0
					AND dn.is_donation = 0
					AND dn.is_production = 0
					AND dn.customer != 'Marketing'
					{}
			GROUP BY dni.item_code , {}
		""".format(self.cond, self.group_by), self.filters, as_dict=1, debug=0)

		processed_data = {}

	def setup_columns(self):
		# Define static (fixed) columns first
		label = "Outlets"
		if self.filters.view_type == "Delivery Note":
			label = "Delivery Note"

		self.columns = [
			{"fieldname": "outlets",   "label": _(label),    "fieldtype": "Data", "width": 120, "options": ""},
		]
		
		# Dynamically append columns based on the list of outlets
		self.outlet_names = []
		self.key_total = {}
		for d in self.raw_data:
			if self.filters.view_type == "All Outlets":
				key, label = self.get_outlet_name(d.outlet_name)
				width = 220
			else:
				key, label = self.get_outlet_name(d.delivery_note)
				width = 180

			
			if key not in self.outlet_names:
				self.columns.append({
					"fieldname": key,           # Unique fieldname (technical outlet name)
					"label": _(label),            # Column label (can be customized)
					"fieldtype": "Data",                 # Data type
					"width": width,                        # Column width
				})
				self.row_map["total_packs"][key] = 0
				self.row_map["total_cartons"][key] = 0
				if self.filters.view_type == "Delivery Note":
					self.row_map['pic'][key] = d.outlet_name
				else:
					self.row_map['pic'][key] = d.contact_display
				self.outlet_names.append(key)

			# Item code
			if d.item_code not in self.row_map:
				self.row_map[d.item_code] = {
					key: d.total_qty, 
					'outlets':d.item_code, 
					'po':0,
					'return':0,
					'delivery':0
				}
			elif key not in self.row_map[d.item_code]:
				self.row_map[d.item_code][key] = flt(d.total_qty)
			else:
				self.row_map[d.item_code][key] += flt(d.total_qty)
			self.key_total.setdefault(d.item_code, )

			# Total
			if key not in self.row_map["total_packs"]:
				self.row_map["total_packs"][key] = flt(d.total_qty)
			else:
				self.row_map["total_packs"][key] += flt(d.total_qty)

			self.row_map["total_cartons"][key] = flt(flt(self.row_map["total_packs"].get(key)) / CARTON_FACTOR,0)


			self.row_map[d.item_code]['po'] += (d.total_qty - d.total_qty_return)
			self.row_map[d.item_code]['return'] += d.total_qty_return
			self.row_map[d.item_code]['delivery'] += d.total_qty

		self.columns += [
			{"fieldname": "po",   		"label": _("PO"),    		"fieldtype": "Float", "width": 100, "options": ""},
			{"fieldname": "return",   	"label": _("Return"),    	"fieldtype": "Float", "width": 100, "options": ""},
			{"fieldname": "delivery",   "label": _("Delivery"),     "fieldtype": "Float", "width": 100, "options": ""},
		]

		for key, val in self.row_map.items():
			if key not in ['total_packs', 'pic', 'total_cartons']:
				self.row_map["total_packs"]['po'] += val['po']
				self.row_map["total_packs"]['return'] += val['return']
				self.row_map["total_packs"]['delivery'] += val['delivery']
			
		
		self.row_map["total_cartons"]['po'] = flt(self.row_map["total_packs"]['po'] / CARTON_FACTOR,0)
		self.row_map["total_cartons"]['return'] = flt(self.row_map["total_packs"]['return'] / CARTON_FACTOR,0)
		self.row_map["total_cartons"]['delivery'] = flt(self.row_map["total_packs"]['delivery'] / CARTON_FACTOR,0)


	def get_outlet_name(self, text):
		return frappe.scrub(text), text
	
	def get_item_name(self, text):
		return text
	
	def prepare_data(self):
		self.data = []
		self.data.append(self.row_map['pic'])
		for key, val in self.row_map.items():
			if key not in ['pic', 'total_packs', 'total_cartons']:
				self.data.append(val)
		self.data.append(self.row_map['total_packs'])
		self.data.append(self.row_map['total_cartons'])

	def execute(self):
		self.set_condition()
		self.get_data()         # Fetch and process the transaction data
		self.setup_columns()    # Set up the dynamic columns for the report
		self.prepare_data()

		# Return the columns and data back to the Frappe framework
		return self.columns, self.data
