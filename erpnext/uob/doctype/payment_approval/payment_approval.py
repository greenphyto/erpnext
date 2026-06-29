# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe, os, re
from frappe.model.document import Document
from frappe.utils import flt, cint, getdate, get_datetime, cstr, get_time, get_link_to_form, add_days
from frappe.utils.file_manager import save_file
from frappe.desk.form.utils import add_comment
from erpnext.controllers.uob import create_payment_xml
from erpnext.controllers.uob import UOBAPI, get_country_code
from frappe.model.mapper import get_mapped_doc
from erpnext.accounts.doctype.payment_entry.payment_entry import get_payment_entry
from frappe.contacts.doctype.address.address import get_company_address


from frappe import _
""" TODO
1. calculate total OK
2. set requested by 
3. set approved by
4. get bank number, filter bank
5. filter invoice (submitted and unpaid)

"""

class PaymentApproval(Document):
	def validate(self):
		self.set_status()
		self.set_requested_by()
		self.validate_data()
		self.process_xml_file()
		self.set_batch_number()

	def validate_data(self):
		self.validate_paynow()
		self.validate_reqd_data()
		self.validate_select()
		self.validate_payment()
		self.validate_bank_number()
		self.validate_invoice()
		self.calculate_amount()

	def validate_paynow(self):
		for d in self.invoices:
			if not d.proxy_number and self.payment_method == "PayNow":
				frappe.throw(_("Row {}, Bank number <u>{}</u> not available for PayNow transfers".format(d.idx, d.supplier_bank_no)))

	def on_submit(self):
		self.update_apporval_date()
		self.remove_unselected_row()

	def on_cancel(self):
		if self.status in ['Approved', 'Received', 'In Progress', 'Complete']:
			frappe.throw(_("Cannot cancel becuase payment already made"))

	def validate_select(self):
		select_row = []
		for d in self.invoices:
			d.selected = cint(d.selected)
			if d.selected:
				select_row.append(d.name)
		
		if not select_row:
			frappe.throw(_("Please select at least 1 invoice to paid"))

	def update_apporval_date(self):
		if self.status == "Approved":
			now = get_datetime()
			self.approved_date = getdate(now)
			self.time = get_time(now)

	def validate_bank(self):
		bic = frappe.get_value("Bank", self.bank, "swift_number")
		if not bic:
			frappe.throw(_(f"Missing BIC/SWIFT for Bank <b>{self.bank}</b>"))
		
		if "UOVB" not in bic:
			frappe.throw(_(f"This transaction requires a UOB bank account. Please select a valid UOB account to proceed."))

		bank_num = frappe.get_doc("Bank Number", self.supplier_bank_no)
		account_no, account_name, currency = bank_num.bank_account_no, bank_num.bank_account_name, bank_num.currency
		if self.payment_method == "PayNow" and not bank_num.proxy_number:
			frappe.throw(_("Row {}, Bank number <u>{}</u> not have PayNow number".format(d.idx, d.supplier_bank_no)))
		if not account_no or not account_name:
			links = get_link_to_form("Bank Account", self.bank_account)
			frappe.throw(_(f"Please update the <b>Bank Account No</b> and <b>Bank Account Name</b> for {links}"))

		if self.currency != currency:
			frappe.throw(_(f"Bank account is not {self.currency}, please select another bank account"))

		for d in self.invoices:
			if d.currency != currency:
				frappe.throw(_(f"Row {d.idx}, invoice currency ({d.currency}) different with payee bank account ({currency})"))

	def set_status(self):
		if self.docstatus == 0 and self.is_new():
			self.status = "Draft"

	def validate_bank_number(self):
		for d in self.get("invoices"):
			if check_branch_code_mandatory(d.supplier_bank, d.bank_account_no):
				frappe.throw(f"Row {d.idx}, Bank account for HSBC/OCBC/SBI should be at least 10 digits")

	def update_payment_status(self, process_id, transactions=[], file_date="", error_message=""):
		# sync with L1,2,3,4 and when any riject
		if cint(self.process_id) > cint(process_id):
			return
		
		self.process_id = process_id

		for tr in transactions:
			account_no = tr['account_no']
			amount = flt(tr['amount'])
			
			if tr["result"] == "ACCP":
				status = "Success"
			elif tr["result"] in ["RCVD", "ACTC"]:
				status = ""
			else:
				status = "Failed"

			for row in self.get("invoices"):
				if row.bank_account_no == account_no  or account_no == "*" or row.proxy_number == account_no:
					row.status = status
					if row.status == "Failed":
						row.error_code = tr["error_code"]
						row.error_info = tr["error_info"]
					else:
						row.error_code = ""
						row.error_info = ""
						use_amount = 0
						if amount >= row.amount:
							amount -= row.amount
							use_amount = flt(row.amount)
						# add tollerance $1
						elif row.amount - amount < 1:
							use_amount = row.amount
							amount = 0
						else:
							use_amount = amount
							amount = 0
													
						# add amount paid
						# if use_amount:
						# 	self.create_payment_entry(row, tr, use_amount)
					
					row.db_update()
			
			if account_no == "*":
				break
		
		if not error_message:
			# try find from row
			temp = ['{}: {}'.format(d.error_code, d.error_info) for d in self.get("invoices") if d.status == "Failed" and d.error_code]
			error_message = "<br> ".join(temp)

		self.update_on = get_datetime(file_date)
		self.sync_status(db_update=True, error_message=error_message)
	
	def create_payment_entry(self, row, tr, amount):
		pi_name = row.invoice_no
		docstatus, status = frappe.db.get_value("Purchase Invoice", pi_name, ["docstatus", "status"]) or (0, "")
		# if docstatus != 1 or status == "Paid":
		# 	return
		
		cheque_no = tr['reff_no']
		
		# create PE
		pe = get_payment_entry(dt="Purchase Invoice", dn=pi_name)
		pe.bank_account = self.get_bank_account(tr['bank_account'])
		pe.mode_of_payment = "Bank Draft"
		pe.paid_amount = amount
		pe.reference_no = cheque_no
		pe.bank = frappe.get_value("Bank Account", pe.bank_account, "bank")
		pe.reference_date = getdate(tr['reff_date'])
		pe.additional_info = self.get_transfer_info(row, tr)
		pe.auto_generated = 1
		pe.insert(ignore_permissions=1)
		pe.submit()

	def get_bank_account(self, account_no):
		bank_name = frappe.db.get_value("Bank Account", {"bank_account_no":account_no}, "name")
		if not bank_name:
			bank_name = frappe.db.get_value("Bank Account", {"proxy_number":account_no}, "name")
		return bank_name

	def get_transfer_info(self, row, tr):
		txt = f"""
		Statement Date: { getdate(tr['reff_date']).strftime("%d-%m-%Y") }
		Initiated Date: { self.request_date.strftime("%d-%m-%Y") }
		Payment No: { tr['remarks'] }
		Invoice: { row.invoice_no }
		"""
		txt = txt.replace("\t", "")
		return txt

	def sync_status(self, db_update=False, error_message=""):
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
			elif self.process_id == 4 and self.status not in ["Failed", "Partially Complete"]:
				if tr_success == 100:
					# Complete
					self.status = "Complete"
					self.transfer_date = self.update_on
				elif tr_success > 0:
					# Partially Complete
					self.status = "Partially Complete"
				else:
					self.status = "Failed"
			else:
				self.status = "Failed"

		else:
			# Cancelled
			self.status = "Cancelled"

		if self.status == "Failed":
			self.error_message = error_message

		old_doc = self.get_doc_before_save()
		if not old_doc or old_doc.get("status") != self.status:
			if not frappe.db.exists("Comment", {
				"comment_type":"Workflow", 
				"reference_doctype": self.doctype,
				"reference_name": self.name,
				"content": self.status
			}):
				comment = frappe.new_doc("Comment")
				comment.update(
					{
						"comment_type": "Workflow",
						"reference_doctype": self.doctype,
						"reference_name": self.name,
						"comment_email": frappe.session.user,
						"content": self.status
					}
				)
				comment.insert(ignore_permissions=True)

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
			elif self.payment_method == "PayNow":
				self.method["method"] = "URNS"
				self.method["property"] = "PAYNOW"
				self.payment_property = "PAYNOW"
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
				frappe.throw(f"row {d.idx}, invoice is duplicate.")
				self.remove(d)
				continue

			# pull essential fields from Purchase Invoice (source document)
			data = frappe.db.get_value(
				"Purchase Invoice",
				d.invoice_no,
				[
					"supplier",
					"company",
					"outstanding_amount",
					"docstatus",
					"currency",
					"conversion_rate",
					"bank_number",
				],
				as_dict=1,
			)
			if not data:
				frappe.throw(_(f"Purchase Invoice {d.invoice_no} Not Found"))
				
			if flt(data.docstatus) != 1:
				frappe.throw(f"Row {d.idx}, only for submitted invoice!")
				self.remove(d)
				continue

			if flt(data.outstanding_amount) <= 0:
				frappe.throw(f"Row {d.idx}, invoice {d.invoice_no} not have outstanding amount")
				self.remove(d)
				continue

			# company must match current document
			if cstr(data.company) != cstr(self.company):
				frappe.throw(_(f"Row {d.idx}, invoice company {data.company} must match Payment Approval company {self.company}."))

			if d.currency != self.currency:
				frappe.throw(_(f"Row {d.idx}, cannot use invoice with currency except {self.currency}. Please change the invoice."))
			
			# find another exist approval with same invoice use
			temp = frappe.db.sql("select name, docstatus, parent from `tabPayment Invoice List` where parent != %s and invoice_no = %s and docstatus != 2 and status !='Failed' ", (self.name, d.invoice_no), as_dict=1)
			if temp:
				temp = temp[0]
				frappe.throw(_(f"Row {d.idx}, Invoice No <b>{d.invoice_no}</b> already in progress, please select another invoice."))

			# ensure row values reflect source + current document
			# party/supplier
			d.party = data.supplier
			# currency and rate from PI
			d.currency = data.currency
			d.exchange_rate = data.conversion_rate
			# amounts (keep amount and basic_amount consistent with outstanding)
			d.amount = data.outstanding_amount
			d.basic_amount = data.outstanding_amount

			# fill supplier bank number: prefer row value, fallback to PI.bank_number
			bank_number_name = d.supplier_bank_no
			if not bank_number_name:
				frappe.throw(_(f"Row {d.idx}, Supplier Bank No is required for supplier {data.supplier}."))

			bn = frappe.get_doc("Bank Number", bank_number_name)
			if not bn:
				frappe.throw(_(f"Row {d.idx}, Bank Number {bank_number_name} not found."))

			# bank number must belong to this supplier
			if cstr(bn.party_type) != "Supplier" or cstr(bn.party) != cstr(data.supplier):
				frappe.throw(_(f"Row {d.idx}, Bank Number {bank_number_name} does not belong to supplier {data.supplier}."))

			# bank currency must match PA currency and row currency
			if cstr(bn.currency) != cstr(self.currency):
				frappe.throw(_(f"Row {d.idx}, Bank Number currency {bn.currency} must match Payment Approval currency {self.currency}."))

			# set bank fields on row to reflect current bank number
			d.supplier_bank_no = bank_number_name
			d.supplier_bank = bn.bank
			d.bank_account_no = bn.bank_number
			d.proxy_number = bn.proxy_number
			d.bank_account_name = bn.bank_account_name
			d.branch_code = bn.branch_code
			d.swift = bn.swift

			already_add.append(d.invoice_no)

	def calculate_amount(self):
		total = 0
		for d in self.get("invoices"):
			total += flt(d.basic_amount)
		
		self.total_amount = total

	def validate_reqd_data(self):
		# TAX ID
		tax_id = frappe.get_value("Company", self.company, "tax_id")
		if not tax_id:
			frappe.throw(_(f"Company tax ID is missing, please set to Company {self.company}"))
		
		# Bank Account
		company = frappe.db.get_value("Bank Account", self.bank_account, "company")
		if self.company != company:
			frappe.throw(_(f"Bank Account <b>{self.bank_account}</b> not belong to {self.company}"))

	def process_xml_file(self, filepath=""):
		workflow_state = self.get("workflow_state") or self.get("status")
		if workflow_state != "Approved" and self.docstatus != 1:
			return

		selected = [x.name for x in self.invoices if x.selected]
		if not selected:
			return
		
		self.validate_payment()
		settings = frappe.get_single("UOB Integration Settings")
		env = settings.env
		dummy = env != "Production"

		def change_to_dummy_bic(bic, index=7):
			bic = (bic or "").strip()  # pastikan bic selalu string, bukan None
			if index < 0 or index >= len(bic):
				return bic + "0"
			return bic[:index] + "0" + bic[index + 1:]

		# other information
		tax_id = frappe.get_value("Company", self.company, "tax_id")

		invoices = []
		group_invoices = self.get_invoice_group()
		batch = self.name.replace("-", "")

		idx = 0
		for d in group_invoices:
			bic = frappe.get_value("Bank",d.supplier_bank,"swift_number", debug=0)
			if dummy:
				bic = change_to_dummy_bic(bic)
				
			# if include branch code
			bank_account_no = cstr(d.bank_account_no) if self.payment_method != "PayNow" else cstr(d.proxy_number)

			doc = frappe.get_doc("Purchase Invoice", d.invoice_no)
			doc_name = doc.name[:-5]
			if len(doc.bill_no or "") < 10:
				ins_start = "{}-{}".format(doc.bill_no or "*", get_date_simple(doc.bill_date)[:-2])
			else:
				ins_start = doc.bill_no
				
			ins_end = "{}-{}".format(doc_name, get_date_simple(doc.posting_date)[:-2])
			email = settings.remitance_email_dummy
			address = {}
			if doc.billing_address:
				addr = frappe.get_doc("Address", doc.billing_address)
				address = {
					"address_line":addr.address_line1,
					"postal_code":addr.pincode,
					"country": get_country_code(addr.country),
					"address_line1": addr.address_line1,
					"address_line2": addr.address_line2,
					"city": addr.city,
					"state": addr.state
				}
			row = {
				'invoice_number': d.invoice_no,
				'amount': d.amount,
				'creditor_name': d.bank_account_name,
				'creditor_bic': bic,
				'creditor_account': bank_account_no,
				'remarks': 'Payment invoice',
				'currency': d.currency,
				"instruction_start":ins_start,
				"instruction_end":ins_end,
				"email":email,
				"country": d.country,
				"address": address,
				"remitence_address": address,
				"proxy_type":d.proxy_type,
				"batch_id":d.batch_id,
				"invoices":[]
			}
			for inv in d['invoices']:
				row['invoices'].append({
					"invoice_number": inv.bill_no or inv.invoice_no,
					"amount": inv.amount,
					"currency": inv.currency
				})
			invoices.append(row)
			idx +=1

		bic = frappe.get_value("Bank", self.bank, "swift_number")
		if dummy:
			bic = change_to_dummy_bic(bic)
		file_name = self.get_file_name()
		address = {}
		if comp_address := get_company_address(self.company):
			addr = frappe.get_doc("Address", comp_address.get("company_address"))
			address = {
				"address_line":addr.address_line1,
				"postal_code":addr.pincode,
				"country": get_country_code(addr.country),
				"address_line1": addr.address_line1,
				"address_line2": addr.address_line2,
				"city": addr.city,
				"state": addr.state
			}

		debtor_info = {
			'company_name': self.company,
			'name': self.bank_account_name,
			'account_number': self.bank_account_no,
			'bic': bic,
			"purpose":self.purpose,
			"batch":batch,
			"company_id": tax_id,
			"dummy_bic": bic,
			"msg_id": file_name,
			"cheque_method": self.cheque_method,
			"country": get_company_code(self.company),
			"currency": self.currency,
			"address": address
		}
		debtor_info.update(self.method)

		doc = self.create_xml_file(invoices, debtor_info, filepath=filepath)

		# upload
		if not filepath:
			self.upload_xml(doc)
		else:
			return filepath

	def get_invoice_group(self):
		# group the same bank address
		map_invoice = {}
		data_field = [
			"supplier_bank",
			"invoice_no",
			"branch_code",
			"amount",
			"bank_account_name",
			"bank_account_no",
			"currency",
			"party",
			"proxy_type",
			"proxy_number"
		]
		def copy_data(source):
			dt = frappe._dict({})
			for f in data_field:
				dt[f] = source.get(f)
			return dt
		
		batch = self.name.replace("-", "")
		idx = 0
		for d in self.invoices:
			if not cint(d.selected):
				continue
			bank_account_no = cstr(d.bank_account_no) if self.payment_method != "PayNow" else cstr(d.proxy_number)
			key = (bank_account_no, d.supplier_bank, d.swift, d.currency)

			if key not in map_invoice:
				map_invoice[key] = copy_data(d)
				map_invoice[key]["invoices"]=[d]
				map_invoice[key]['batch_id'] = batch + get_alpha(idx)
				map_invoice[key]['pay_no'] = self.name
			else:
				map_invoice[key]["amount"] += flt(d.amount)
				map_invoice[key]['invoices'].append(d)

			map_invoice[key]["country"] = get_bank_number_country(d.supplier_bank_no)
			idx += 1
			
		return list(map_invoice.values())

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
		self.file_id = f"PA113{dates}{number}"
		return file_name
	
	def remove_unselected_row(self):
		rows_to_remove = []
		removed_info = []

		for idx, d in enumerate(self.invoices, start=1):
			if not d.selected:
				if frappe.db.get_value("Purchase Invoice", d.invoice_no, "docstatus") == 1:
					rows_to_remove.append(d)
					removed_info.append(f"<li>Row {idx}, Invoice {d.invoice_no} ${d.amount}</li>")

		for d in rows_to_remove:
			self.remove(d)
			frappe.db.delete(d.doctype, d.name)

		if removed_info:
			items_html = "".join(removed_info)
			msg = f"Removed due to not selected:<br><ul>{items_html}</ul>"
			self.add_comment("Comment", msg)
		self.calculate_amount()
		self.db_update()

