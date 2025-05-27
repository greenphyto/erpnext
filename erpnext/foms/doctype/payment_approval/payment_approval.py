# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import flt, cint, getdate
from frappe.utils.file_manager import save_file
from erpnext.controllers.uob import create_payment_xml
from frappe import _
""" TODO
1. calculate total OK
2. set requested by 
3. set approved by
4. get bank number, filter bank
5. filter invoice (submitted and unpaid)

"""

COUNTRY_CODE = "SG"


class PaymentApproval(Document):
	def validate(self):
		self.set_requested_by()
		self.validate_data()
		self.process_xml_file()
		self.set_batch_number()

	def validate_data(self):
		self.validate_payment()
		self.validate_invoice()
		self.calculate_amount()

	def set_batch_number(self):
		if not self.batch_number and "PAY" in self.name:
			self.batch_number = cint(self.name.split("-")[1][-4:])

	def validate_payment(self):
		self.method = {
			"type":"",
			"method":"",
			"property":""
		}
		property = {
			"PayNow":"PAYNOW",
			"CHQ":"CCHQ",
			"CO":"BCHQ"
		}
		if self.payment_type == "Transfer":
			self.method["type"] = "TRF"
			self.method["property"] = ""
			if self.payment_method == "TT":
				self.method["method"] = "URGP"
				self.payment_property = ""
			elif self.payment_method == "FAST":
				self.method["method"] = "URNS"
			elif self.payment_method == "IBG":
				self.method["method"] = "NURG"
			elif self.payment_method == "IBG Express":
				self.method["method"] = "BOOK"
				self.payment_property = ""
			else:
				frappe.throw(_("Payment Method must be set."))

			
		else:
			self.method["type"] = "CHK"
			self.method["method"] = ""
			self.payment_method = ""
			if not self.payment_property:
				frappe.throw(_("Payment Property must be set."))

			self.method["property"] = property.get(self.payment_property)

	def set_requested_by(self):
		if not self.requested_by:
			self.requested_by = frappe.session.user

	def validate_invoice(self):
		# validate invoice
		# validate outstanding
		already_add = []
		for d in list(self.get("invoices")):
			if d.invoice_no in already_add:
				frappe.msgprint(f"Removed row {d.idx}, invoice is duplicate.")
				self.remove(d)
				continue

			data = frappe.db.get_value("Purchase Invoice", d.invoice_no, [
				'supplier', 
				'outstanding_amount', 
				'docstatus', 
				'currency', 
				'conversion_rate',
			], as_dict=1)
			if flt(data.docstatus) != 1:
				frappe.msgprint(f"Removed Row {d.idx}, only for submitted invoice!")
				self.remove(d)
				continue

			if flt(data.outstanding_amount) <= 0:
				frappe.msgprint(f"Removed Row {d.idx}, invoice {d.invoice_no} not have outstanding amount")
				self.remove(d)
				continue
			
			already_add.append(d.invoice_no)
			d.supplier = data.supplier
			d.amount = data.outstanding_amount
			d.currency = data.currency
			d.exchange_rate = data.conversion_rate
			# validate bank own from the supplier


	def calculate_amount(self):
		total = 0
		for d in self.get("invoices"):
			total += flt(d.basic_amount)
		
		self.total_amount = total
 
	def process_xml_file(self, filepath=""):
		if self.workflow_state != "Approved" and self.docstatus != 1:
			return
		
		self.validate_payment()

		# other information
		tax_id = frappe.get_value("Company", self.company, "tax_id")

		invoices = []
		for d in self.invoices:
			bic = frappe.get_value("Bank",d.bank_account_name,"swift_number")
			doc = frappe.get_doc("Purchase Invoice", d.invoice_no)
			ins_start = "{}{}-BILL:{}-DATE:{}".format(get_date_simple(self.posting_date), self.payment_method, doc.bill_no, get_date_simple(doc.bill_date))
			ins_end = "GP.INV:{}-DATE:{}".format(doc.name, get_date_simple(doc.posting_date))
			row = {
				'invoice_number': d.invoice_no,
				'amount': d.amount,
				'creditor_name': d.bank_account_name,
				'creditor_bic': bic,
				'creditor_account': d.supplier_bank_no,
				'remarks': 'Payment invoice',
				'currency': d.currency,
				"instruction_start":ins_start,
				"instruction_end":ins_end
			}
			invoices.append(row)

		bic = frappe.get_value("Bank", self.bank, "swift_number")
		file_name = self.get_file_name()
		debtor_info = {
			'company_name': self.company,
			'name': self.bank_account_name,
			'account_number': self.bank_account_no,
			'bic': bic,
			"purpose":self.purpose,
			"batch":self.name,
			"company_id": tax_id,
			"msg_id": file_name
		}
		debtor_info.update(self.method)

		return self.create_xml_file(invoices, debtor_info, filepath=filepath)

	def create_xml_file(self, invoices, debtor_info, filepath=""):
		"""
		Saves XML content as a File in ERPNext and links it to a Payment Approval.
		
		Args:
			xml_content (str): Generated XML string (ISO 20022 format).
			payment_approval_name (str): Name of the Payment Approval doc (e.g., "PAY-001").
		"""

		xml_content = create_payment_xml(invoices, debtor_info, filepath=filepath)

		# Validate inputs
		if not xml_content:
			frappe.throw("XML content cannot be empty.")
		
		# Define file properties
		file_name = self.get_file_name()
		doc_type = "Payment Approval"
		doc_name = self.name
		
		# Save the file to ERPNext
		if not filepath:
			save_file(
				fname=file_name,
				content=xml_content,
				dt=doc_type,
				dn=doc_name,
				folder="Home/Attachments",
				is_private=1,  # Restrict access to authorized users
			)
		
		return True

	def get_file_name(self):
		dates = getdate(self.posting_date).strftime("%d%m")
		n = self.batch_number
		number = f"{n:03d}"
		file_name = f"{COUNTRY_CODE}_PA113{dates}{number}.xml"
		return file_name

def get_date_simple(value):
	return getdate(value).strftime("%y%m%d")