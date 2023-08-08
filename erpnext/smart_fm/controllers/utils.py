import frappe
from frappe.utils import cint, getdate

def get_day_diff(date1, date2):
    delta = getdate(date2) - getdate(date1)
    return delta.days

def create_contact(data, customer, doctype="Customer"):
	email = data.get("email", None)
	phone = data.get("phone", None)

	if not email and not phone:
		return

	contact = frappe.new_doc("Contact")
	contact.first_name = data.get("first_name")
	contact.last_name = data.get("last_name")
	contact.is_primary_contact = 1
	contact.is_billing_contact = 1

	if phone:
		contact.add_phone(phone, is_primary_mobile_no=1, is_primary_phone=1)

	if email:
		contact.add_email(email, is_primary=1)

	contact.append("links", {"link_doctype": doctype, "link_name": customer.name})

	contact.flags.ignore_mandatory = True
	contact.save()


def create_address(raw_data, customer, doctype="Customer"):
	address = frappe.new_doc("Address")

	address.address_line1 = raw_data.get("address_1", "Not Provided")
	address.address_line2 = raw_data.get("address_2", "Not Provided")
	address.city = raw_data.get("city", "Not Provided")
	address.address_type = raw_data.get("address_type")
	address.country = frappe.get_value("Country", {"code": raw_data.get("country", "IN").lower()})
	address.state = raw_data.get("state")
	address.pincode = raw_data.get("postcode")
	address.phone = raw_data.get("phone")
	address.email_id = raw_data.get("email_id")
	address.append("links", {"link_doctype": doctype, "link_name": customer.name})

	address.flags.ignore_mandatory = True
	print("Address", address.name)
	address.save()