def get_company_code(company):
	country = frappe.db.get_value("Company", company, "country")
	code = frappe.db.get_value("Country", country, "code")
	return (code or "SG").upper()

def get_bank_number_country(bank_number):
	country = frappe.db.get_value("Bank Number", bank_number)
	code = frappe.db.get_value("Country", country, "code")
	return (code or "SG").upper()

def get_date_simple(value):
	return getdate(value).strftime("%y%m%d")

def check_branch_code_mandatory(bank_name, account_no):
	"""
	Validate if the account number length is correct for OCBC, HSBC, and SBI.
	Returns True if valid or not applicable, False if invalid.
	"""
	bank_name = cstr(bank_name).upper()
	account_no = re.sub(r'\D', '', cstr(account_no))  # keep digits only
	bic = (frappe.get_value("Bank", bank_name, "swift_number") or "").upper()

	# Determine bank type
	if re.search(r'\bOCBC\b', bank_name) or re.search(r'\bOCBC\b', bic):
		valid_lengths = 10, 12
	elif re.search(r'\bHSBC\b', bank_name) or re.search(r'\bHSBC\b', bic):
		valid_lengths = 12
	elif re.search(r'\bSBI\b', bank_name) or re.search(r'\bSBI\b', bic):
		valid_lengths = 11
	else:
		# Other banks not restricted
		return False

	# Validate account number length
	return len(account_no) < valid_lengths

