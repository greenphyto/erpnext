# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt


import json

import frappe
import frappe.utils
from frappe import _
from frappe.contacts.doctype.address.address import get_company_address
from frappe.desk.notifications import clear_doctype_notifications
from frappe.model.mapper import get_mapped_doc
from frappe.model.utils import get_fetch_values
from frappe.utils import add_days, cint, cstr, flt, get_link_to_form, getdate, nowdate, strip_html
from frappe.utils import safe_abs as abs

from erpnext.accounts.doctype.sales_invoice.sales_invoice import (
	unlink_inter_company_doc,
	update_linked_doc,
	validate_inter_company_party,
)
from erpnext.accounts.party import get_party_account
from erpnext.controllers.selling_controller import SellingController
from erpnext.manufacturing.doctype.production_plan.production_plan import (
	get_items_for_material_requests,
)
from erpnext.selling.doctype.customer.customer import check_credit_limit
from erpnext.setup.doctype.item_group.item_group import get_item_group_defaults
from erpnext.stock.doctype.item.item import get_item_defaults
from erpnext.stock.get_item_details import get_default_bom
from erpnext.stock.stock_balance import get_reserved_qty, update_bin_qty
from erpnext.stock.doctype.batch.batch import get_batch_no

form_grid_templates = {"items": "templates/form_grid/item_grid.html"}


class ConsignmentRequest(SellingController):
	def __init__(self, *args, **kwargs):
		super(ConsignmentRequest, self).__init__(*args, **kwargs)

	# def onload(self):
	# 	super(ConsignmentRequest, self).onload()
	# 	return_warehouse = frappe.get_value("Warehouse", {"warehouse_name": "Salvage Room", "company":self.company})
	# 	print("Return Warehouse:", return_warehouse, self.company)
	# 	self.set_onload("return_warehouse", return_warehouse)

	def validate(self):
		super(ConsignmentRequest, self).validate()
		self.validate_uom_is_integer("stock_uom", "stock_qty")
		self.validate_uom_is_integer("uom", "qty")
		self.set_status()
		self.reset_default_field_value("set_warehouse", "items", "warehouse")

	def on_submit(self):
		self.check_credit_limit()
		frappe.get_doc("Authorization Control").validate_approving_authority(
			self.doctype, self.company, self.base_grand_total, self
		)
		self.create_customer_warehouse()

	def on_cancel(self):
		self.ignore_linked_doctypes = ("GL Entry", "Stock Ledger Entry", "Payment Ledger Entry")
		super(ConsignmentRequest, self).on_cancel()

		# Cannot cancel closed SO
		if self.status == "Closed":
			frappe.throw(_("Closed order cannot be cancelled. Unclose to cancel."))

		self.db_set("status", "Cancelled")

	def update_prevdoc_status(self, action):
		pass

	def check_credit_limit(self):
		# if bypass credit limit check is set to true (1) at Consignment Request level,
		# then we need not to check credit limit and vise versa
		if not cint(
			frappe.db.get_value(
				"Customer Credit Limit",
				{"parent": self.customer, "parenttype": "Customer", "company": self.company},
				"bypass_credit_limit_check",
			)
		):
			check_credit_limit(self.customer, self.company)

	def check_modified_date(self):
		mod_db = frappe.db.get_value("Consignment Request", self.name, "modified")
		date_diff = frappe.db.sql("select TIMEDIFF('%s', '%s')" % (mod_db, cstr(self.modified)))
		if date_diff and date_diff[0][0]:
			frappe.throw(_("{0} {1} has been modified. Please refresh.").format(self.doctype, self.name))

	def update_status(self, status):
		self.check_modified_date()
		self.set_status(update=True, status=status)

	def set_indicator(self):
		"""Set indicator for portal"""
		if self.per_billed < 100 and self.per_delivered < 100:
			self.indicator_color = "orange"
			self.indicator_title = _("Not Paid and Not Delivered")

		elif self.per_billed == 100 and self.per_delivered < 100:
			self.indicator_color = "orange"
			self.indicator_title = _("Paid and Not Delivered")

		else:
			self.indicator_color = "green"
			self.indicator_title = _("Paid")

	def create_customer_warehouse(self):
		from erpnext.stock.doctype.warehouse.warehouse import create_warehouse

		# create parent warehouse if not exists
		parent_name = "Consignment Warehouse"
		parent = frappe.db.exists("Warehouse", {"warehouse_name": parent_name, "company": self.company})
		if not parent:
			parent = create_warehouse(
				parent_name,
				company=self.company,
				is_group=1,
			)

		self.con_warehouse = frappe.db.get_value("Warehouse", {"customer": self.customer})
		if not self.con_warehouse:
			warehouse_name = f"Consignment - {self.customer}"
			warehouse = create_warehouse(
				warehouse_name,
				company=self.company,
				customer=self.customer,
				is_group=0,
				parent_warehouse=parent,
				return_doc=True,
			)
			warehouse.customer=self.customer
			frappe.msgprint(
				_("Warehouse {0} created for Customer {1}").format(
					get_link_to_form("Warehouse", warehouse.name), self.customer
				)
			)
			self.con_warehouse = warehouse.name

	def set_status(self, update=False, status=None):
		status = "Draft"

		if flt(self.per_billed) > 0:
			status = "Completed"
		elif flt(self.per_delivered) > 0:
			status = "To Bill"
		elif (flt(self.per_sold) > 0 or flt(self.per_return) > 0) and flt(self.per_delivered) == 0:
			status = "Returned and To Bill"
		elif flt(self.per_transfer) == 100:
			status = "Transfered to Customer"
		elif flt(self.per_transfer) > 0:
			status = "Partially Transfered"
		elif flt(self.per_transfer) == 0:
			status = "Waiting for Tranfer"

		if update:
			self.db_set("status", status)
		else:
			self.status = status
	
	def sync_qty(self):
		self.total_transfer_qty = 0
		self.total_return_qty = 0
		self.total_sold_qty = 0
		self.total_billed_qty = 0
		self.total_delivered_qty = 0
		for d in self.get("items"):
			self.total_transfer_qty += flt(d.transfer_qty)
			self.total_sold_qty += flt(d.sold_qty)
			self.total_return_qty += flt(d.returned_qty)
			self.total_billed_qty += flt(d.billed_qty)
			self.total_delivered_qty += flt(d.delivered_qty)
			d.db_update()

		self.per_transfer = flt(self.total_transfer_qty/ flt(self.total_qty)*100 if self.total_qty else 0, 2)
		self.per_return = flt(self.total_return_qty/ flt(self.total_transfer_qty)*100 if self.total_transfer_qty else 0, 2)
		self.per_sold = flt(self.total_sold_qty/ flt(self.total_transfer_qty)*100 if self.total_transfer_qty else 0, 2)
		self.per_billed = flt(self.total_billed_qty/ flt(self.total_sold_qty)*100 if self.total_sold_qty else 0, 2)
		self.per_delivered = flt(self.total_delivered_qty/ flt(self.total_sold_qty)*100 if self.total_sold_qty else 0, 2)

		self.set_status()
		self.db_update()

