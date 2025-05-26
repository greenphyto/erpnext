# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import flt
from frappe.utils.file_manager import save_file
from erpnext.controllers.uob import create_payment_xml
""" TODO
1. calculate total OK
2. set requested by 
3. set approved by
4. get bank number, filter bank
5. filter invoice (submitted and unpaid)

"""

class PaymentApproval(Document):
	def validate(self):
		self.set_requested_by()
		self.validate_data()
		self.process_xml_file()

	def validate_data(self):
		self.validate_invoice()
		self.calculate_amount()

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
		
		invoices = []
		for d in self.invoices:
			bic = frappe.get_value("Bank",d.bank_account_name,"swift_number")
			row = {
				'invoice_number': d.invoice_no,
				'amount': d.amount,
				'creditor_name': d.bank_account_name,
				'creditor_bic': bic,
				'creditor_account': d.supplier_bank_no,
				'remarks': 'Payment invoice',
				'currency': d.currency,
			}
			invoices.append(row)

		bic = frappe.get_value("Bank", self.bank, "swift_number")
		debtor_info = {
			'name': self.bank_account_name,
			'account_number': self.bank_account_no,
			'bic': bic,
			"purpose":self.purpose
		}

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
		file_name = f"payment_export_{frappe.utils.nowdate()}.xml"
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