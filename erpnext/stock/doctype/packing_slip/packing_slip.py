# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt


import frappe
from frappe import _
from frappe.contacts.doctype.contact.contact import get_contact_details, get_default_contact
from frappe.contacts.doctype.address.address import get_default_address, get_address_display
from frappe.model import no_value_fields
from frappe.model.document import Document
from frappe.utils import cint, flt
from frappe.utils import safe_abs as abs

from erpnext.controllers.status_updater import StatusUpdater


class PackingSlip(StatusUpdater):
	def __init__(self, *args, **kwargs) -> None:
		super(PackingSlip, self).__init__(*args, **kwargs)
		self.status_updater = [
			{
				"target_dt": "Delivery Note Item",
				"join_field": "dn_detail",
				"target_field": "packed_qty",
				"target_parent_dt": "Delivery Note",
				"target_ref_field": "qty",
				"source_dt": "Packing Slip Item",
				"source_field": "qty",
			},
			{
				"target_dt": "Packed Item",
				"join_field": "pi_detail",
				"target_field": "packed_qty",
				"target_parent_dt": "Delivery Note",
				"target_ref_field": "qty",
				"source_dt": "Packing Slip Item",
				"source_field": "qty",
			},
		]

	def validate(self) -> None:
		from erpnext.utilities.transaction_base import validate_uom_is_integer

		self.validate_delivery_note()
		self.validate_case_nos()
		self.validate_items()

		validate_uom_is_integer(self, "stock_uom", "qty")
		validate_uom_is_integer(self, "weight_uom", "net_weight")

		self.set_missing_values()

	def on_submit(self):
		self.update_prevdoc_status()

	def on_cancel(self):
		self.update_prevdoc_status()

	@frappe.whitelist()
	def fetch_delivery_note(self):
		"""Fetch items from Delivery Note"""
		if not self.delivery_note:
			frappe.throw(_("Please select a Delivery Note"))
		
		self.items = []
		dn = frappe.get_doc("Delivery Note", self.delivery_note)
		
		# Set letter head from Delivery Note
		if dn.letter_head:
			self.letter_head = dn.letter_head
		
		# Add items from Delivery Note Items
		for item in dn.items:
			# Skip if item is a Product Bundle
			if frappe.db.exists("Product Bundle", {"new_item_code": item.item_code}):
				continue
			
			self.append("items", {
				"item_code": item.item_code,
				"item_name": item.item_name,
				"description": item.description,
				"qty": item.qty,
				"stock_uom": item.uom,
				"unit_weight": item.weight_per_unit,
				"dn_detail": item.name,
			})
		
		# Add items from Packed Items
		for packed_item in dn.packed_items:
			self.append("items", {
				"item_code": packed_item.item_code,
				"item_name": packed_item.item_name,
				"batch_no": packed_item.batch_no,
				"description": packed_item.description,
				"qty": packed_item.qty,
				"pi_detail": packed_item.name,
			})
		
		# Set missing values
		self.set_missing_values()

	def validate_delivery_note(self):
		"""Raises an exception if the `Delivery Note` status is not Draft"""

		if cint(frappe.db.get_value("Delivery Note", self.delivery_note, "docstatus")) == 2:
			frappe.throw(
				_("A Packing Slip can only be created for Draft/Submitted Delivery Note.").format(self.delivery_note)
			)

	def validate_case_nos(self):
		"""Validate if case nos overlap. If they do, recommend next case no."""

		if cint(self.from_case_no) <= 0:
			frappe.throw(
				_("The 'From Package No.' field must neither be empty nor it's value less than 1.")
			)
		elif not self.to_case_no:
			self.to_case_no = self.from_case_no
		elif cint(self.to_case_no) < cint(self.from_case_no):
			frappe.throw(_("'To Package No.' cannot be less than 'From Package No.'"))
		else:
			ps = frappe.qb.DocType("Packing Slip")
			res = (
				frappe.qb.from_(ps)
				.select(
					ps.name,
				)
				.where(
					(ps.delivery_note == self.delivery_note)
					& (ps.docstatus == 1)
					& (
						(ps.from_case_no.between(self.from_case_no, self.to_case_no))
						| (ps.to_case_no.between(self.from_case_no, self.to_case_no))
						| ((ps.from_case_no <= self.from_case_no) & (ps.to_case_no >= self.from_case_no))
					)
				)
			).run()

			if res:
				frappe.throw(
					_("""Package No(s) already in use. Try from Package No {0}""").format(
						self.get_recommended_case_no()
					)
				)

	def validate_items(self):
		for item in self.items:
			if item.qty <= 0:
				frappe.throw(_("Row {0}: Qty must be greater than 0.").format(item.idx))

			if not item.dn_detail and not item.pi_detail:
				frappe.throw(
					_("Row {0}: Either Delivery Note Item or Packed Item reference is mandatory.").format(
						item.idx
					)
				)
			DocType = frappe.qb.DocType("Delivery Note Item" if item.dn_detail else "Packed Item")
			remaining_qty = frappe.db.get_value(
				"Delivery Note Item" if item.dn_detail else "Packed Item",
				{"name": item.dn_detail or item.pi_detail, "docstatus": 0},
				"sum(qty - packed_qty)",
			)

			if remaining_qty is None:
				frappe.throw(
					_("Row {0}: Please provide a valid Delivery Note Item or Packed Item reference.").format(
						item.idx
					)
				)
			elif remaining_qty <= 0:
				frappe.throw(
					_("Row {0}: Packing Slip is already created for Item {1}.").format(
						item.idx, frappe.bold(item.item_code)
					)
				)
			elif item.qty > remaining_qty:
				frappe.throw(
					_("Row {0}: Qty cannot be greater than {1} for the Item {2}.").format(
						item.idx, frappe.bold(remaining_qty), frappe.bold(item.item_code)
					)
				)

	def set_missing_values(self):
		# Set shipper information from Delivery Note
		if self.delivery_note:
			dn = frappe.get_doc("Delivery Note", self.delivery_note)
			# Set shipper as company from DN
			if not self.shipper and dn.company:
				self.shipper = dn.company
			
			# Set shipper address name (Link) from DN company_address or fetch from Company
			self.shipper_address_name = get_default_address("Company", dn.company)
			self.shipper_address = get_address_display(self.shipper_address_name).replace("<br>", "\n")
			self.country_of_origin = frappe.db.get_value("Address", self.shipper_address_name, "country")
			
			# Set shipper contact from Company default contact
			self.shipper_contact_name = get_default_contact("Company", dn.company)
			if self.shipper_contact_name:
				self.shipper_contact = get_contact_details(self.shipper_contact_name).get("contact_display")

			if not self.importer and dn.customer:
				self.importer = dn.customer	
			
			self.importer_address_name = dn.shipping_address_name
			self.importer_address = get_address_display(dn.shipping_address_name).replace("<br>", "\n")
			self.importer_contact_name = dn.contact_person
			if self.importer_contact_name:
				self.importer_contact = get_contact_details(self.importer_contact_name).get("contact_display")
			self.destination = frappe.db.get_value("Address", dn.shipping_address_name, "country")
		for item in self.items:
			weight_per_unit, weight_uom = frappe.db.get_value(
				"Item", item.item_code, ["weight_per_unit", "weight_uom"]
			)
			if weight_uom and not item.weight_uom:
				item.weight_uom = weight_uom
		
		self.calculate_net_total_pkg()
		self.set_case()

	def get_recommended_case_no(self):
		"""Returns the next case no. for a new packing slip for a delivery note"""

		return (
			cint(
				frappe.db.get_value(
					"Packing Slip",
					{"delivery_note": self.delivery_note, "docstatus": 1},
					["max(to_case_no)"],
				)
			)
			+ 1
		)
	
	def set_case(self):
		self.from_case_no = self.get_recommended_case_no()
		self.to_case_no = self.from_case_no + self.get_to_case_no()
		print(1217, self.to_case_no)


	def get_to_case_no(self):
		return sum([d.cartons for d in self.get("items")])

	def calculate_net_total_pkg(self):
		self.net_weight_uom = self.items[0].weight_uom if self.items else None
		self.gross_weight_uom = self.net_weight_uom
		self.unit_per_carton = self.unit_per_carton or 12
		self.carton_weight = self.carton_weight or 0.435

		net_weight_pkg = 0
		gross_weight_pkg = 0
		for item in self.items:
			item.weight_uom = self.net_weight_uom
			item.cartons = cint(cint(item.qty)/self.unit_per_carton)
			carton_weight = item.cartons * self.carton_weight
			item.net_weight = flt(item.unit_weight) * flt(item.qty)
			item.gross_weight = item.net_weight + carton_weight
			net_weight_pkg += flt(item.net_weight)
			gross_weight_pkg += flt(item.gross_weight)
			item.uom_view = "{} Gr".format(cint(item.unit_weight * 1000))

		self.net_weight_pkg = round(net_weight_pkg, 2)
		self.gross_weight_pkg = round(gross_weight_pkg, 2)