# and salvage, create repack from SE get from SE return
# and validation for over delivery etc
# qty based on left qty - ongoing
# rate configuration

def stock_entry_controller(doc, method=""):
	con_list = list(set(d.consignment_request for d in doc.items if d.consignment_request))
	for con in con_list:
		cr = frappe.get_doc("Consignment Request", con)

		# sync for transfer qty
		qty_map = get_qty_from_transfer(con, "Consignment Transfer")
		for d in cr.get("items"):
			key = (d.item_code, d.uom)
			if key in qty_map:
				d.transfer_qty = qty_map[key].get("qty")
			else:
				d.transfer_qty = 0

		# sync for return	
		qty_map = get_qty_from_transfer(con, "Consignment Return")
		for d in cr.get("items"):
			key = (d.item_code, d.uom)
			if qty_map:
				if key in qty_map:
					d.returned_qty = qty_map[key].get("qty")
					d.sold_qty = d.transfer_qty - d.returned_qty
				else:
					d.returned_qty = 0
					d.sold_qty = d.transfer_qty
			else:
				d.returned_qty = 0
				d.sold_qty = 0

		cr.sync_qty()

def billing_consignment_controller(doc, method=""):
	cancel = doc.docstatus == 2
	# from Delivery Note and Sales Invoice
	if doc.doctype == "Sales Invoice":	
		for d in doc.items:
			cr = frappe.get_doc("Consignment Request", d.consignment_request)
			for dt in cr.items:
				if dt.name ==  d.cr_detail:
					if cancel:
						dt.db_set("billed_qty", dt.billed_qty - d.qty)
					else:
						dt.db_set("billed_qty", dt.billed_qty + d.qty)
			cr.sync_qty()

	elif doc.doctype == "Delivery Note":	
		for d in doc.items:
			cr = frappe.get_doc("Consignment Request", d.consignment_request)
			for dt in cr.items:
				if dt.name ==  d.cr_detail:
					if cancel:
						dt.db_set("delivered_qty", dt.delivered_qty - d.qty)
					else:
						dt.db_set("delivered_qty", dt.delivered_qty + d.qty)
			cr.sync_qty()