@frappe.whitelist()
def map_purchase_invoices(source_name, target_doc=None, args=None):
	"""Server-side mapper using get_mapped_doc to append PI rows.

	For each selected Purchase Invoice, append a row to Payment Approval's
	`invoices` child table. Uses get_mapped_doc to align with ERPNext mapping flow.
	"""

	def set_missing_values(source, target):
		# Append if not already present
		if not any(d.invoice_no == source.name for d in (target.get("invoices") or [])):
			target.append("invoices", {"invoice_no": source.name})
		return target

	mapper = {
		"Purchase Invoice": {
			"doctype": "Payment Approval",
			"validation": {"docstatus": ["=", 1]},
		}
	}

	return get_mapped_doc(
		"Purchase Invoice",
		source_name,
		mapper,
		target_doc,
		set_missing_values,
	)

@frappe.whitelist()
def make_payment_approval(source_name, target_doc=None):
	def postprocess(source_doc, target_doc):
		target_doc.total_amount = sum(flt(d.amount) for d in target_doc.get("invoices"))
		row = target_doc.append("invoices")
		row.invoice_no = source_doc.name
		row.party = source_doc.supplier
		row.amount = flt(source_doc.outstanding_amount)
		row.basic_amount = flt(source_doc.outstanding_amount)
		row.currency = source_doc.currency
		row.exchange_rate = flt(source_doc.conversion_rate)
		row.selected = 1
		target_doc.days_ago = 90
		target_doc.total_amount += flt(source_doc.outstanding_amount)
		source_doc.days_ago = 8

		# Fetch bank information from supplier's default bank account
		supplier = frappe.get_doc("Supplier", source_doc.supplier)
		if supplier.default_bank_account_no:
			row.supplier_bank_no = supplier.default_bank_account_no
			bank_account = frappe.get_doc("Bank Number", supplier.default_bank_account_no)
			if bank_account.bank:
				row.supplier_bank = bank_account.bank
				bank = frappe.get_doc("Bank", bank_account.bank)
				row.swift = bank.swift_number

	doc = get_mapped_doc(
		"Purchase Invoice",
		source_name,
		{
			"Purchase Invoice": {
				"doctype": "Payment Approval",
				"validation": {
					"docstatus": ["=", 1],
				},
			}
		},
		target_doc,
		postprocess
	)

	return doc

