# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


from inspect import _void
import json

import frappe
from frappe import _
from frappe.contacts.report.addresses_and_contacts import test_addresses_and_contacts
from frappe.utils import formatdate, get_link_to_form, flt,fmt_money, getdate


def execute(filters=None):

	return VATAuditReport(filters).run()


class VATAuditReport(object):
	def __init__(self, filters=None):
		self.filters = frappe._dict(filters or {})
		self.columns = []
		self.data = []
		self.doctypes = ["Sales Invoice","Purchase Invoice"]

	def run(self):
		#self.get_sa_vat_accounts()
		self.invoice_items = frappe._dict()
		self.get_columns()
		gftotal_net = gstotal_net = gptotal_net = 0
		totalsstr = "Output Tax Due"
		totalpstr = "Less:Input Tax and Refunds claimed"
		totalfstr = "Equals: Net GST to be paid by you or Net GST to be claimed by you"
		for doctype in self.doctypes:
			self.select_columns = """
			name as voucher_no,
			taxes_and_charges,
			posting_date, remarks"""
			columns = (
				", supplier as party, credit_to as account, bill_no as Invoice_No"
				if doctype == "Purchase Invoice"
				else ", customer as party, debit_to as account, name as Invoice_No, debit_note_transaction"
			)
			self.select_columns += columns

			self.setup_data()
			self.get_journal_entry_data(doctype)
			self.get_invoice_data(doctype)

			if self.invoices:
				self.get_invoice_items(doctype)
				self.get_items_based_on_tax_rate(doctype)
				self.get_data(doctype)
				taxdata = self.data
			
				if doctype == "Purchase Invoice" :
					gptotal_net = taxdata[-2]["tax_amount"]
				if doctype == "Sales Invoice" :
					gstotal_net = taxdata[-2]["tax_amount"]
		gftotal_net=( 0.0 if flt(gstotal_net) =="" else flt(gstotal_net)  )- ( 0.0 if flt(gptotal_net) =="" else flt(gptotal_net)  )  
		gstotal = {
				"posting_date":  totalsstr,
				"gross_amount": '',
				"tax_amount": '',
				"tax_amount": fmt_money(gstotal_net),
				"bold": 0,
			}
		gptotal = {
				"posting_date": totalpstr,
				"gross_amount": '',
				"tax_amount": '',
				"tax_amount": fmt_money(gptotal_net),
				"bold": 0,
			}
		gftotal = {
				"posting_date": totalfstr,
				"gross_amount": '',
				"tax_amount": '',
				"tax_amount": fmt_money(gftotal_net ),
				"bold": 0,
			}
		self.data.append(gstotal)
		self.data.append(gptotal)
		self.data.append(gftotal)
		
		return self.columns, self.data

	# def get_sa_vat_accounts(self):
	# 	self.sa_vat_accounts = frappe.get_all(
	# 		"South Africa VAT Account", filters={"parent": self.filters.company}, pluck="account"
	# 	)
	# 	if not self.sa_vat_accounts and not frappe.flags.in_test and not frappe.flags.in_migrate:
	# 		link_to_settings = get_link_to_form(
	# 			"South Africa VAT Settings", "", label="South Africa VAT Settings"
	# 		)
	# 		frappe.throw(_("Please set VAT Accounts in {0}").format(link_to_settings))

	def setup_data(self):
		self.invoices = frappe._dict()
		self.tax_details = []

	def get_invoice_data(self, doctype):
		conditions = self.get_conditions()

		invoice_data = frappe.db.sql(
			"""
			SELECT
				docstatus, posting_date as inv_date, 
				{select_columns}
			FROM
				`tab{doctype}`
			WHERE
				docstatus in (1,2) 
				and is_opening = 'No'
				{where_conditions}
			ORDER BY
				posting_date DESC
			""".format(
				select_columns=self.select_columns, doctype=doctype, where_conditions=conditions
			),
			self.filters,
			as_dict=1,
			debug=0
		)

		self.get_deleted_data(doctype)

		invoice_data += self.deleted_data
		invoice_data.sort(key=lambda x: x.posting_date, reverse=True)

		for d in invoice_data:
			self.invoices.setdefault(d.voucher_no, d)

	def get_invoice_items(self, doctype):
		#, is_zero_rated
		items = frappe.db.sql(
			"""
			SELECT
				ifnull(item_code, item_name) as item_code, parent, base_net_amount
			FROM
				`tab%s Item`
			WHERE
				parent in (%s)
			"""
			% (doctype, ", ".join(["%s"] * len(self.invoices))),
			tuple(self.invoices),
			as_dict=1,
		)
		for d in items:
			self.invoice_items.setdefault(d.parent, {}).setdefault(d.item_code, {"net_amount": 0.0})
			self.invoice_items[d.parent][d.item_code]["net_amount"] += d.get("base_net_amount", 0)
		##	self.invoice_items[d.parent][d.item_code]["is_zero_rated"] = d.is_zero_rated
	def get_tax_types(self, doctype):
		tax_type = frappe._dict()
		tax_doctype = (
			"Purchase Taxes and Charges" if doctype == "Purchase Invoice" else "Sales Taxes and Charges"
		)
		#, is_zero_rated
		items = frappe.db.sql(
			"""
			SELECT
				rate, parent
			FROM
				`tab{doc_type}`
			WHERE
				parenttype = "{doc_type} Template"
			""".format(
				  doc_type=tax_doctype
			),
			as_dict=1,debug=0
		)
	 
		return items	

	def get_items_based_on_tax_rate(self, doctype):
		self.items_based_on_tax_rate = frappe._dict()
		self.item_tax_rate = frappe._dict()
		self.tax_doctype = (
			"Purchase Taxes and Charges" if doctype == "Purchase Invoice" else "Sales Taxes and Charges"
		)

		self.tax_details += list(frappe.db.sql(
			"""
			SELECT
				s.name as parent,
				t.account_head,
				t.item_wise_tax_detail,
				%(doctype)s as parenttype,
				s.posting_date
			FROM
				`tab{}` s
			LEFT JOIN 
				`tab{}` t on t.parent = s.name
			WHERE
				s.docstatus in (1, 2)
				and s.name in %(invoices)s
			ORDER BY
				t.account_head
			""".format(doctype, self.tax_doctype),
			{
				"doctype":doctype,
				"tax_doctype":self.tax_doctype,
				"invoices": [x for x in self.invoices.keys()]
			}
			, debug=0
		))

		self.tax_details += self.tax_detail_on_deleted 

		for parent, account, item_wise_tax_detail, parenttype, posting_date in self.tax_details:
			if item_wise_tax_detail:
				try:
					# if account in self.sa_vat_accounts:
					# 	item_wise_tax_detail = json.loads(item_wise_tax_detail)
					# else:
					# 	continue
					item_wise_tax_detail = json.loads(item_wise_tax_detail)
					for item_code, taxes in item_wise_tax_detail.items():
						is_zero_rated = 0# self.invoice_items.get(parent).get(item_code).get("is_zero_rated")
						# to skip items with non-zero tax rate in multiple rows gf
						#if taxes[0] == 0 and not is_zero_rated:
							#continue
						tax_rate = self.get_item_amount_map(parent, parenttype, item_code, taxes)

						if tax_rate is not None:
							rate_based_dict = self.items_based_on_tax_rate.setdefault(parent, {}).setdefault(
								tax_rate, []
							)
							if item_code not in rate_based_dict:
								rate_based_dict.append(item_code)
				except ValueError:
					continue
			else:
				items = []
				for item, detail in self.invoice_items.get(parent).items():
					items.append(item)
					taxes = [0, 0]
					self.get_item_amount_map(parent, parenttype, item, taxes)

				self.items_based_on_tax_rate.setdefault(parent, {}).setdefault(
					0, items
				)

	def get_item_amount_map(self, parent, parenttype, item_code, taxes):
		net_amount = flt(self.invoice_items.get(parent, {}).get(item_code, {}).get("net_amount"))
		gst_item = False
		if not net_amount and parent and parenttype == "Purchase Invoice":
			net_amount = flt(frappe.get_value("Purchase Invoice", parent, "base_value_for_gst_input"))
			gst_item = True

		tax_rate = taxes[0]
		tax_amount = taxes[1]
		gross_amount = net_amount + tax_amount

		self.item_tax_rate.setdefault(parent, {}).setdefault(
			item_code,
			{
				"tax_rate": tax_rate,
				"gross_amount": 0.0,
				"tax_amount": 0.0,
				"net_amount": 0.0,
				"parent":parent,
			},
		)

		self.item_tax_rate[parent][item_code]["tax_amount"] += tax_amount
		if not gst_item:
			self.item_tax_rate[parent][item_code]["net_amount"] += net_amount
			self.item_tax_rate[parent][item_code]["gross_amount"] += gross_amount
		else:
			gross_amount = net_amount + self.item_tax_rate[parent][item_code]["tax_amount"]
			self.item_tax_rate[parent][item_code]["net_amount"] = net_amount
			self.item_tax_rate[parent][item_code]["gross_amount"] = gross_amount

		return tax_rate

	def get_conditions(self):
		conditions = ""
		for opts in (
			("company", " and company=%(company)s"),
			("from_date", " and posting_date>=%(from_date)s"),
			("to_date", " and posting_date<=%(to_date)s"),
		):
			if self.filters.get(opts[0]):
				conditions += opts[1]

		return conditions

	def get_data(self, doctype):
		consolidated_data = self.get_consolidated_data(doctype)
		isloop = False
		section_name = _("Input tax/ Purchase tax") if doctype == "Purchase Invoice" else _("Output tax/ Sales tax")

		 
		gtotal_gross = gtotal_tax = gtotal_net = 0.0
		totalstr = " "
		for taxType, section in consolidated_data.items():
			label = frappe.bold(section_name )
			section_head = {"posting_date": label}
			total_gross = total_tax = total_net = 0.0
			self.data.append(section_head) if isloop == False else  _void
			isloop = True
			invoice_detail = []
			for row in section.get("data"):
				if (self.filters.show_details):
					invoice_detail.append(row)

				total_gross += 0 if  row["gross_amount"]=="" else flt(row["gross_amount"])
				total_tax += 0 if  row["tax_amount"] =="" else  flt(row["tax_amount"])
				total_net += 0 if row["net_amount"] =="" else flt(row["net_amount"])
			
			# add cancelled
			# if self.filters.show_details:
			# 	invoice_detail += pi_cancel
			# 	invoice_detail += si_cancel

			def sort_by_data(dt):
				return getdate(dt.get("inv_date"))
			
			# invoice_detail.sort(key = sort_by_data)
			
			self.data += invoice_detail
			totalstr = _("Total value of taxable ") if doctype == "Purchase Invoice" else _("Total value of taxable ")
			doctypestr = _("Purchases") if doctype == "Purchase Invoice" else _("Sales")
			total = {
				"posting_date": totalstr + taxType,
				"gross_amount": fmt_money(total_gross),
				"tax_amount": fmt_money(total_tax),
				"net_amount": fmt_money(total_net),
				"bold": 0,
				#"voucher_type":"noclick",
			}
			
			self.data.append(total)
			gross_amount= 0.0 if  row["gross_amount"] =="" else flt(total["gross_amount"])
			gtotal_gross += gross_amount
			gtotal_tax +=  0.0 if  row["tax_amount"] =="" else flt(total["tax_amount"])
			gtotal_net +=  0.0 if  row["net_amount"] =="" else flt(total["net_amount"])
			
		gtotal = {
				"posting_date": totalstr + doctypestr,
				"gross_amount": fmt_money(gtotal_gross),
				"tax_amount": fmt_money(gtotal_tax),
				"net_amount": fmt_money(gtotal_net),
				"bold": 0,
				"voucher_type":doctype,
			}
		self.data.append(gtotal)
		self.data.append({}) #if doctype == "Purchase Invoice" else _void

	def get_deleted_data(self, doctype):
		self.deleted_data = []
		self.tax_detail_on_deleted = []
		conditions = ""
		for opts in (
			("from_date", " and document_date>=%(from_date)s"),
			("to_date", " and document_date<=%(to_date)s"),
		):
			if self.filters.get(opts[0]):
				conditions += opts[1]
		data = frappe.db.sql("""
			SELECT 
				name, document_date, data
			FROM
				`tabDeleted Document`
			WHERE
				deleted_doctype = "{doctype}" 
				{where_conditions}
					   
		""".format(
			where_conditions=conditions, doctype=doctype
		), self.filters, as_dict=1, debug=0)

		for d in data:
			dt = frappe._dict(json.loads(d.data))

			if dt.docstatus == 0:
				continue

			# overide data
			dt.voucher_no = dt.name
			dt.docstatus = 3
			dt.posting_date = getdate(dt.posting_date)
			if doctype == "Purchase Invoice":
				dt.Invoice_No = dt.bill_no
				dt.party = dt.supplier
				dt.account = dt.credit_to
			else:
				dt.Invoice_No = dt.name
				dt.party = dt.customer
				dt.account = dt.debit_to

			self.deleted_data.append(dt)
			self.invoices.setdefault(dt.voucher_no, dt)
			for row in dt.get("items"):
				row = frappe._dict(row)
				# print(1000, row.parent, [row.item_code, {"net_amount": 0.0}])
				self.invoice_items.setdefault(row.parent, {}).setdefault(row.item_code, {"net_amount": 0.0})

			for row in dt.get("taxes"):
				row = frappe._dict(row)
				# print(2000, row.parent, [row.account_head, row.item_wise_tax_detail, row.parenttype, getdate(dt.posting_date)])
				self.tax_detail_on_deleted.append((row.parent, row.account_head, row.item_wise_tax_detail, row.parenttype, getdate(dt.posting_date)))
			
	def get_journal_entry_data(self, doctype):
		self.tax_detail_on_deleted = []
		conditions = ""
		for opts in (
			("from_date", " and posting_date>=%(from_date)s"),
			("to_date", " and posting_date<=%(to_date)s"),
		):
			if self.filters.get(opts[0]):
				conditions += opts[1]
		data = frappe.db.sql("""
			SELECT 
				name, transaction_type, tax_template, total_debit, invoice_no, party_name, base_value, posting_date, is_tax_refund
			FROM
				`tabJournal Entry`
			WHERE
				voucher_type = "GST Input Tax"
				and docstatus = 1
				and invoice_type = "{doctype}"
				{where_conditions}
					   
		""".format(
			where_conditions=conditions, doctype=doctype
		), self.filters, as_dict=1)

		for d in data:
			dt = frappe._dict(d)

			# overide data
			dt.voucher_no = dt.name
			dt.docstatus = 1
			dt.is_journal_entry = 1
			dt.posting_date = getdate(d.posting_date)
			dt.Invoice_No = dt.invoice_no
			dt.party = dt.party_name
			dt.taxes_and_charges = dt.tax_template
			if d.transaction_type == "Buying":
				invoice_type = "Purchase Invoice"
				if dt.is_tax_refund:
					account_head = ''
				# dt.account = dt.credit_to
			else:
				invoice_type = "Sales Invoice"
				pass
				# dt.account = dt.debit_to

			item_name = "item"
			account_head = ''
			temp = {}
			total = dt.total_debit * (-1 if dt.is_tax_refund else 1)
			temp[item_name] = [8, total]
			tax_detail = json.dumps(temp)
			self.invoices.setdefault(dt.voucher_no, dt)
			self.invoice_items.setdefault(dt.name, {}).setdefault(item_name, {"net_amount": d.base_value})
			self.tax_details.append((dt.name, account_head, tax_detail, invoice_type, getdate(dt.posting_date)))


	def get_consolidated_data(self, doctype):
		consolidated_data_map = {}
		self.already_add = []
		tax_doctype = (
			"Purchase Taxes and Charges Template" if doctype == "Purchase Invoice" else "Sales Taxes and Charges Template"
		)
		default_for_zero_tax = frappe.get_value(tax_doctype, {"default_for_zero":1}) or ""
		for inv, inv_data in self.invoices.items():
			if True:
				data = self.items_based_on_tax_rate.get(inv) or {0: ['']}
				for rate, items in data.items():
					row = {"tax_amount": 0.0, "gross_amount": 0.0, "net_amount": 0.0}
					docprefix = _("purchases ") if doctype == "Purchase Invoice" else _("sales ")
					taxdata = default_for_zero_tax if inv_data.get("taxes_and_charges") is None else inv_data.get("taxes_and_charges")
					taxType = docprefix + taxdata
					consolidated_data_map.setdefault(taxType, {"data": []})
					key = inv
					if key not in self.already_add:
						self.already_add.append(key)
					else:
						continue

					for item in items:
						detail = self.item_tax_rate.get(inv) or {}
						item_details = detail.get(item)

						row['inv_date'] = inv_data.get("posting_date")
						row["account"] = inv_data.get("account")
						row["Invoice_No"]= inv_data.get("Invoice_No")
						row["posting_date"] = inv#formatdate(inv_data.get("posting_date"), "dd-mm-yyyy")

						row["Date"] = formatdate(inv_data.get("posting_date"), "dd-mm-yyyy")
						#row["voucher_type"] = ""
						row["voucher_no"] = inv
						row["party_type"] = "Customer" if doctype == "Sales Invoice" else "Supplier"
						row["party"] = inv_data.get("party")
						row["remarks"] = inv_data.get("remarks")

						if inv_data.docstatus == 2:
							row['posting_date'] = f"{inv} - Cancelled"
							continue

						if inv_data.docstatus == 3:
							row['posting_date'] = f"{inv} - Deleted"
							continue

						if inv_data.get("debit_note_transaction"):
							row['posting_date'] = f"{inv} - Debit Note"
							# continue
						
						if inv_data.get("is_journal_entry"):
							row['posting_date'] = f"{inv} - Journal Entry"

						if inv_data.get("is_tax_refund"):
							row['posting_date'] += " (refund)"

						if not item_details:
							continue
					 
						rowgross_amount = 0.0 if item_details.get("gross_amount") =="" else item_details.get("gross_amount")

						row["gross_amount"] += item_details.get("gross_amount")
						row["tax_amount"] +=  item_details.get("tax_amount")
						row["net_amount"] += item_details.get("net_amount")
						row["tax_charge"] = inv_data.get("taxes_and_charges")
      
				 	
					row["tax_amount"] = fmt_money(row["tax_amount"] )
					row["net_amount"] = fmt_money(row["net_amount"] )
					row["gross_amount"] = fmt_money(row["gross_amount"] )
					consolidated_data_map[taxType]["data"].append(row)

		get_tax_type = self.get_tax_types(doctype)
		
		for tax_type in get_tax_type:
			docprefix = _("purchases ") if doctype == "Purchase Invoice" else _("sales ")
			taxtype =docprefix +  tax_type.get("parent")
			 
			if (taxtype in consolidated_data_map):
				continue
			else:
				row = {"tax_amount": 0.0, "gross_amount": 0.0, "net_amount": 0.0}	 
				consolidated_data_map.setdefault(taxtype, {"data": []})
				row["account"] = ""
				row["posting_date"] =""
				row["voucher_type"] = ""
				row["voucher_no"] = ""
				row["party_type"] = "Customer" if doctype == "Sales Invoice" else "Supplier"
				row["party"] = ""
				row["remarks"] = ""
				row["gross_amount"] = ""
				row["tax_amount"] = ""
				row["net_amount"] = ""
				row["tax_charge"] = tax_type.get("parent")
				consolidated_data_map[taxtype]["data"].append(row)
		 
		return consolidated_data_map

	def get_columns(self):
		if (self.filters.show_details):
						self.columns +=[ 	{"fieldname": "party",
								"label": "Company",
								"fieldtype": "Data",
								"width": 140}]
		if (self.filters.show_details):
							self.columns +=[ {"fieldname": "Invoice_No",
							"label": "Invoice",
							"fieldtype": "Data",
							"width": 140}]
		if (self.filters.show_details):	
							self.columns +=[ {"fieldname": "Date",
							"label": "Date",
							"fieldtype": "Data",
							"width": 140}]
		self.columns += [
						

			{"fieldname": "posting_date", "label": " ", "fieldtype": "Link","options": "Account", "width": 350},
			{
				"fieldname": "account",
				"label": "Account",
				"fieldtype": "Link",
				"options": "Account",
				"width": 180,
				"hidden": 1
			},
			{
				"fieldname": "voucher_type",
				"label": "Voucher Type",
				"fieldtype": "Data",
				"width": 140,
				"hidden": 1
			},
			{
				"fieldname": "voucher_no",
				"label": "Reference",
				"fieldtype": "Dynamic Link",
				"options": "voucher_type",
				"width": 150,
				"hidden": 1
			},
			{
				"fieldname": "party_type",
				"label": "Party Type",
				"fieldtype": "Data",
				"width": 140,
				"hidden": 1
				 
			},
			{
				"fieldname": "party",
				"label": "Party",
				"fieldtype": "Dynamic Link",
				"options": "party_type",
				"width": 150,
				"hidden": 1
			},
			{"fieldname": "remarks", "label": "Details", "fieldtype": "Data", "width": 150,"hidden": 1},
			{"fieldname": "net_amount", "label": "Taxable Amount", "fieldtype": "Currency","options":"Company:company:default_currency", "width": 150},
			{"fieldname": "tax_amount", "label": "GST Amount", "fieldtype": "Currency","options":"Company:company:default_currency", "width": 150},
			{"fieldname": "gross_amount", "label": "Total", "fieldtype": "Currency","options":"Company:company:default_currency", "width": 150},
		]
