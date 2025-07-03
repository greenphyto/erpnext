# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe, os
from frappe.model.document import Document
from frappe.utils import flt, cint, getdate, get_link_to_form
from frappe.utils.file_manager import save_file
from erpnext.controllers.uob import create_payment_xml
from erpnext.controllers.uob import UOBAPI, get_country_code

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
		self.set_status()
		self.set_requested_by()
		self.validate_data()
		self.process_xml_file()
		self.set_batch_number()

	def validate_data(self):
		self.validate_bank()
		self.validate_payment()
		self.validate_invoice()
		self.calculate_amount()

	def validate_bank(self):
		bic = frappe.get_value("Bank", self.bank, "swift_number")
		if not bic:
			frappe.throw(_(f"Missing BIC/SWIFT for Bank <b>{self.bank}</b>"))
		
		if "UOVB" not in bic:
			frappe.throw(_(f"This transaction requires a UOB bank account. Please select a valid UOB account to proceed."))

		account_no, account_name = frappe.db.get_value("Bank Account", self.bank_account, ["bank_account_no", "bank_account_name"]) or ("", "")
		if not account_no or not account_name:
			links = get_link_to_form("Bank Account", self.bank_account)
			frappe.throw(_(f"Please update the <b>Bank Account No</b> and <b>Bank Account Name</b> for {links}"))

	def set_status(self):
		if self.docstatus == 0 and self.is_new():
			self.status = "Draft"

	def update_payment_status(self, process_id, transactions=[]):
		# sync with L1,2,3,4 abnd when any riject
		if cint(self.process_id) > cint(process_id):
			return
		
		self.process_id = process_id

		for tr in transactions:
			invoice_no = tr['invoice_no']
			account_no = tr['account_no']
			
			if tr["result"] == "ACCP":
				status = "Success"
			else:
				status = "Failed"

			for row in self.get("invoices"):
				if row.invoice_no == invoice_no and row.bank_account_no == account_no:
					row.status = status
					if row.status == "Failed":
						row.error_code = tr["error_code"]
					
					row.db_update()

		self.sync_status(db_update=True)

	def sync_status(self, db_update=False):
		tr_success = 0
		tr_len = len(self.get("invoices"))
		tr_comp = 0
		for d in self.get("invoices"):
			if d.status == "Success":
				tr_comp += 1

		if tr_comp:
			tr_success = tr_comp/tr_len*100 

		if self.docstatus == 0:
			# Draft
			self.status = "Draft"
		elif self.docstatus == 1:
			# this is based on workflow:
			# Pending
			# Approved
			# Rejected
			if self.process_id == 1:
				# Received
				self.status = "Received"
			elif self.process_id == 2:
				# Failed
				self.status = "Failed"
			elif self.process_id == 3:
				# In Progress
				self.status = "In Progress"
			elif self.process_id == 4:
				if tr_success == 100:
					# Complete
					self.status = "Complete"
				else:
					# Partially Complete
					self.status = "Partially Complete"
			else:
				self.status = "Failed"
		else:
			# Cancelled
			self.status = "Cancelled"

		if db_update:
			self.db_update()

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
			if self.payment_method in ("TT", "MEPS", "IAFT"):
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
		settings = frappe.get_single("UOB Integration Settings")
		env = settings.env
		dummy = env != "Production"

		def change_to_dummy_bic(bic):
			index = 7
			if not bic or index < 0 or index >= len(bic):
				return bic
			return bic[:index] + "0" + bic[index + 1:]

		# other information
		tax_id = frappe.get_value("Company", self.company, "tax_id")

		invoices = []
		for d in self.invoices:
			bic = frappe.get_value("Bank",d.supplier_bank,"swift_number", debug=0)
			if dummy:
				bic = change_to_dummy_bic(bic)

			doc = frappe.get_doc("Purchase Invoice", d.invoice_no)
			doc_name = doc.name[:-5]
			if len(doc.bill_no or "") < 10:
				ins_start = "{}-{}".format(doc.bill_no or "*", get_date_simple(doc.bill_date)[:-2])
			else:
				ins_start = doc.bill_no
				
			ins_end = "{}-{}".format(doc_name, get_date_simple(doc.posting_date)[:-2])
			email = settings.remitance_email_dummy
			address = None
			if doc.supplier_address:
				addr = frappe.get_doc("Address", doc.supplier_address)
				address = {
					"address_line":addr.address_line1,
					"postal_code":addr.pincode,
					"country": get_country_code(addr.country),
				}
			row = {
				'invoice_number': d.invoice_no,
				'amount': d.amount,
				'creditor_name': d.bank_account_name,
				'creditor_bic': bic,
				'creditor_account': d.bank_account_no,
				'remarks': 'Payment invoice',
				'currency': d.currency,
				"instruction_start":ins_start,
				"instruction_end":ins_end,
				"email":email,
				"country": get_country_code("Singapore"),
				"address": address,
				"remitence_address": address
			}
			invoices.append(row)

		bic = frappe.get_value("Bank", self.bank, "swift_number")
		if dummy:
			bic = change_to_dummy_bic(bic)
		file_name = self.get_file_name()
		batch = self.name.replace("-", "")
		debtor_info = {
			'company_name': self.company,
			'name': self.bank_account_name,
			'account_number': self.bank_account_no,
			'bic': bic,
			"purpose":self.purpose,
			"batch":batch,
			"company_id": tax_id,
			"dummy_bic": bic,
			"msg_id": file_name
		}
		debtor_info.update(self.method)

		doc = self.create_xml_file(invoices, debtor_info, filepath=filepath)

		# upload
		if not filepath:
			self.upload_xml(doc)
		else:
			return filepath


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
			doc = save_file(
				fname=file_name,
				content=xml_content,
				dt=doc_type,
				dn=doc_name,
				folder="Home/Attachments",
				is_private=1,  # Restrict access to authorized users
			)
		
			return doc
		
	def upload_xml(self,file_doc):
		uob = UOBAPI()
		file_name = self.get_file_name()
		file_path = os.path.join(frappe.get_site_path("private", "files"), os.path.basename(file_doc.file_url))
		absolute_path = os.path.abspath(file_path)
		res = uob.upload_bank_tx(absolute_path, file_name)

	def get_file_name(self):
		dates = getdate(self.posting_date).strftime("%d%m")
		n = self.batch_number
		number = f"{n:03d}"
		file_name = f"PA113{dates}{number}.xml"
		return file_name

def get_date_simple(value):
	return getdate(value).strftime("%y%m%d")