@frappe.whitelist()
def search_purchase_invoice(doctype, txt, searchfield, start=0, page_len=20, filters=None):
	filters = frappe._dict(filters or {})

	days_old = filters.get("days_old")
	if days_old is None:
		days_old = filters.get("days_ago")

	print(789, searchfield, txt)

	if filters.get("name"):
		del filters["name"]
	if filters.get("outstanding_amount"):
		filters["outstanding_amount"] = [">=", 0]
	if filters.get("days_ago"):
		filters['posting_date'] = ['<=', add_days(getdate(), -int(filters.get("days_ago")))]
		del filters["days_ago"]

	if txt and searchfield:
		filters[searchfield]=['like', "%{}%".format(txt)]

	# Debug trace (can be removed if noisy)
	# print("search_purchase_invoice filters:", dict(filters))

	return frappe.db.get_list(
		"Purchase Invoice",
		filters,
		[
			"name",
			"supplier",
			"company",
			"posting_date",
			"DATEDIFF(CURDATE(), posting_date) AS days_ago",
			"outstanding_amount"
		],
		limit_start=start,
		limit_page_length=page_len
	)


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def get_available_purchase_invoices(doctype, txt, searchfield, start, page_len, filters):
	limit_amount = ""
	limit_amt = frappe.db.get_single_value("UOB Integration Settings", "limit_amount")
	if limit_amt:
		limit_amount = f" AND pi.outstanding_amount <= {flt(limit_amt)} "

	return frappe.db.sql("""
		SELECT pi.name, pi.supplier, pi.posting_date,pi.outstanding_amount
		FROM `tabPurchase Invoice` pi
		WHERE pi.docstatus = 1
		  AND pi.outstanding_amount > 0
		  AND pi.currency = %(currency)s
		  AND pi.name NOT IN (
			  SELECT pil.invoice_no
			  FROM `tabPayment Invoice List` pil
			  WHERE pil.docstatus != 2 and pil.parent != %(cur_name)s
		  )
		  AND (
			  pi.{searchfield} LIKE %(txt)s
			  OR pi.supplier_name LIKE %(txt)s
		  )
		  {limit_amount}
		ORDER BY pi.posting_date DESC, pi.name DESC
		LIMIT %(start)s, %(page_len)s
	""".format(searchfield=searchfield, limit_amount=limit_amount), {
		"txt": "%%%s%%" % txt,
		"start": start,
		"page_len": page_len,
		"currency": filters.get("currency"),
		"cur_name": filters.get("cur_name"),
	}, debug=0)

def get_alpha(index):
    """
    Convert index to alphabetical suffix
    0 = A, 1 = B, ... 25 = Z, 26 = AA, 27 = AB, ...
    """
    result = ""
    index += 1  
    while index > 0:
        index, remainder = divmod(index - 1, 26)
        result = chr(ord('A') + remainder) + result
    return result