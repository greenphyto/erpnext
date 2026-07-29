import frappe
import erpnext
from frappe import _
from frappe.utils import flt

from erpnext.selling.doctype.quotation.quotation import Quotation


class QuotationGP(Quotation):
    def validate(self):
        super(QuotationGP, self).validate()
        self.create_lead()

    def create_lead(self):
        if not self.new_customer or self.is_existing_customer:
            return

        self.quotation_to = "Lead"

        lead_name = frappe.db.get_value(
            "Lead", {"company_name": self.new_customer}, "name"
        )
        if not lead_name:
            lead_name = frappe.db.get_value(
                "Lead", {"lead_name": self.new_customer}, "name"
            )

        if not lead_name:
            lead = frappe.get_doc(
                {
                    "doctype": "Lead",
                    "company_name": self.new_customer,
                    "email_id": self.manual_email,
                    "mobile_no": self.manual_mobile_no,
                    "phone": self.manual_tlp,
                    "fax": self.manual_fax,
                    "city": self.manual_city,
                    "state": self.manual_state,
                    "country": self.manual_country,
                }
            )
            lead.insert()
            lead_name = lead.name

        self.party_name = lead_name
        self._create_manual_address_for_lead(lead_name)
        self._create_manual_contact_for_lead(lead_name)

    def _create_manual_address_for_lead(self, lead_name):
        if not (self.manual_address_line and self.manual_city and self.manual_country):
            return

        existing_address = frappe.db.exists(
            "Dynamic Link",
            {
                "parenttype": "Address",
                "link_doctype": "Lead",
                "link_name": lead_name,
            },
        )
        if existing_address:
            return

        address_title = self.new_customer or self.manual_contact_person_name or lead_name
        frappe.get_doc(
            {
                "doctype": "Address",
                "address_title": address_title,
                "address_type": "Billing",
                "address_line1": self.manual_address_line,
                "city": self.manual_city,
                "state": self.manual_state,
                "country": self.manual_country,
                "phone": self.manual_tlp,
                "fax": self.manual_fax,
                "email_id": self.manual_email,
                "links": [{"link_doctype": "Lead", "link_name": lead_name}],
            }
        ).insert()

    def _create_manual_contact_for_lead(self, lead_name):
        if not (
            self.manual_contact_person_name
            or self.manual_mobile_no
            or self.manual_tlp
            or self.manual_email
        ):
            return

        existing_contact = frappe.db.exists(
            "Dynamic Link",
            {
                "parenttype": "Contact",
                "link_doctype": "Lead",
                "link_name": lead_name,
            },
        )
        if existing_contact:
            return

        contact = frappe.get_doc(
            {
                "doctype": "Contact",
                "first_name": self.manual_contact_person_name or self.new_customer,
                "is_primary_contact": 1,
                "links": [{"link_doctype": "Lead", "link_name": lead_name}],
            }
        )

        if self.manual_email:
            contact.add_email(self.manual_email, is_primary=True)
        if self.manual_mobile_no:
            contact.add_phone(self.manual_mobile_no, is_primary_mobile_no=True)
        if self.manual_tlp and self.manual_tlp != self.manual_mobile_no:
            contact.add_phone(self.manual_tlp, is_primary_phone=True)

        contact.insert()

    def get_existing_lead_from_new_customer(self):
        if not self.new_customer:
            return {"clear": 1}

        lead_name = frappe.db.get_value(
            "Lead", {"company_name": self.new_customer}, "name"
        )
        if not lead_name:
            lead_name = frappe.db.get_value(
                "Lead", {"lead_name": self.new_customer}, "name"
            )

        if not lead_name:
            return {"clear": 0}

        lead = frappe.db.get_value(
            "Lead",
            lead_name,
            ["name", "email_id", "mobile_no", "phone", "fax", "city", "state", "country"],
            as_dict=True,
        )

        address_name = frappe.db.get_value(
            "Dynamic Link",
            {
                "parenttype": "Address",
                "link_doctype": "Lead",
                "link_name": lead_name,
            },
            "parent",
        )

        address = {}
        if address_name:
            address = frappe.db.get_value(
                "Address",
                address_name,
                ["address_line1", "city", "state", "country", "phone", "fax", "email_id"],
                as_dict=True,
            )

        return {
            "clear": 0,
            "lead_name": lead_name,
            "manual_address_line": (address or {}).get("address_line1"),
            "manual_city": (address or {}).get("city") or (lead or {}).get("city"),
            "manual_state": (address or {}).get("state") or (lead or {}).get("state"),
            "manual_country": (address or {}).get("country") or (lead or {}).get("country"),
            "manual_tlp": (address or {}).get("phone") or (lead or {}).get("phone"),
            "manual_mobile_no": (lead or {}).get("mobile_no"),
            "manual_email": (address or {}).get("email_id") or (lead or {}).get("email_id"),
        }