def get_list_context(context=None):
	from erpnext.controllers.website_list_for_contact import get_list_context

	list_context = get_list_context(context)
	list_context.update(
		{
			"show_sidebar": True,
			"show_search": True,
			"no_breadcrumbs": True,
			"title": _("Orders"),
		}
	)

	return list_context


@frappe.whitelist()
def make_stock_transfer(source_name, target_doc=None):
	se_type = "Consignment Transfer"
	se_series = frappe.get_value("Stock Entry Type", {"name": se_type}, "series")
	def postprocess(source, target):
		target.purpose = "Material Transfer"
		target.stock_entry_type = "Material Transfer"
		target.stock_entry_type_view = se_type
		target.naming_series = se_series
		target.from_warehouse = source.set_warehouse
		target.to_warehouse = source.con_warehouse

	def update_item(source_doc, target_doc, source_parent):
		target_doc.s_warehouse = source_parent.set_warehouse
		target_doc.t_warehouse = source_parent.con_warehouse

		# Rate configuration!

	doclist = get_mapped_doc(
		"Consignment Request",
		source_name,
		{
			"Consignment Request": {
				"doctype": "Stock Entry",
				"field_map": {},
				"field_no_map": ["payment_terms_template"],
				"validation": {"docstatus": ["=", 1]},
			},
			"Consignment Request Item": {
				"doctype": "Stock Entry Detail",
				"field_map": {
					"name": "consignment_item",
					"parent": "consignment_request",
				},
				"postprocess": update_item,
				# "condition": lambda doc: doc.delivered_qty < doc.qty,
			},
		},
		target_doc,
		postprocess,
		ignore_permissions=1,
	)

	return doclist

@frappe.whitelist()
def make_stock_return(source_name, target_doc=None):
	se_type = "Consignment Return"
	se_series = frappe.get_value("Stock Entry Type", {"name": se_type}, "series")
	def post_process_item(row, batch):
		row.consignment_item = batch.get("consignment_item")
		row.consignment_request = batch.get("consignment_request")
	
	def postprocess(source, target):
		target.purpose = "Material Transfer"
		target.stock_entry_type = "Material Transfer"
		target.stock_entry_type_view = se_type
		target.naming_series = se_series
		target.from_warehouse = source.con_warehouse
		target.to_warehouse = source.salvage_warehouse
		add_item_from_transfer(target, source.name, post_process_item)
		target.set_missing_values()

	def update_item(source_doc, target_doc, source_parent):
		target_doc.s_warehouse = source_parent.con_warehouse
		target_doc.t_warehouse = source_parent.salvage_warehouse

	doclist = get_mapped_doc(
		"Consignment Request",
		source_name,
		{
			"Consignment Request": {
				"doctype": "Stock Entry",
				"field_map": {},
				"field_no_map": ["payment_terms_template"],
				"validation": {"docstatus": ["=", 1]},
			},
			"Consignment Request Item": {
				"doctype": "Stock Entry Detail",
				"field_map": {
					"name": "consignment_item",
					"parent": "consignment_request",
				},
				"postprocess": update_item,
				# "condition": lambda doc: doc.delivered_qty < doc.qty,
			},
		},
		target_doc,
		postprocess,
		ignore_permissions=1,
	)

	return doclist

@frappe.whitelist()
def make_salvage_process(source_name, target_doc=None):
	se_type = "Salvage Process (Repack)"
	se_series = frappe.get_value("Stock Entry Type", {"name": se_type}, "series")
	def postprocess(source, target):
		target.purpose = "Material Transfer"
		target.stock_entry_type = "Material Transfer"
		target.stock_entry_type_view = se_type
		target.naming_series = se_series
		target.from_warehouse = source.salvage_warehouse
		target.to_warehouse = source.set_warehouse
		# add row for repack product
		for d in list(target.get("items")):
			row = target.append("items")
			row.t_warehouse = source.set_warehouse
			row.item_code = d.item_code
			row.qty = d.qty
			row.uom = d.uom
			row.stock_uom = d.stock_uom
			row.conversion_factor = d.conversion_factor

	def update_item(source_doc, target_doc, source_parent):
		target_doc.s_warehouse = source_parent.salvage_warehouse

	doclist = get_mapped_doc(
		"Consignment Request",
		source_name,
		{
			"Consignment Request": {
				"doctype": "Stock Entry",
				"field_map": {},
				"field_no_map": ["payment_terms_template"],
				"validation": {"docstatus": ["=", 1]},
			},
			"Consignment Request Item": {
				"doctype": "Stock Entry Detail",
				"field_map": {
					"name": "consignment_item",
					"parent": "consignment_request",
				},
				"postprocess": update_item,
				# "condition": lambda doc: doc.delivered_qty < doc.qty,
			},
		},
		target_doc,
		postprocess,
		ignore_permissions=1,
	)

	return doclist