@frappe.whitelist()
def item_details(doctype, txt, searchfield, start, page_len, filters):
	from erpnext.controllers.queries import get_match_cond

	return frappe.db.sql(
		"""select name, item_name, description from `tabItem`
				where name in ( select item_code FROM `tabDelivery Note Item`
	 						where parent= %s)
	 			and %s like "%s" %s
	 			limit  %s offset %s """
		% ("%s", searchfield, "%s", get_match_cond(doctype), "%s", "%s"),
		((filters or {}).get("delivery_note"), "%%%s%%" % txt, page_len, start),
	)

def get_company_billing_address(company):
    """
    Fetch default billing address for a given Company.
    Returns address name and full display.
    """
    # Cari primary billing address
    address = frappe.db.get_value(
        "Address",
        {
            "link_doctype": "Company",
            "link_name": company,
            "is_primary_address": 1,
        },
        ["name", "address_line1", "address_line2", "city", "state", "pincode", "country"],
        as_dict=True
    )

    if not address:
        # Fallback: ambil address pertama yang terkait company
        address_name = frappe.db.get_value(
            "Dynamic Link",
            {
                "link_doctype": "Company",
                "link_name": company,
                "parenttype": "Address"
            },
            "parent"
        )
        if address_name:
            address = frappe.db.get_value(
                "Address",
                address_name,
                ["name", "address_line1", "address_line2", "city", "state", "pincode", "country"],
                as_dict=True
            )

    if not address:
        return None

    # Format display
    parts = [
        address.get("address_line1"),
        address.get("address_line2"),
        address.get("city"),
        address.get("state"),
        address.get("pincode"),
        address.get("country"),
    ]
    address["display"] = ", ".join(filter(None, parts))

    return address