def get_batch_from_transfer(con_order):
	batch_map = {}
	data = frappe.db.sql("""
		SELECT 
			se.item_code, se.batch_no, sum(se.qty) as qty, se.uom, se.stock_uom, 
			se.conversion_factor, se.consignment_request, se.consignment_item
		FROM
			`tabStock Entry Detail` se
				LEFT JOIN
			`tabStock Entry` s ON s.name = se.parent
		WHERE
				s.stock_entry_type_view = 'Consignment Transfer'
				AND se.consignment_request = %s
				AND s.docstatus = 1
		group by se.item_code, se.batch_no, se.uom
		""", (con_order,), as_dict=1)
	for d in data:
		batch_map.setdefault((d.item_code, d.uom, d.batch_no), d)

	return batch_map

def get_qty_from_transfer(con_order, se_type):
	qty_map = {}
	temp = frappe.db.sql("""
		SELECT 
			se.item_code, se.batch_no, sum(se.qty) as qty, se.uom
		FROM
			`tabStock Entry Detail` se
				LEFT JOIN
			`tabStock Entry` s ON s.name = se.parent
		WHERE
				s.stock_entry_type_view = %s
				AND se.consignment_request = %s
				AND s.docstatus = 1
		group by se.item_code,  se.uom
		""", (se_type, con_order), as_dict=1)
	
	for d in temp:
		qty_map.setdefault((d.item_code, d.uom), d)

	return qty_map

def add_item_from_transfer(doc, cr_name, post_process=None):
	# get all batch from stock entry
	batch_dict = get_batch_from_transfer(cr_name)
	doc.items = []
	for key, batch in batch_dict.items():
		row = doc.append("items")
		row.item_code = batch.get("item_code")
		row.t_warehouse = doc.to_warehouse
		row.s_warehouse = doc.from_warehouse
		row.uom = batch.get("uom")
		row.conversion_factor = batch.get("conversion_factor")
		row.stock_uom = batch.get("stock_uom")
		row.batch_no = batch.get("batch_no")
		row.qty = batch.get("qty")
		post_process(row, batch)
	
	return doc

@frappe.whitelist()
def make_delivery_note(source_name, target_doc=None):
	# take from Consignment Transfer for batching

	def post_process_item(row, batch):
		row.cr_detail = batch.get("consignment_item")
		row.consignment_request = batch.get("consignment_request")

	def postprocess(source, target):
		target.consignment_request = source.name
		add_item_from_transfer(target, source.name, post_process_item)
		target.set_missing_values()

	def update_item(source_doc, target_doc, source_parent):
		target_doc.qty = source_doc.sold_qty - source_doc.delivered_qty
	
	doclist = get_mapped_doc(
		"Consignment Request",
		source_name,
		{
			"Consignment Request": {
				"doctype": "Delivery Note",
				"field_map": {},
				"field_no_map": [""],
				"validation": {"docstatus": ["=", 1]},
			},
			"Consignment Request Item": {
				"doctype": "Delivery Note Item",
				"field_map": {
					"name": "cr_detail",
					"parent": "against_consignment_request",
				},
				"postprocess": update_item,
				"condition": lambda doc: doc.sold_qty > 0,
			},
		},
		target_doc,
		postprocess,
		ignore_permissions=1,
	)

	return doclist

@frappe.whitelist()
def make_sales_invoice(source_name, target_doc=None):
	# take from delivery note for billing

	def postprocess(source, target):
		target.consignment_request = source.name
		target.set_missing_values()

	def update_item(source_doc, target_doc, source_parent):
		target_doc.qty = source_doc.delivered_qty
	
	doclist = get_mapped_doc(
		"Consignment Request",
		source_name,
		{
			"Consignment Request": {
				"doctype": "Sales Invoice",
				"field_map": {},
				"field_no_map": [""],
				"validation": {"docstatus": ["=", 1]},
			},
			"Consignment Request Item": {
				"doctype": "Sales Invoice Item",
				"field_map": {
					"name": "cr_detail",
					"parent": "consignment_request",
				},
				"postprocess": update_item,
				"condition": lambda doc: doc.delivered_qty > 0,
			},
		},
		target_doc,
		postprocess,
		ignore_permissions=1,
	)

	return doclist